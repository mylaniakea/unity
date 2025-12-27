"""Alert Lifecycle Service

Manages alert state transitions and integrates with notification system.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.monitoring import Alert, AlertChannel
from app.models.alert_rules import AlertRule, AlertStatus
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)


def get_websocket_module():
    """Lazy import WebSocket module to avoid circular dependencies."""
    try:
        from app.api import websocket
        return websocket
    except ImportError:
        return None


class AlertLifecycleService:
    """Service for managing alert lifecycle and notifications."""
    
    def __init__(self, db: Session, notification_service: Optional[NotificationService] = None):
        self.db = db
        self.notification_service = notification_service or NotificationService(db)
    
    def trigger_alert(
        self,
        rule: AlertRule,
        resource,
        metric_value: float,
        metric_name: str
    ) -> Optional[Alert]:
        """
        Trigger a new alert if conditions are met.
        
        Args:
            rule: The alert rule that triggered
            resource: The resource (server, device, pool, database) that triggered
            metric_value: The actual metric value
            metric_name: The name of the metric
            
        Returns:
            The created Alert object, or None if cooldown is active
        """
        # Check for existing active alert
        existing_alert = self.db.query(Alert).filter(
            Alert.alert_rule_id == rule.id,
            Alert.resource_id == resource.id,
            Alert.resource_type == rule.resource_type.value,
            Alert.status == AlertStatus.ACTIVE.value
        ).first()
        
        if existing_alert:
            logger.debug(f"Alert already active for rule {rule.id}, resource {resource.id}")
            return None
        
        # Check cooldown
        if not self.check_cooldown(rule, resource):
            logger.debug(f"Alert cooldown active for rule {rule.id}, resource {resource.id}")
            return None
        
        # Create alert
        alert = Alert(
            alert_rule_id=rule.id,
            resource_type=rule.resource_type.value,
            resource_id=resource.id,
            severity=rule.severity.value,
            alert_type="infrastructure",
            message=self._format_alert_message(rule, resource, metric_value),
            metric_value=int(metric_value),
            threshold=rule.threshold,
            status=AlertStatus.ACTIVE.value,
            triggered_at=datetime.utcnow()
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Alert triggered: {alert.id} for rule {rule.name}")
        
        # Send notifications
        self._send_alert_notifications(alert, rule, "triggered")
        
        # Broadcast via WebSocket
        self._broadcast_alert(alert, "triggered")
        
        return alert
    
    def acknowledge_alert(self, alert_id: int, user_id: Optional[str] = None) -> Optional[Alert]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            user_id: User who is acknowledging (optional)
            
        Returns:
            The updated Alert object, or None if not found
        """
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return None
        
        if alert.status == AlertStatus.ACKNOWLEDGED.value:
            logger.debug(f"Alert {alert_id} already acknowledged")
            return alert
        
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user_id or "system"
        alert.status = AlertStatus.ACKNOWLEDGED.value
        
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Alert {alert_id} acknowledged by {user_id or 'system'}")
        
        # Send acknowledgment notification
        if alert.alert_rule_id:
            rule = self.db.query(AlertRule).filter(AlertRule.id == alert.alert_rule_id).first()
            if rule:
                self._send_alert_notifications(alert, rule, "acknowledged")
        
        # Broadcast via WebSocket
        self._broadcast_alert(alert, "acknowledged")
        
        return alert
    
    def resolve_alert(self, alert_id: int, user_id: Optional[str] = None) -> Optional[Alert]:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of the alert to resolve
            user_id: User who is resolving (optional)
            
        Returns:
            The updated Alert object, or None if not found
        """
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return None
        
        if alert.status == AlertStatus.RESOLVED.value:
            logger.debug(f"Alert {alert_id} already resolved")
            return alert
        
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.status = AlertStatus.RESOLVED.value
        
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Alert {alert_id} resolved")
        
        # Send resolution notification
        if alert.alert_rule_id:
            rule = self.db.query(AlertRule).filter(AlertRule.id == alert.alert_rule_id).first()
            if rule:
                self._send_alert_notifications(alert, rule, "resolved")
        
        # Broadcast via WebSocket
        self._broadcast_alert(alert, "resolved")
        
        return alert
    
    def snooze_alert(self, alert_id: int, duration_minutes: int) -> Optional[Alert]:
        """
        Snooze an alert for a specified duration.
        
        Args:
            alert_id: ID of the alert to snooze
            duration_minutes: How long to snooze (in minutes)
            
        Returns:
            The updated Alert object, or None if not found
        """
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return None
        
        alert.snoozed_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Alert {alert_id} snoozed until {alert.snoozed_until}")
        
        return alert
    
    def auto_resolve_alert(self, rule: AlertRule, resource) -> bool:
        """
        Auto-resolve an alert when conditions are no longer met.
        
        Args:
            rule: The alert rule
            resource: The resource
            
        Returns:
            True if an alert was resolved, False otherwise
        """
        alert = self.db.query(Alert).filter(
            Alert.alert_rule_id == rule.id,
            Alert.resource_id == resource.id,
            Alert.resource_type == rule.resource_type.value,
            Alert.status == AlertStatus.ACTIVE.value
        ).first()
        
        if alert:
            self.resolve_alert(alert.id, "auto-resolved")
            return True
        
        return False
    
    def check_cooldown(self, rule: AlertRule, resource) -> bool:
        """
        Check if cooldown period has elapsed since last alert.
        
        Args:
            rule: The alert rule
            resource: The resource
            
        Returns:
            True if cooldown has elapsed (OK to trigger), False otherwise
        """
        if rule.cooldown_minutes <= 0:
            return True
        
        cooldown_time = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
        
        recent_alert = self.db.query(Alert).filter(
            Alert.alert_rule_id == rule.id,
            Alert.resource_id == resource.id,
            Alert.resource_type == rule.resource_type.value,
            Alert.triggered_at >= cooldown_time
        ).first()
        
        return recent_alert is None
    
    def _format_alert_message(self, rule: AlertRule, resource, metric_value: float) -> str:
        """Format alert message."""
        resource_name = getattr(resource, 'name', getattr(resource, 'hostname', f'Resource {resource.id}'))
        condition_str = self._condition_to_string(rule.condition.value)
        
        return (
            f"{rule.name}: {rule.resource_type.value.title()} '{resource_name}' "
            f"{rule.metric_name}={metric_value} {condition_str} {rule.threshold}"
        )
    
    def _condition_to_string(self, condition: str) -> str:
        """Convert condition enum to readable string."""
        mapping = {
            "gt": ">",
            "lt": "<",
            "gte": ">=",
            "lte": "<=",
            "eq": "==",
            "ne": "!="
        }
        return mapping.get(condition, condition)
    
    def _send_alert_notifications(self, alert: Alert, rule: AlertRule, action: str):
        """
        Send notifications for alert state changes.
        
        Args:
            alert: The alert object
            rule: The alert rule
            action: The action that occurred (triggered, acknowledged, resolved)
        """
        if not rule.notification_channels:
            logger.debug(f"No notification channels configured for rule {rule.id}")
            return
        
        # Build notification title and body
        action_emoji = {
            "triggered": "🚨",
            "acknowledged": "👀",
            "resolved": "✅"
        }
        
        title = f"{action_emoji.get(action, '⚠️')} Alert {action.title()}: {rule.name}"
        body = f"""
