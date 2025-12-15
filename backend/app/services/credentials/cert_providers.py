"""
Certificate Auto-Renewal Providers

ACME support for Let's Encrypt, ZeroSSL, and other certificate authorities.
Adapted from KC-Booth for Unity integration.
"""

import subprocess
import os
import tempfile
import re
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from .certificates import CertificateService
from .encryption import EncryptionService


def validate_domain(domain: str) -> str:
    """
    Validate domain name to prevent command injection.
    
    Raises:
        ValueError: If domain contains invalid characters
    """
    if not re.match(r'^[a-zA-Z0-9\.\-\*]+$', domain):
        raise ValueError(f"Invalid domain name: {domain}")
    if len(domain) > 253:
        raise ValueError("Domain name too long")
    if domain.startswith('-') or domain.endswith('-'):
        raise ValueError("Domain cannot start or end with hyphen")
    return domain


class CertificateProvider(ABC):
    """Abstract base class for certificate providers"""
    
    @abstractmethod
    def issue_certificate(self, domain: str, email: Optional[str] = None) -> Tuple[str, str, Optional[str]]:
        """
        Issue a certificate for the given domain.
        
        Returns:
            Tuple of (certificate, private_key, chain)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this provider"""
        pass


class LetsEncryptProvider(CertificateProvider):
    """
    Let's Encrypt via certbot for TLS/HTTPS certificates.
    
    Supports HTTP-01 and DNS-01 challenges.
    """
    
    def get_name(self) -> str:
        return "letsencrypt"
    
    def issue_certificate(
        self, 
        domain: str, 
        email: Optional[str] = None,
        use_staging: bool = False,
        challenge_type: str = "standalone"
    ) -> Tuple[str, str, Optional[str]]:
        """
        Issue TLS certificate via Let's Encrypt.
        
        Args:
            domain: Domain name
            email: Contact email for notifications
            use_staging: Use staging server for testing
            challenge_type: 'standalone', 'webroot', or 'dns'
            
        Returns:
            Tuple of (certificate, private_key, chain)
        """
        domain = validate_domain(domain)
        email = email or "admin@example.com"
        
        # Build certbot command
        cmd = [
            "certbot", "certonly",
            "--non-interactive",
            "--agree-tos",
            "--email", email,
            "-d", domain
        ]
        
        if use_staging:
            cmd.append("--staging")
        
        if challenge_type == "standalone":
            cmd.append("--standalone")
        elif challenge_type == "webroot":
            cmd.extend(["--webroot", "-w", "/var/www/html"])
        elif challenge_type == "dns":
            cmd.append("--manual")
            cmd.append("--preferred-challenges=dns")
        
        # Run certbot
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Certbot failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("Certbot timed out after 5 minutes")
        
        # Read certificate files
        # Certificates stored in /etc/letsencrypt/live/{domain}/
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        chain_path = f"/etc/letsencrypt/live/{domain}/chain.pem"
        
        try:
            with open(cert_path, "r") as f:
                cert = f.read()
            with open(key_path, "r") as f:
                key = f.read()
            with open(chain_path, "r") as f:
                chain = f.read()
        except FileNotFoundError as e:
            raise Exception(f"Certificate files not found: {e}")
        
        return cert, key, chain


