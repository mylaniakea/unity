"""
OAuth authentication models.

Links external OAuth providers (GitHub, Google, etc.) to local user accounts.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserOAuthLink(Base):
    """
    Links a user account to an external OAuth provider.
    
    Allows users to sign in with GitHub, Google, etc. and links those
    identities to their local Unity account.
    """
    __tablename__ = "user_oauth_links"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to local user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # OAuth provider info
    provider = Column(String(50), nullable=False, index=True)  # github, google, etc.
    provider_user_id = Column(String(255), nullable=False)  # User ID from provider
    provider_username = Column(String(255), nullable=True)  # Username from provider
    provider_email = Column(String(255), nullable=True)  # Email from provider
    
    # OAuth tokens (encrypted in production!)
    access_token = Column(Text, nullable=True)  # TODO: Encrypt this
    refresh_token = Column(Text, nullable=True)  # TODO: Encrypt this
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Profile data from provider
    profile_data = Column(Text, nullable=True)  # JSON string of profile data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="oauth_links")
    
    # Ensure one OAuth account can only be linked to one Unity user
    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user'),
    )
    
    def __repr__(self):
        return f"<UserOAuthLink(user_id={self.user_id}, provider='{self.provider}', provider_username='{self.provider_username}')>"
