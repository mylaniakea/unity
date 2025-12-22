"""
Notification service using Apprise for 78+ notification channels.

Supports: Email, Slack, Discord, Telegram, webhooks, and many more.
"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
import apprise
from sqlalchemy.orm import Session
from app.models.notifications import NotificationChannel, NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications through multiple channels using Apprise.
    
    Apprise supports 78+ notification services out of the box.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.apprise_obj = apprise.Apprise()
    
    async def send_notification(
        self,
        title: str,
        body: str,
        channel_ids: Optional[List[str]] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a notification through one or more channels.
        
        Args:
            title: Notification title
            body: Notification body/message
            channel_ids: List of channel IDs to send through (None = all active)
            trigger_type: What triggered this notification (alert, test, manual)
            trigger_id: ID of the trigger (e.g., alert ID)
        
        Returns:
            Dict with success status and results per channel
        """
        # Get channels to send through
        query = self.db.query(NotificationChannel).filter(
            NotificationChannel.is_active == True
        )
        
        if channel_ids:
            # Convert string IDs to UUIDs
            uuid_ids = [uuid.UUID(cid) if isinstance(cid, str) else cid for cid in channel_ids]
            query = query.filter(NotificationChannel.id.in_(uuid_ids))
        
        channels = query.all()
        
        if not channels:
            logger.warning("No active notification channels found")
            return {
                "success": False,
                "message": "No active notification channels configured",
                "results": []
            }
        
        results = []
        overall_success = True
        
        for channel in channels:
            try:
                # Create Apprise instance for this channel
                apobj = apprise.Apprise()
                apobj.add(channel.apprise_url)
                
                # Send notification
                success = apobj.notify(
                    title=title,
                    body=body,
                )
                
                if success:
                    channel.success_count += 1
                    channel.last_used_at = datetime.utcnow()
                    error_msg = None
                else:
                    channel.failure_count += 1
                    error_msg = "Notification failed (Apprise returned False)"
                    overall_success = False
                
                # Log the notification
                log_entry = NotificationLog(
                    channel_id=channel.id,
                    title=title,
                    body=body,
                    success=success,
                    error_message=error_msg,
                    trigger_type=trigger_type,
                    trigger_id=trigger_id,
                )
                self.db.add(log_entry)
                
                results.append({
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                    "success": success,
                    "error": error_msg
                })
                
                logger.info(
                    f"Notification {'sent' if success else 'failed'} via {channel.name} "
                    f"({channel.service_type})"
                )
                
            except Exception as e:
                logger.error(f"Error sending notification via {channel.name}: {e}")
                channel.failure_count += 1
                overall_success = False
                
                # Log failed attempt
                log_entry = NotificationLog(
                    channel_id=channel.id,
                    title=title,
                    body=body,
                    success=False,
                    error_message=str(e),
                    trigger_type=trigger_type,
                    trigger_id=trigger_id,
                )
                self.db.add(log_entry)
                
                results.append({
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                    "success": False,
                    "error": str(e)
                })
        
        self.db.commit()
        
        return {
            "success": overall_success,
            "message": f"Sent to {len(results)} channel(s)",
            "results": results
        }
    
    async def test_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Test a specific notification channel.
        
        Args:
            channel_id: ID of the channel to test
        
        Returns:
            Dict with test results
        """
        channel = self.db.query(NotificationChannel).filter(
            NotificationChannel.id == (uuid.UUID(channel_id) if isinstance(channel_id, str) else channel_id)
        ).first()
        
        if not channel:
            return {
                "success": False,
                "message": "Channel not found"
            }
        
        result = await self.send_notification(
            title="Unity Test Notification",
            body=f"This is a test notification from Unity sent via {channel.name}.",
            channel_ids=[channel_id],
            trigger_type="test",
        )
        
        return result
    
    def get_channels(self, active_only: bool = True) -> List[NotificationChannel]:
        """Get all configured notification channels."""
        query = self.db.query(NotificationChannel)
        
        if active_only:
            query = query.filter(NotificationChannel.is_active == True)
        
        return query.all()
    
    def get_channel_by_id(self, channel_id: str) -> Optional[NotificationChannel]:
        """Get a specific channel by ID."""
        return self.db.query(NotificationChannel).filter(
            NotificationChannel.id == (uuid.UUID(channel_id) if isinstance(channel_id, str) else channel_id)
        ).first()
    
    def create_channel(
        self,
        name: str,
        apprise_url: str,
        service_type: str,
        description: Optional[str] = None,
        is_active: bool = True,
        config: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[str] = None,
    ) -> NotificationChannel:
        """
        Create a new notification channel.
        
        Args:
            name: Display name for the channel
            apprise_url: Apprise URL format (e.g., mailto://user:pass@host)
            service_type: Type of service (email, slack, discord, etc.)
            description: Optional description
            is_active: Whether channel is active
            config: Optional configuration metadata
            created_by_id: ID of user who created it
        
        Returns:
            Created NotificationChannel
        """
        channel = NotificationChannel(
            name=name,
            apprise_url=apprise_url,
            service_type=service_type,
            description=description,
            is_active=is_active,
            config=config,
            created_by_id=created_by_id,
        )
        
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        
        logger.info(f"Created notification channel: {name} ({service_type})")
        
        return channel
    
    def update_channel(
        self,
        channel_id: str,
        **kwargs
    ) -> Optional[NotificationChannel]:
        """Update a notification channel."""
        channel = self.get_channel_by_id(channel_id)
        
        if not channel:
            return None
        
        for key, value in kwargs.items():
            if hasattr(channel, key):
                setattr(channel, key, value)
        
        self.db.commit()
        self.db.refresh(channel)
        
        logger.info(f"Updated notification channel: {channel.name}")
        
        return channel
    
    def delete_channel(self, channel_id: str) -> bool:
        """Delete a notification channel."""
        channel = self.get_channel_by_id(channel_id)
        
        if not channel:
            return False
        
        self.db.delete(channel)
        self.db.commit()
        
        logger.info(f"Deleted notification channel: {channel.name}")
        
        return True
    
    def get_notification_logs(
        self,
        channel_id: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationLog]:
        """Get recent notification logs."""
        query = self.db.query(NotificationLog).order_by(
            NotificationLog.sent_at.desc()
        )
        
        if channel_id:
            query = query.filter(NotificationLog.channel_id == (uuid.UUID(channel_id) if isinstance(channel_id, str) else channel_id))
        
        return query.limit(limit).all()
    
    @staticmethod
    def get_supported_services() -> List[Dict[str, str]]:
        """
        Get list of supported notification services.
        
        Returns a curated list of popular services. Apprise supports 78+ total.
        """
        return [
            {"type": "email", "name": "Email (SMTP)", "url_format": "mailto://user:pass@host"},
            {"type": "slack", "name": "Slack", "url_format": "slack://token/channel"},
            {"type": "discord", "name": "Discord", "url_format": "discord://webhook_id/webhook_token"},
            {"type": "telegram", "name": "Telegram", "url_format": "tgram://bot_token/chat_id"},
            {"type": "webhook", "name": "Generic Webhook", "url_format": "json://webhook_url"},
            {"type": "msteams", "name": "Microsoft Teams", "url_format": "msteams://webhook_url"},
            {"type": "matrix", "name": "Matrix", "url_format": "matrix://user:pass@host/room"},
            {"type": "pushover", "name": "Pushover", "url_format": "pover://user@token"},
            {"type": "gotify", "name": "Gotify", "url_format": "gotify://host/token"},
            {"type": "ntfy", "name": "ntfy", "url_format": "ntfy://host/topic"},
            {"type": "pagerduty", "name": "PagerDuty", "url_format": "pagerduty://integration_key"},
            {"type": "pushbullet", "name": "Pushbullet", "url_format": "pbul://access_token"},
            # Many more supported - see Apprise docs
        ]


def get_notification_service(db: Session) -> NotificationService:
    """Factory function to get NotificationService instance."""
    return NotificationService(db)
