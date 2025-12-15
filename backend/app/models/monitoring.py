from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.database import Base



class ThresholdRule(Base):
    __tablename__ = "threshold_rules"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True, nullable=True) # null = all servers
    name = Column(String, index=True) # e.g., "High CPU Usage"
    metric = Column(String, index=True) # e.g., "cpu_percent", "memory_percent", "disk_percent"
    condition = Column(String) # e.g., "greater_than", "less_than"
    threshold_value = Column(Integer) # e.g., 90 for 90%
    severity = Column(String, default="warning") # "info", "warning", "critical"
    enabled = Column(Boolean, default=True)
    muted_until = Column(DateTime(timezone=True), nullable=True) # New: Time until rule is muted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    server_profile = relationship("ServerProfile", backref="threshold_rules")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey('threshold_rules.id'), index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True)
    monitored_server_id = Column(Integer, ForeignKey('monitored_servers.id'), index=True, nullable=True)  # For infrastructure alerts
    severity = Column(String, index=True) # "info", "warning", "critical"
    alert_type = Column(String, index=True, default="threshold")  # "threshold", "storage", "database", "server_health"
    # Infrastructure alert rule system (Phase 3.5)
    alert_rule_id = Column(Integer, ForeignKey('alert_rules.id'), index=True, nullable=True)  # Link to AlertRule
    resource_type = Column(String, nullable=True)  # "server", "device", "pool", "database"
    resource_id = Column(Integer, nullable=True, index=True)  # ID of the resource
    threshold = Column(Float, nullable=True)  # Threshold that was exceeded
    status = Column(String, nullable=True, index=True)  # "active", "acknowledged", "resolved"
    acknowledged_by = Column(String(255), nullable=True)  # User who acknowledged
    message = Column(Text)
    metric_value = Column(Integer) # Actual value that triggered the alert
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    snoozed_until = Column(DateTime(timezone=True), nullable=True) # New: Time until alert is snoozed

    threshold_rule = relationship("ThresholdRule", backref="alerts")
    server_profile = relationship("ServerProfile", backref="alerts")


class AlertChannel(Base):
    __tablename__ = "alert_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # e.g., "SMTP", "Telegram", "ntfy"
    channel_type = Column(String, index=True) # "smtp", "telegram", "ntfy", "discord", "slack", "pushover"
    enabled = Column(Boolean, default=False)
    config = Column(JSON().with_variant(JSONB, "postgresql"), default={}) # Channel-specific configuration
    template = Column(Text, nullable=True) # New: Customizable message template for the channel
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True) # Optional: Link to a user if authentication is implemented
    endpoint = Column(String, unique=True, index=True)
    p256dh = Column(String)
    auth = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey('alerts.id'), index=True, nullable=True)
    channel_id = Column(Integer, ForeignKey('alert_channels.id'), index=True, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean)
    message = Column(Text, nullable=True) # Success or error message

    alert = relationship("Alert", backref="notification_logs")
    channel = relationship("AlertChannel", backref="notification_logs")


