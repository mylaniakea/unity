"""
SSH Key Management Service

Handles CRUD operations for SSH keys with encryption.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import subprocess
import tempfile
import os

from app.models import SSHKey, User
from .encryption import EncryptionService


class SSHKeyService:
    """Service for managing SSH keys"""
    
    @staticmethod
    def generate_key_pair(key_type: str = "rsa", key_size: int = 4096) -> tuple[str, str]:
        """
        Generate a new SSH key pair.
        
        Args:
            key_type: Key type (rsa, ed25519)
            key_size: Key size for RSA (2048, 4096)
            
        Returns:
            Tuple of (private_key, public_key)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "key")
            
            if key_type == "ed25519":
                subprocess.run(
                    ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-N", ""],
                    check=True,
                    capture_output=True
                )
            else:  # rsa
                subprocess.run(
                    ["ssh-keygen", "-t", "rsa", "-b", str(key_size), "-f", key_path, "-N", ""],
                    check=True,
                    capture_output=True
                )
            
            with open(key_path, "r") as f:
                private_key = f.read()
            
            with open(f"{key_path}.pub", "r") as f:
                public_key = f.read()
        
        return private_key, public_key
    
    @staticmethod
    def get_fingerprint(public_key: str) -> Optional[str]:
        """Get SSH key fingerprint from public key"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pub') as f:
                f.write(public_key)
                f.flush()
                
                result = subprocess.run(
                    ["ssh-keygen", "-lf", f.name],
                    capture_output=True,
                    text=True
                )
                
                os.unlink(f.name)
                
                if result.returncode == 0:
                    # Output format: "2048 SHA256:xxx comment"
                    parts = result.stdout.strip().split()
                    if len(parts) >= 2:
                        return parts[1]  # The fingerprint
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def create_ssh_key(
        db: Session,
        name: str,
        description: Optional[str],
        private_key: str,
        public_key: str,
        key_type: str,
        key_size: Optional[int],
        created_by: Optional[int],
        encryption_service: EncryptionService
    ) -> SSHKey:
        """Create a new SSH key with encryption"""
        
        # Encrypt the private key
        encrypted_private_key = encryption_service.encrypt(private_key)
        
        # Get fingerprint
        fingerprint = SSHKeyService.get_fingerprint(public_key)
        
        ssh_key = SSHKey(
            name=name,
            description=description,
            public_key=public_key,
            private_key=encrypted_private_key,
            key_type=key_type,
            key_size=key_size,
            fingerprint=fingerprint,
            created_by=created_by
        )
        
        db.add(ssh_key)
        db.commit()
        db.refresh(ssh_key)
        
        return ssh_key
    
    @staticmethod
    def get_ssh_key(
        db: Session,
        key_id: int,
        encryption_service: EncryptionService,
        decrypt: bool = False
    ) -> Optional[SSHKey]:
        """Get SSH key by ID, optionally decrypting private key"""
        
        stmt = select(SSHKey).where(SSHKey.id == key_id)
        result = db.execute(stmt)
        ssh_key = result.scalar_one_or_none()
        
        if ssh_key and decrypt:
            ssh_key.private_key = encryption_service.decrypt(ssh_key.private_key)
        
        return ssh_key
    
    @staticmethod
    def get_ssh_key_by_name(
        db: Session,
        name: str,
        encryption_service: EncryptionService,
        decrypt: bool = False
    ) -> Optional[SSHKey]:
        """Get SSH key by name"""
        
        stmt = select(SSHKey).where(SSHKey.name == name)
        result = db.execute(stmt)
        ssh_key = result.scalar_one_or_none()
        
        if ssh_key and decrypt:
            ssh_key.private_key = encryption_service.decrypt(ssh_key.private_key)
        
        return ssh_key
    
    @staticmethod
    def list_ssh_keys(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        created_by: Optional[int] = None
    ) -> List[SSHKey]:
        """List SSH keys (private keys remain encrypted)"""
        
        stmt = select(SSHKey)
        
        if created_by:
            stmt = stmt.where(SSHKey.created_by == created_by)
        
        stmt = stmt.offset(skip).limit(limit)
        
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    def update_last_used(db: Session, key_id: int):
        """Update last_used timestamp"""
        
        stmt = select(SSHKey).where(SSHKey.id == key_id)
        result = db.execute(stmt)
        ssh_key = result.scalar_one_or_none()
        
        if ssh_key:
            ssh_key.last_used = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def delete_ssh_key(db: Session, key_id: int) -> bool:
        """Delete SSH key"""
        
        stmt = select(SSHKey).where(SSHKey.id == key_id)
        result = db.execute(stmt)
        ssh_key = result.scalar_one_or_none()
        
        if ssh_key:
            db.delete(ssh_key)
            db.commit()
            return True
        
        return False
