from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.database import Base



class SSHKey(Base):
    """SSH key pairs for server authentication"""
    __tablename__ = "ssh_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Keys (encrypted)
    public_key = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)  # Encrypted with Fernet
    
    # Key metadata
    key_type = Column(String(50), default="rsa")  # rsa, ed25519, etc.
    key_size = Column(Integer, nullable=True)  # 2048, 4096 for RSA
    fingerprint = Column(String(255), nullable=True)
    
    # Ownership and access
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)


class Certificate(Base):
    """SSL/TLS certificates"""
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Certificate data (encrypted)
    certificate = Column(Text, nullable=False)  # PEM format
    private_key = Column(Text, nullable=False)  # PEM format, encrypted
    certificate_chain = Column(Text, nullable=True)  # Full chain if available
    
    # Certificate metadata
    common_name = Column(String(255), nullable=True)
    subject_alt_names = Column(JSON().with_variant(JSONB, "postgresql"), default=[])  # List of SANs
    issuer = Column(String(255), nullable=True)
    
    # Validity
    not_before = Column(DateTime(timezone=True), nullable=True)
    not_after = Column(DateTime(timezone=True), nullable=True)
    is_expired = Column(Boolean, default=False)
    
    # Provider info
    provider = Column(String(50), default="manual")  # manual, step-ca, letsencrypt, etc.
    provider_order_id = Column(String(255), nullable=True)  # External provider reference
    
    # Auto-renewal
    auto_renew = Column(Boolean, default=False)
    renewal_days_before = Column(Integer, default=30)
    last_renewal_attempt = Column(DateTime(timezone=True), nullable=True)
    renewal_status = Column(String(50), nullable=True)  # success, failed, pending
    
    # Ownership
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ServerCredential(Base):
    """Server connection credentials"""
    __tablename__ = "server_credentials"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to Unity's ServerProfile
    server_profile_id = Column(Integer, ForeignKey('server_profiles.id'), nullable=False, unique=True)
    
    # Credentials (encrypted)
    username = Column(String(255), nullable=True)
    password = Column(Text, nullable=True)  # Encrypted with Fernet
    
    # SSH Key association
    ssh_key_id = Column(Integer, ForeignKey('ssh_keys.id'), nullable=True)
    
    # Additional connection details
    port = Column(Integer, default=22)
    connection_type = Column(String(50), default="ssh")  # ssh, winrm, etc.
    
    # Metadata
    notes = Column(Text, nullable=True)
    
    # Ownership
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)


class StepCAConfig(Base):
    """Step-CA certificate authority configuration"""
    __tablename__ = "step_ca_config"

    id = Column(Integer, primary_key=True)
    
    # Step-CA connection details
    ca_url = Column(String(255), nullable=False)
    ca_fingerprint = Column(String(255), nullable=False)
    provisioner_name = Column(String(255), nullable=False)
    provisioner_password = Column(Text, nullable=False)  # Encrypted
    
    # Configuration
    default_validity_days = Column(Integer, default=90)
    enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CredentialAuditLog(Base):
    """Audit log for credential operations"""
    __tablename__ = "credential_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(255), nullable=True)  # Denormalized for history
    
    # What
    action = Column(String(100), nullable=False, index=True)  # create, read, update, delete, rotate, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # ssh_key, certificate, credential
    resource_id = Column(Integer, nullable=True)
    resource_name = Column(String(255), nullable=True)
    
    # When
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # How
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Details
    details = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Additional context
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

# ============================================================================
# Infrastructure Monitoring Models (Phase 3: BD-Store Integration)
# ============================================================================

import enum
from sqlalchemy import Enum, BigInteger, Float


