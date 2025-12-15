"""
Pydantic schemas for credential management API.

Security note: Sensitive fields (private keys, passwords) are excluded from response models.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional
import re


# ============================================================
# SSH Key Schemas
# ============================================================

class SSHKeyBase(BaseModel):
    """Base SSH key schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name contains no special characters"""
        if not re.match(r'^[a-zA-Z0-9\-_\s]+$', v):
            raise ValueError("Name contains invalid characters")
        return v


class SSHKeyCreate(SSHKeyBase):
    """Create SSH key - includes private key"""
    public_key: str
    private_key: str
    key_type: str = Field(..., pattern="^(rsa|ed25519)$")
    key_size: Optional[int] = Field(None, ge=2048, le=8192)
    
    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, v: str) -> str:
        """Validate SSH public key format"""
        if not v.startswith(("ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2-")):
            raise ValueError("Invalid SSH public key format")
        parts = v.split()
        if len(parts) < 2:
            raise ValueError("SSH public key must have at least key type and key data")
        return v
    
    @field_validator("private_key")
    @classmethod
    def validate_private_key(cls, v: str) -> str:
        """Validate SSH private key format"""
        if not ("BEGIN" in v and "PRIVATE KEY" in v and "END" in v):
            raise ValueError("Invalid SSH private key format")
        return v


class SSHKeyGenerate(BaseModel):
    """Request to generate SSH key pair"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    key_type: str = Field(default="rsa", pattern="^(rsa|ed25519)$")
    key_size: int = Field(default=4096, ge=2048, le=8192)


class SSHKeyResponse(SSHKeyBase):
    """SSH key response - private key excluded for security"""
    id: int
    public_key: str
    key_type: str
    key_size: Optional[int]
    fingerprint: Optional[str]
    created_by: Optional[int]
    created_at: datetime
    last_used: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class SSHKeyWithPrivateKey(SSHKeyResponse):
    """SSH key with decrypted private key - only for authorized access"""
    private_key: str


# ============================================================
# Certificate Schemas
# ============================================================

class CertificateBase(BaseModel):
    """Base certificate schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    provider: str = Field(..., max_length=50)
    auto_renew: bool = False
    renewal_days: int = Field(default=30, ge=1, le=90)


class CertificateCreate(CertificateBase):
    """Create certificate - includes private key"""
    certificate: str
    private_key: Optional[str] = None
    chain: Optional[str] = None
    
    @field_validator("certificate")
    @classmethod
    def validate_certificate(cls, v: str) -> str:
        """Validate certificate format"""
        if not ("BEGIN CERTIFICATE" in v and "END CERTIFICATE" in v):
            raise ValueError("Invalid certificate format")
        return v
    
    @field_validator("private_key")
    @classmethod
    def validate_private_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate private key format if provided"""
        if v and not ("BEGIN" in v and "PRIVATE KEY" in v and "END" in v):
            raise ValueError("Invalid private key format")
        return v


class CertificateGenerateSelfSigned(BaseModel):
    """Request to generate self-signed certificate"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    common_name: str = Field(..., min_length=1, max_length=253)
    organization: Optional[str] = Field(None, max_length=100)
    validity_days: int = Field(default=365, ge=1, le=3650)


class CertificateResponse(CertificateBase):
    """Certificate response - private key excluded for security"""
    id: int
    certificate: str
    chain: Optional[str]
    valid_from: datetime
    valid_until: datetime
    last_renewed: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CertificateWithPrivateKey(CertificateResponse):
    """Certificate with decrypted private key - only for authorized access"""
    private_key: Optional[str]


# ============================================================
# Server Credential Schemas
# ============================================================

class ServerCredentialBase(BaseModel):
    """Base server credential schema"""
    server_profile_id: int = Field(..., gt=0)
    username: str = Field(..., min_length=1, max_length=100)
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username to prevent command injection"""
        if not re.match(r'^[a-zA-Z0-9_\-\.@]+$', v):
            raise ValueError("Username contains invalid characters")
        return v


class ServerCredentialCreate(ServerCredentialBase):
    """Create server credential - includes passwords"""
    password: Optional[str] = Field(None, min_length=1)
    ssh_key_id: Optional[int] = Field(None, gt=0)
    sudo_password: Optional[str] = Field(None, min_length=1)
    
    @field_validator("password", "sudo_password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate password if provided"""
        if v is not None and len(v) < 1:
            raise ValueError("Password cannot be empty if provided")
        return v


class ServerCredentialUpdate(BaseModel):
    """Update server credential"""
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=1)
    ssh_key_id: Optional[int] = Field(None, gt=0)
    sudo_password: Optional[str] = Field(None, min_length=1)


class ServerCredentialResponse(ServerCredentialBase):
    """Server credential response - passwords excluded for security"""
    id: int
    ssh_key_id: Optional[int]
    created_by: Optional[int]
    created_at: datetime
    last_used: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class ServerCredentialWithSecrets(ServerCredentialResponse):
    """Server credential with decrypted passwords - only for authorized access"""
    password: Optional[str]
    sudo_password: Optional[str]


# ============================================================
# Audit Log Schemas
# ============================================================

class CredentialAuditLogResponse(BaseModel):
    """Credential audit log response"""
    id: int
    action: str
    resource_type: str
    resource_id: int
    user_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[str]
    success: bool
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Utility Schemas
# ============================================================

class CredentialStats(BaseModel):
    """Statistics about credentials"""
    total_ssh_keys: int
    total_certificates: int
    total_credentials: int
    expiring_certificates: int
    unused_keys: int


class CertificateRenewalRequest(BaseModel):
    """Request certificate renewal"""
    certificate: str
    private_key: Optional[str] = None
    chain: Optional[str] = None
