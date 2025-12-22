"""
Pydantic schemas for notification API.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class NotificationChannelBase(BaseModel):
    """Base schema for notification channel."""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    apprise_url: str
    service_type: str = Field(..., max_length=50)
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None


class NotificationChannelCreate(NotificationChannelBase):
    """Schema for creating a notification channel."""
    pass


class NotificationChannelUpdate(BaseModel):
    """Schema for updating a notification channel."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    apprise_url: Optional[str] = None
    service_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class NotificationChannelResponse(NotificationChannelBase):
    """Schema for notification channel response."""
    id: UUID
    success_count: int
    failure_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True


class SendNotificationRequest(BaseModel):
    """Schema for sending a notification."""
    title: str = Field(..., max_length=255)
    body: str
    channel_ids: Optional[List[UUID]] = None  # None = send to all active channels
    trigger_type: Optional[str] = Field(None, max_length=50)
    trigger_id: Optional[str] = Field(None, max_length=100)


class NotificationResult(BaseModel):
    """Result of sending to a single channel."""
    channel_id: str
    channel_name: str
    success: bool
    error: Optional[str] = None


class SendNotificationResponse(BaseModel):
    """Response from sending notifications."""
    success: bool
    message: str
    results: List[NotificationResult]


class NotificationLogResponse(BaseModel):
    """Schema for notification log."""
    id: UUID
    channel_id: Optional[UUID] = None
    title: str
    body: str
    success: bool
    error_message: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_id: Optional[str] = None
    sent_at: datetime
    
    class Config:
        from_attributes = True


class SupportedServiceResponse(BaseModel):
    """Schema for supported notification services."""
    type: str
    name: str
    url_format: str
