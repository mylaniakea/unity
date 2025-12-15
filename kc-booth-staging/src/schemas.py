from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Union
import re
import ipaddress

class SSHKeyBase(BaseModel):
    name: str
    public_key: str

class SSHKeyCreate(SSHKeyBase):
    private_key: str
    
    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, v: str) -> str:
        """Validate SSH public key format."""
        # Basic validation - should start with ssh-rsa, ssh-ed25519, etc.
        if not v.startswith(("ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2-")):
            raise ValueError("Invalid SSH public key format")
        # Check for basic structure
        parts = v.split()
        if len(parts) < 2:
            raise ValueError("SSH public key must have at least key type and key data")
        return v
    
    @field_validator("private_key")
    @classmethod
    def validate_private_key(cls, v: str) -> str:
        """Validate SSH private key format."""
        if not ("BEGIN" in v and "PRIVATE KEY" in v and "END" in v):
            raise ValueError("Invalid SSH private key format")
        return v

class SSHKey(SSHKeyBase):
    """SSH Key response model - private_key is excluded for security."""
    id: int
    model_config = ConfigDict(from_attributes=True)

class ServerBase(BaseModel):
    hostname: str
    ip_address: str
    username: str
    
    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        """Validate hostname to prevent command injection."""
        # Allow alphanumeric, dots, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\.\-_]+$', v):
            raise ValueError("Hostname contains invalid characters")
        if len(v) > 253:
            raise ValueError("Hostname too long")
        return v
    
    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address format")
        return v
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username to prevent command injection."""
        # Allow alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Username contains invalid characters")
        if len(v) > 32:
            raise ValueError("Username too long")
        return v

class ServerCreate(ServerBase):
    password: str
    ssh_key_id: Union[int, None] = None

class Server(ServerBase):
    """Server response model - password is excluded for security."""
    id: int
    ssh_key_id: Union[int, None] = None
    model_config = ConfigDict(from_attributes=True)

class CertificateBase(BaseModel):
    certificate: str
    key: str

class CertificateCreate(CertificateBase):
    expires_at: datetime
    server_id: int

class Certificate(CertificateBase):
    id: int
    expires_at: datetime
    server_id: int
    model_config = ConfigDict(from_attributes=True)
