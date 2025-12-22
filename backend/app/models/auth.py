"""
Authentication and authorization database models.

This module contains models for:
- API keys for programmatic access
- Audit logs for security tracking
- User role enum for RBAC
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class APIKey(Base):
    """
    API Key model for programmatic authentication.
    
    Keys are hashed before storage for security. The plaintext key
    is only shown once during creation.
    """
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String, nullable=False, index=True, unique=True)
    name = Column(String(100), nullable=False)
    scopes = Column(JSON, nullable=True)  # Works with both PostgreSQL and SQLite
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey(name='{self.name}', user_id={self.user_id}, active={self.is_active})>"


class AuditLog(Base):
    """
    Audit log for tracking authentication and authorization events.
    
    Captures all security-relevant actions for compliance and troubleshooting.
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # login, logout, api_key_created, etc.
    resource_type = Column(String(50), nullable=True)  # user, api_key, plugin, etc.
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)  # Works with both PostgreSQL and SQLite
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user_id={self.user_id}, success={self.success})>"
