"""
Threshold Monitoring Service
Checks server metrics against threshold rules and triggers alerts
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
from app import models
from app.services.notification_service import NotificationService
from app.services.push_notifications import send_push_notification

logger = logging.getLogger(__name__)

class ThresholdMonitor:
    """Service for monitoring thresholds and triggering alerts"""

    def __init__(self, db: Session, tenant_id: str = "default"):
        self.db = db
        self.notification_service = NotificationService()

    async def check_all_thresholds(self):
        """Check all enabled threshold rules against current server metrics"""
        logger.info("Starting threshold monitoring check...")

        # Check for maintenance mode
        settings = self.db.query(models.Settings).first()
        if settings and settings.maintenance_mode_until and settings.maintenance_mode_until > datetime.now():
            logger.info(f"Maintenance mode is active until {settings.maintenance_mode_until}. Skipping all threshold checks.")
            return

        # Get all enabled threshold rules
        rules = self.db.query(models.ThresholdRule).filter(models.ThresholdRule.tenant_id == tenant_id).filter(
            models.ThresholdRule.enabled == True
        ).all()

        logger.info(f"Found {len(rules)} enabled threshold rules")

        for rule in rules:
            try:
                await self._check_rule(rule)
            except Exception as e:
                logger.error(f"Error checking rule {rule.id} ({rule.name}): {e}")

        logger.info("Threshold monitoring check completed")

    async def _check_rule(self, rule: models.ThresholdRule):
        """Check a single threshold rule"""
        if rule.muted_until and rule.muted_until > datetime.now():
            logger.info(f"Rule {rule.id} ({rule.name}) is muted until {rule.muted_until}, skipping.")
            return
        # Get servers to check (specific server or all servers)
        if rule.server_id:
            servers = [self.db.query(models.ServerProfile).filter(models.ServerProfile.tenant_id == tenant_id).filter(
                models.ServerProfile.id == rule.server_id
            ).first()]
            if not servers[0]:
                logger.warning(f"Server {rule.server_id} not found for rule {rule.id}")
                return
        else:
            servers = self.db.query(models.ServerProfile).filter(models.ServerProfile.tenant_id == tenant_id).all()

        for server in servers:
            try:
                await self._check_server_metric(rule, server)
            except Exception as e:
                logger.error(f"Error checking server {server.id} for rule {rule.id}: {e}")

    async def _check_server_metric(self, rule: models.ThresholdRule, server: models.ServerProfile):
        """Check if a server's metric exceeds the threshold"""
        # Get latest snapshot for the server
        latest_snapshot = self.db.query(models.ServerSnapshot).filter(models.ServerSnapshot.tenant_id == tenant_id).filter(
            models.ServerSnapshot.server_id == server.id
        ).order_by(models.ServerSnapshot.timestamp.desc()).first()

        if not latest_snapshot:
            logger.debug(f"No snapshot found for server {server.id}")
            return

        # Extract metric value from snapshot data
        metric_value = self._extract_metric_value(rule.metric, latest_snapshot.data)

        if metric_value is None:
            logger.debug(f"Metric {rule.metric} not found in snapshot for server {server.id}")
            return

        # Check if threshold is exceeded
        threshold_exceeded = self._evaluate_condition(
            metric_value,
            rule.condition,
            rule.threshold_value
        )

        if threshold_exceeded:
            # Check if we already have a recent unresolved alert for this rule+server
            # (avoid alert spam - don't create duplicate alerts within 5 minutes)
            recent_alert = self.db.query(models.Alert).filter(models.Alert.tenant_id == tenant_id).filter(
                and_(
                    models.Alert.rule_id == rule.id,
                    models.Alert.server_id == server.id,
                    models.Alert.resolved == False,
                    # Only consider non-snoozed alerts for duplication check, or if snooze has expired
                    and_(
                        models.Alert.snoozed_until == None,
                        models.Alert.snoozed_until < datetime.now()
                    ),
                    models.Alert.triggered_at >= datetime.now() - timedelta(minutes=5)
                )
            ).first()

            if recent_alert:
                logger.debug(f"Recent alert exists for rule {rule.id} on server {server.id}, skipping")
                return

            # Create alert
            await self._create_alert(rule, server, metric_value)

    def _extract_metric_value(self, metric: str, snapshot_data: Dict[str, Any]) -> float | None:
        """Extract metric value from snapshot data"""
        try:
            # Map metric names to snapshot data paths
            if metric == 'cpu_percent':
                return snapshot_data.get('cpu', {}).get('percent')
            elif metric == 'memory_percent':
                mem = snapshot_data.get('memory', {})
                if mem.get('total'):
                    return (mem.get('used', 0) / mem.get('total')) * 100
            elif metric == 'disk_percent':
                disks = snapshot_data.get('disk', [])
                if disks and len(disks) > 0:
                    # Check highest disk usage
                    max_usage = 0
                    for disk in disks:
                        if disk.get('percent'):
                            max_usage = max(max_usage, disk['percent'])
                    return max_usage if max_usage > 0 else None
            elif metric == 'disk_io_read':
                io = snapshot_data.get('disk_io', {})
                return io.get('read_mb_s')
            elif metric == 'disk_io_write':
                io = snapshot_data.get('disk_io', {})
                return io.get('write_mb_s')
            elif metric == 'network_sent':
                net = snapshot_data.get('network', {})
                return net.get('bytes_sent_mb_s')
            elif metric == 'network_recv':
                net = snapshot_data.get('network', {})
                return net.get('bytes_recv_mb_s')
            elif metric == 'temperature':
                temps = snapshot_data.get('temperatures', [])
                if temps and len(temps) > 0:
                    # Check highest temperature
                    max_temp = 0
                    for temp in temps:
                        if temp.get('current'):
                            max_temp = max(max_temp, temp['current'])
                    return max_temp if max_temp > 0 else None

            return None
        except Exception as e:
            logger.error(f"Error extracting metric {metric}: {e}")
            return None

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate if condition is met"""
        if condition == 'greater_than':
            return value > threshold
        elif condition == 'less_than':
            return value < threshold
        elif condition == 'equal_to':
            return abs(value - threshold) < 0.01  # Allow small floating point differences
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False

    async def _create_alert(self, rule: models.ThresholdRule, server: models.ServerProfile, metric_value: float):
        """Create a new alert and send notifications"""
        # Generate alert message
        metric_labels = {
            'cpu_percent': 'CPU Usage',
            'memory_percent': 'Memory Usage',
            'disk_percent': 'Disk Usage',
            'disk_io_read': 'Disk Read I/O',
            'disk_io_write': 'Disk Write I/O',
            'network_sent': 'Network Sent',
            'network_recv': 'Network Received',
            'temperature': 'Temperature'
        }

        metric_label = metric_labels.get(rule.metric, rule.metric)
        message = f"{metric_label} on {server.name}: {int(metric_value)}"

        if rule.metric in ['cpu_percent', 'memory_percent', 'disk_percent']:
            message += '%'
        elif rule.metric in ['disk_io_read', 'disk_io_write', 'network_sent', 'network_recv']:
            message += ' MB/s'
        elif rule.metric == 'temperature':
            message += '°C'

        message += f" (threshold: {rule.threshold_value})"

        # Create alert record
        alert = models.Alert(
            rule_id=rule.id,
            server_id=server.id,
            severity=rule.severity,
            message=message,
            metric_value=int(metric_value),
            triggered_at=datetime.now()
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert created: {message} (Alert ID: {alert.id})")

        # Send notifications through all enabled channels
        await self._send_notifications(alert, server, rule)

    async def _send_notifications(self, alert: models.Alert, server: models.ServerProfile, rule: models.ThresholdRule):
        """Send alert notifications through all enabled channels"""
        # Get all enabled alert channels
        channels = self.db.query(models.AlertChannel).filter(
            models.AlertChannel.enabled == True
        ).all()

        if not channels:
            logger.info("No enabled notification channels found")
            return

        # Prepare alert data for notification
        alert_data = {
            'alert_id': alert.id,
            'severity': alert.severity,
            'message': alert.message,
            'metric_value': alert.metric_value,
            'server_name': server.name,
            'server_id': server.id,
            'rule_name': rule.name,
            'triggered_at': alert.triggered_at.isoformat(),
            'timestamp': int(alert.triggered_at.timestamp())
        }

        # Send through each channel
        for channel in channels:
            try:
                channel_dict = {
                    'id': channel.id,
                    'name': channel.name,
                    'channel_type': channel.channel_type,
                    'config': channel.config,
                    'template': channel.template # Pass the template field
                }

                success, message = await self.notification_service.send_notification(self.db, channel_dict, alert_data)

                if success:
                    logger.info(f"Notification sent via {channel.name} (ID: {channel.id}): {message}")
                else:
                    logger.warning(f"Failed to send notification via {channel.name} (ID: {channel.id}): {message}")

            except Exception as e:
                logger.error(f"Error sending notification via {channel.name}: {e}")
        
        # Send browser push notifications for critical alerts
        if alert.severity == 'critical':
            push_subscriptions = self.db.query(models.PushSubscription).all()
            if push_subscriptions:
                message_title = f"CRITICAL Alert: {server.name}"
                message_body = alert.message
                for sub in push_subscriptions:
                    try:
                        subscription_info = {
                            "endpoint": sub.endpoint,
                            "keys": {
                                "p256dh": sub.p256dh,
                                "auth": sub.auth,
                            }
                        }
                        await send_push_notification(subscription_info, json.dumps({"title": message_title, "body": message_body}))
                        logger.info(f"Browser push notification sent to {sub.endpoint}")
                    except Exception as e:
                        logger.error(f"Error sending browser push notification to {sub.endpoint}: {e}")
