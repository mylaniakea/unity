"""
Notification models for Unity.

Supports 78+ notification channels via Apprise integration.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationChannel(Base):
    """
    Notification channel configuration.
    
    Stores Apprise URL and metadata for each notification destination.
    Supports 78+ services including email, Slack, Discord, webhooks, etc.
    """
    __tablename__ = "notification_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Apprise URL format (e.g., "mailto://user:pass@gmail.com", "slack://token/channel")
    apprise_url = Column(Text, nullable=False)
    
    # Service type for UI display (email, slack, discord, webhook, etc.)
    service_type = Column(String(50), nullable=False, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Configuration metadata (optional service-specific settings)
    config = Column(JSON, nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Optional: Link to user who created it
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    def __repr__(self):
        return f"<NotificationChannel(name='{self.name}', type='{self.service_type}', active={self.is_active})>"


class NotificationLog(Base):
    """
    Log of sent notifications for debugging and audit trail.
    """
    __tablename__ = "notification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("notification_channels.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Context about what triggered the notification
    trigger_type = Column(String(50), nullable=True)  # alert, test, manual
    trigger_id = Column(String(100), nullable=True)  # ID of the alert or other trigger
    
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<NotificationLog(title='{self.title}', success={self.success}, sent_at={self.sent_at})>"