Alert ID: {alert.id}
Severity: {alert.severity.upper()}
Resource: {alert.resource_type} (ID: {alert.resource_id})
Message: {alert.message}
Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Status: {alert.status}
""".strip()
        
        try:
            # Get channel IDs from rule configuration
            # rule.notification_channels can be a list of channel IDs or names
            channel_ids = rule.notification_channels if isinstance(rule.notification_channels, list) else []
            
            # Send notification
            result = self.notification_service.send_notification(
                title=title,
                body=body,
                channel_ids=channel_ids if channel_ids else None,  # None = all active channels
                trigger_type="alert",
                trigger_id=str(alert.id)
            )
            
            logger.info(f"Notification sent for alert {alert.id}: {result.get('message', 'Unknown result')}")
            
        except Exception as e:
            logger.error(f"Failed to send notification for alert {alert.id}: {e}", exc_info=True)
    
    def _broadcast_alert(self, alert: Alert, action: str):
        """
        Broadcast alert updates via WebSocket.
        
        Args:
            alert: The alert object
            action: The action that occurred (triggered, acknowledged, resolved)
        """
        ws = get_websocket_module()
        if not ws:
            return
        
        try:
            alert_data = {
                "id": alert.id,
                "alert_rule_id": alert.alert_rule_id,
                "resource_type": alert.resource_type,
                "resource_id": alert.resource_id,
                "severity": alert.severity,
                "message": alert.message,
                "status": alert.status,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "action": action
            }
            
            # Use asyncio to call async function from sync context
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If loop is already running, schedule the coroutine
                asyncio.create_task(ws.broadcast_alert(alert_data))
            else:
                # If no loop is running, run it
                loop.run_until_complete(ws.broadcast_alert(alert_data))
                
        except Exception as e:
            logger.debug(f"WebSocket broadcast skipped for alert {alert.id}: {e}")
