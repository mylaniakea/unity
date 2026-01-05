"""
Server Credential Management Service

Handles CRUD operations for server credentials with encryption.
Links to Unity's ServerProfile system.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.models import ServerCredential, ServerProfile, User
from .encryption import EncryptionService


class ServerCredentialService:
    """Service for managing server credentials"""
    
    @staticmethod
    def create_credential(
        db: Session,
        server_profile_id: int,
        username: str,
        password: Optional[str],
        ssh_key_id: Optional[int],
        sudo_password: Optional[str],
        created_by: Optional[int],
        encryption_service: EncryptionService
    ) -> ServerCredential:
        """Create a new server credential with encryption"""
        
        # Encrypt sensitive fields
        encrypted_password = None
        if password:
            encrypted_password = encryption_service.encrypt(password)
        
        encrypted_sudo_password = None
        if sudo_password:
            encrypted_sudo_password = encryption_service.encrypt(sudo_password)
        
        credential = ServerCredential(
            server_profile_id=server_profile_id,
            username=username,
            password=encrypted_password,
            ssh_key_id=ssh_key_id,
            sudo_password=encrypted_sudo_password,
            created_by=created_by
        )
        
        db.add(credential)
        db.commit()
        db.refresh(credential)
        
        return credential
    
    @staticmethod
    def get_credential(
        db: Session,
        credential_id: int,
        encryption_service: EncryptionService,
        decrypt: bool = False
    ) -> Optional[ServerCredential]:
        """Get credential by ID, optionally decrypting passwords"""
        
        stmt = select(ServerCredential).where(ServerCredential.id == credential_id)
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if credential and decrypt:
            if credential.password:
                credential.password = encryption_service.decrypt(credential.password)
            if credential.sudo_password:
                credential.sudo_password = encryption_service.decrypt(credential.sudo_password)
        
        return credential
    
    @staticmethod
    def get_credential_by_server(
        db: Session,
        server_profile_id: int,
        encryption_service: EncryptionService,
        decrypt: bool = False
    ) -> Optional[ServerCredential]:
        """Get credential for a specific server"""
        
        stmt = select(ServerCredential).where(
            ServerCredential.server_profile_id == server_profile_id
        )
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if credential and decrypt:
            if credential.password:
                credential.password = encryption_service.decrypt(credential.password)
            if credential.sudo_password:
                credential.sudo_password = encryption_service.decrypt(credential.sudo_password)
        
        return credential
    
    @staticmethod
    def list_credentials(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        created_by: Optional[int] = None
    ) -> List[ServerCredential]:
        """List credentials (passwords remain encrypted)"""
        
        stmt = select(ServerCredential)
        
        if created_by:
            stmt = stmt.where(ServerCredential.created_by == created_by)
        
        stmt = stmt.offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def update_credential(
        db: Session,
        credential_id: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssh_key_id: Optional[int] = None,
        sudo_password: Optional[str] = None,
        encryption_service: Optional[EncryptionService] = None
    ) -> Optional[ServerCredential]:
        """Update credential"""
        
        stmt = select(ServerCredential).where(ServerCredential.id == credential_id)
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            return None
        
        if username is not None:
            credential.username = username
        
        if password is not None and encryption_service:
            credential.password = encryption_service.encrypt(password)
        
        if ssh_key_id is not None:
            credential.ssh_key_id = ssh_key_id
        
        if sudo_password is not None and encryption_service:
            credential.sudo_password = encryption_service.encrypt(sudo_password)
        
        db.commit()
        db.refresh(credential)
        
        return credential
    
    @staticmethod
    def update_last_used(db: Session, credential_id: int, tenant_id: str = "default"):
        """Update last_used timestamp"""
        
        stmt = select(ServerCredential).where(ServerCredential.id == credential_id)
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if credential:
            credential.last_used = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def delete_credential(db: Session, credential_id: int) -> bool:
        """Delete credential"""
        
        stmt = select(ServerCredential).where(ServerCredential.id == credential_id)
        result = db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if credential:
            db.delete(credential)
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def verify_server_exists(db: Session, server_profile_id: int) -> bool:
        """Verify that server profile exists"""
        
        stmt = select(ServerProfile).where(ServerProfile.id == server_profile_id)
        result = db.execute(stmt)
        server = result.scalar_one_or_none()
        
        return server is not None
