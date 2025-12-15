from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB # Import JSONB for PostgreSQL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.database import Base

class ServerProfile(Base):
    __tablename__ = "server_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, default="Unknown Server")
    description = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)

    # SSH Configuration
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True) # Path to local key file
    use_local_agent = Column(Boolean, default=False)
    
    # Data Plugins
    enabled_plugins = Column(JSONB, default=[])   # List of enabled plugin IDs ["lm-sensors", "smartctl"]
    detected_plugins = Column(JSONB, default={})  # Detected plugins with status {"lm-sensors": True, "smartctl": False}
    
    # Store complex data as JSONB for PostgreSQL
    hardware_info = Column(JSONB, default={})
    os_info = Column(JSONB, default={})
    packages = Column(JSONB, default=[])
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to Reports
    reports = relationship("Report", back_populates="server_profile")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True) # Singleton, always ID 1
    
    # Store provider keys/configs securely (encrypted in future, plain for now)
    providers = Column(JSONB, default={
        "ollama": {"url": "http://host.docker.internal:11434", "enabled": True},
        "openai": {"api_key": "", "enabled": False},
        "anthropic": {"api_key": "", "enabled": False},
        "google": {"api_key": "", "enabled": False}
    })
    
    # Configuration
    active_model = Column(String, nullable=True)
    primary_provider = Column(String, nullable=True) 
    fallback_provider = Column(String, nullable=True)
    system_prompt = Column(Text, default="You are a helpful Homelab Assistant. You have access to server stats and documentation.")
    
    # Cron settings for reports
    cron_24hr_report = Column(String, default="0 2 * * *") # Daily at 02:00 UTC
    cron_7day_report = Column(String, default="0 3 * * 1") # Mondays at 03:00 UTC
    cron_monthly_report = Column(String, default="0 4 1 * *") # 1st of each month at 04:00 UTC

    # Polling settings
    polling_interval = Column(Integer, default=30) # Dashboard polling interval in seconds (default: 30s)
    alert_sound_enabled = Column(Boolean, default=False) # Enable sound notifications for critical alerts
    maintenance_mode_until = Column(DateTime(timezone=True), nullable=True) # New: Time until maintenance mode is active

    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True) # Link to ServerProfile
    report_type = Column(String, index=True) # e.g., "24-hour", "7-day", "monthly"
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True), index=True)
    aggregated_data = Column(JSONB, default={}) # Store aggregated metrics, charts data etc.
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to ServerProfile
    server_profile = relationship("ServerProfile", back_populates="reports")

class KnowledgeItem(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    category = Column(String, index=True) # network, hardware, manual
    tags = Column(JSONB, default=[]) # Use JSONB for tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ServerSnapshot(Base):
    __tablename__ = "server_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    data = Column(JSONB, default={}) # Comprehensive snapshot data

    server_profile = relationship("ServerProfile", backref="snapshots")

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
    severity = Column(String, index=True) # "info", "warning", "critical"
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
    config = Column(JSONB, default={}) # Channel-specific configuration
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

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # Kept for backwards compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())