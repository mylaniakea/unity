"""
Certificate Management Service

Handles CRUD operations for SSL/TLS certificates with validation and renewal.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import subprocess

from app.models import Certificate, User
from .encryption import EncryptionService


class CertificateService:
    """Service for managing SSL/TLS certificates"""
    
    @staticmethod
    def parse_certificate(cert_pem: str) -> dict:
        """
        Parse certificate and extract metadata.
        
        Returns:
            dict with subject, issuer, valid_from, valid_until, serial_number
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
            
            return {
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "valid_from": cert.not_valid_before_utc,
                "valid_until": cert.not_valid_after_utc,
                "serial_number": str(cert.serial_number)
            }
        except Exception as e:
            raise ValueError(f"Invalid certificate: {str(e)}")
    
    @staticmethod
    def generate_self_signed_cert(
        common_name: str,
        organization: Optional[str] = None,
        validity_days: int = 365
    ) -> tuple[str, str]:
        """
        Generate a self-signed certificate.
        
        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        if organization:
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Convert to PEM format
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        return cert_pem, key_pem
    
    @staticmethod
    def create_certificate(
        db: Session,
        name: str,
        description: Optional[str],
        certificate: str,
        private_key: Optional[str],
        chain: Optional[str],
        provider: str,
        auto_renew: bool,
        renewal_days: int,
        created_by: Optional[int],
        encryption_service: EncryptionService
    ) -> Certificate:
        """Create a new certificate with encryption"""
        
        # Parse certificate metadata
        cert_info = CertificateService.parse_certificate(certificate)
        
        # Encrypt private key if provided
        encrypted_private_key = None
        if private_key:
            encrypted_private_key = encryption_service.encrypt(private_key)
        
        cert_obj = Certificate(
            name=name,
            description=description,
            certificate=certificate,
            private_key=encrypted_private_key,
            chain=chain,
            provider=provider,
            auto_renew=auto_renew,
            renewal_days=renewal_days,
            valid_from=cert_info["valid_from"],
            valid_until=cert_info["valid_until"],
            created_by=created_by
        )
        
        db.add(cert_obj)
        db.commit()
        db.refresh(cert_obj)
        
        return cert_obj
    
    @staticmethod
    def get_certificate(
        db: Session,
        cert_id: int,
        encryption_service: EncryptionService,
        decrypt: bool = False
    ) -> Optional[Certificate]:
        """Get certificate by ID, optionally decrypting private key"""
        
        stmt = select(Certificate).where(Certificate.id == cert_id)
        result = db.execute(stmt)
        cert = result.scalar_one_or_none()
        
        if cert and decrypt and cert.private_key:
            cert.private_key = encryption_service.decrypt(cert.private_key)
        
        return cert
    
    @staticmethod
    def get_certificate_by_name(
        db: Session,
        name: str,
        encryption_service: EncryptionService,
        decrypt: bool = False
    ) -> Optional[Certificate]:
        """Get certificate by name"""
        
        stmt = select(Certificate).where(Certificate.name == name)
        result = db.execute(stmt)
        cert = result.scalar_one_or_none()
        
        if cert and decrypt and cert.private_key:
            cert.private_key = encryption_service.decrypt(cert.private_key)
        
        return cert
    
    @staticmethod
    def list_certificates(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        created_by: Optional[int] = None
    ) -> List[Certificate]:
        """List certificates (private keys remain encrypted)"""
        
        stmt = select(Certificate)
        
        if created_by:
            stmt = stmt.where(Certificate.created_by == created_by)
        
        stmt = stmt.offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def get_expiring_soon(
        db: Session,
        days: int = 30
    ) -> List[Certificate]:
        """Get certificates expiring within specified days"""
        
        threshold = datetime.utcnow() + timedelta(days=days)
        
        stmt = select(Certificate).where(
            Certificate.valid_until <= threshold
        )
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def update_certificate(
        db: Session,
        cert_id: int,
        certificate: str,
        private_key: Optional[str],
        chain: Optional[str],
        encryption_service: EncryptionService
    ) -> Optional[Certificate]:
        """Update certificate (for renewal)"""
        
        stmt = select(Certificate).where(Certificate.id == cert_id)
        result = db.execute(stmt)
        cert_obj = result.scalar_one_or_none()
        
        if not cert_obj:
            return None
        
        # Parse new certificate metadata
        cert_info = CertificateService.parse_certificate(certificate)
        
        # Update fields
        cert_obj.certificate = certificate
        cert_obj.valid_from = cert_info["valid_from"]
        cert_obj.valid_until = cert_info["valid_until"]
        cert_obj.last_renewed = datetime.utcnow()
        
        if private_key:
            cert_obj.private_key = encryption_service.encrypt(private_key)
        
        if chain:
            cert_obj.chain = chain
        
        db.commit()
        db.refresh(cert_obj)
        
        return cert_obj
    
    @staticmethod
    def delete_certificate(db: Session, cert_id: int) -> bool:
        """Delete certificate"""
        
        stmt = select(Certificate).where(Certificate.id == cert_id)
        result = db.execute(stmt)
        cert = result.scalar_one_or_none()
        
        if cert:
            db.delete(cert)
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def is_expiring_soon(cert: Certificate, days: int = 30) -> bool:
        """Check if certificate is expiring soon"""
        threshold = datetime.utcnow() + timedelta(days=days)
        return cert.valid_until <= threshold
