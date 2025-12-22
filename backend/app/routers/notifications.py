"""
Notification API endpoints.

Provides endpoints for managing notification channels and sending notifications.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.services.notifications import get_notification_service, NotificationService
from app.schemas.notifications import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    NotificationLogResponse,
    SupportedServiceResponse,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/services", response_model=List[SupportedServiceResponse])
async def get_supported_services():
    """
    Get list of supported notification services.
    
    Apprise supports 78+ services including:
    - Email (SMTP)
    - Slack
    - Discord
    - Telegram
    - Microsoft Teams
    - Webhooks
    - And many more...
    """
    return NotificationService.get_supported_services()


@router.get("/channels", response_model=List[NotificationChannelResponse])
async def list_channels(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all notification channels."""
    service = get_notification_service(db)
    channels = service.get_channels(active_only=active_only)
    return channels


@router.post("/channels", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: NotificationChannelCreate,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user),  # TODO: Add auth
):
    """
    Create a new notification channel.
    
    Example Apprise URLs:
    - Email: mailto://user:pass@gmail.com
    - Slack: slack://token/channel
    - Discord: discord://webhook_id/webhook_token
    - Webhook: json://webhook_url
    """
    service = get_notification_service(db)
    
    channel = service.create_channel(
        name=channel_data.name,
        apprise_url=channel_data.apprise_url,
        service_type=channel_data.service_type,
        description=channel_data.description,
        config=channel_data.config,
        # created_by_id=current_user.id,  # TODO: Add after auth
    )
    
    return channel


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a specific notification channel by ID."""
    service = get_notification_service(db)
    channel = service.get_channel_by_id(str(channel_id))
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    return channel


@router.patch("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(
    channel_id: UUID,
    channel_data: NotificationChannelUpdate,
    db: Session = Depends(get_db),
):
    """Update a notification channel."""
    service = get_notification_service(db)
    
    # Filter out None values
    update_data = {k: v for k, v in channel_data.dict().items() if v is not None}
    
    channel = service.update_channel(str(channel_id), **update_data)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    return channel


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a notification channel."""
    service = get_notification_service(db)
    
    success = service.delete_channel(str(channel_id))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )


@router.post("/channels/{channel_id}/test", response_model=SendNotificationResponse)
async def test_channel(
    channel_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Test a notification channel by sending a test message.
    """
    service = get_notification_service(db)
    
    result = await service.test_channel(str(channel_id))
    
    if not result.get("success") and "not found" in result.get("message", "").lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found"
        )
    
    return result


@router.post("/send", response_model=SendNotificationResponse)
async def send_notification(
    notification: SendNotificationRequest,
    db: Session = Depends(get_db),
):
    """
    Send a notification through configured channels.
    
    If channel_ids is not provided, sends through all active channels.
    """
    service = get_notification_service(db)
    
    # Convert UUIDs to strings
    channel_ids = [str(cid) for cid in notification.channel_ids] if notification.channel_ids else None
    
    result = await service.send_notification(
        title=notification.title,
        body=notification.body,
        channel_ids=channel_ids,
        trigger_type=notification.trigger_type,
        trigger_id=notification.trigger_id,
    )
    
    return result


@router.get("/logs", response_model=List[NotificationLogResponse])
async def get_notification_logs(
    channel_id: Optional[UUID] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get recent notification logs.
    
    Optionally filter by channel_id.
    """
    service = get_notification_service(db)
    
    logs = service.get_notification_logs(
        channel_id=str(channel_id) if channel_id else None,
        limit=limit
    )
    
    return logs