class ZeroSSLProvider(CertificateProvider):
    """
    ZeroSSL provider (ACME-compatible).
    
    Free alternative to Let's Encrypt with higher rate limits.
    """
    
    def get_name(self) -> str:
        return "zerossl"
    
    def issue_certificate(
        self, 
        domain: str, 
        email: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Issue certificate via ZeroSSL.
        
        Requires ZeroSSL account and API key.
        """
        domain = validate_domain(domain)
        email = email or "admin@example.com"
        
        if not api_key:
            raise ValueError("ZeroSSL requires an API key")
        
        # ZeroSSL uses ACME but with EAB (External Account Binding)
        cmd = [
            "certbot", "certonly",
            "--non-interactive",
            "--agree-tos",
            "--email", email,
            "--server", "https://acme.zerossl.com/v2/DV90",
            "--eab-kid", api_key,  # External Account Binding
            "--eab-hmac-key", api_key,
            "-d", domain,
            "--standalone"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        except subprocess.CalledProcessError as e:
            raise Exception(f"ZeroSSL certbot failed: {e.stderr}")
        
        # Read certificates
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        chain_path = f"/etc/letsencrypt/live/{domain}/chain.pem"
        
        with open(cert_path, "r") as f:
            cert = f.read()
        with open(key_path, "r") as f:
            key = f.read()
        with open(chain_path, "r") as f:
            chain = f.read()
        
        return cert, key, chain


class SelfSignedProvider(CertificateProvider):
    """Self-signed certificate generator for testing"""
    
    def get_name(self) -> str:
        return "self-signed"
    
    def issue_certificate(
        self, 
        domain: str, 
        email: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """Generate self-signed certificate using openssl"""
        
        # Use the existing CertificateService method
        from .certificates import CertificateService
        cert, key = CertificateService.generate_self_signed_cert(
            common_name=domain,
            validity_days=365
        )
        
        return cert, key, None


# Provider registry
PROVIDERS = {
    "letsencrypt": LetsEncryptProvider,
    "zerossl": ZeroSSLProvider,
    "self-signed": SelfSignedProvider,
}


def get_provider(provider_name: str) -> CertificateProvider:
    """
    Get certificate provider instance.
    
    Args:
        provider_name: Name of provider (letsencrypt, zerossl, self-signed)
        
    Returns:
        CertificateProvider instance
        
    Raises:
        ValueError: If provider not found
    """
    provider_class = PROVIDERS.get(provider_name.lower())
    if not provider_class:
        available = ', '.join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{provider_name}'. Available: {available}")
    
    return provider_class()


class CertificateRenewalService:
    """Service for automatic certificate renewal"""
    
    @staticmethod
    def renew_certificate_acme(
        db: Session,
        cert_id: int,
        encryption_service: EncryptionService,
        provider_name: str = "letsencrypt",
        email: Optional[str] = None,
        **provider_kwargs
    ) -> dict:
        """
        Renew certificate using ACME provider.
        
        Args:
            db: Database session
            cert_id: Certificate ID to renew
            encryption_service: Encryption service
            provider_name: Provider to use (letsencrypt, zerossl)
            email: Contact email
            **provider_kwargs: Additional provider-specific arguments
            
        Returns:
            Dict with renewal status
        """
        
        # Get existing certificate
        cert = CertificateService.get_certificate(db, cert_id, encryption_service, decrypt=False)
        if not cert:
            raise ValueError(f"Certificate {cert_id} not found")
        
        # Extract domain from certificate name or metadata
        domain = cert.name.replace(" ", "").replace("*", "wildcard")
        
        # Get provider
        provider = get_provider(provider_name)
        
        try:
            # Issue new certificate
            new_cert, new_key, chain = provider.issue_certificate(
                domain=domain,
                email=email,
                **provider_kwargs
            )
            
            # Update certificate in database
            updated_cert = CertificateService.update_certificate(
                db=db,
                cert_id=cert_id,
                certificate=new_cert,
                private_key=new_key,
                chain=chain,
                encryption_service=encryption_service
            )
            
            return {
                "success": True,
                "certificate_id": cert_id,
                "certificate_name": cert.name,
                "provider": provider_name,
                "valid_until": updated_cert.valid_until.isoformat() if updated_cert else None,
                "renewed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "certificate_id": cert_id,
                "certificate_name": cert.name,
                "provider": provider_name,
                "error": str(e),
                "attempted_at": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_expiring_certificates(
        db: Session,
        days_threshold: int = 30
    ) -> list:
        """
        Check for certificates expiring soon.
        
        Returns:
            List of certificates that need renewal
        """
        expiring = CertificateService.get_expiring_soon(db, days=days_threshold)
        
        return [
            {
                "id": cert.id,
                "name": cert.name,
                "valid_until": cert.valid_until.isoformat(),
                "days_remaining": (cert.valid_until - datetime.utcnow()).days,
                "auto_renew": cert.auto_renew,
                "provider": cert.provider
            }
            for cert in expiring
        ]
