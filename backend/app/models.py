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

# ==================
# PLUGIN SYSTEM MODELS
# ==================

class Plugin(Base):
    """Plugin registry - tracks all registered plugins"""
    __tablename__ = "plugins"

    id = Column(String(100), primary_key=True)  # Plugin ID (e.g., "lm-sensors")
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)  # thermal, system, network, etc.
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=False)
    external = Column(Boolean, default=False)  # True for external plugins, False for built-in
    
    # Plugin metadata and config
    plugin_metadata = Column(JSONB, default={})  # Full plugin metadata
    config = Column(JSONB, default={})  # Plugin-specific configuration
    
    # Health and status tracking
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_status = Column(String(50), default='unknown')  # healthy, unhealthy, unknown
    health_message = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    metrics = relationship("PluginMetric", back_populates="plugin", cascade="all, delete-orphan")
    executions = relationship("PluginExecution", back_populates="plugin", cascade="all, delete-orphan")


class PluginMetric(Base):
    """Time-series metrics collected by plugins"""
    __tablename__ = "plugin_metrics"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(String(100), ForeignKey('plugins.id'), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, server_default=func.now())
    data = Column(JSONB, nullable=False)  # The actual metrics data
    
    # Relationship
    plugin = relationship("Plugin", back_populates="metrics")

    __table_args__ = (
        # Index for efficient time-series queries
        {'postgresql_partition_by': 'RANGE (timestamp)'},  # Optional: for partitioning
    )


class PluginExecution(Base):
    """Plugin execution history and status"""
    __tablename__ = "plugin_executions"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(String(100), ForeignKey('plugins.id'), nullable=False, index=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False, index=True, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(String(50), nullable=False, default='running')  # running, success, failed
    error_message = Column(Text, nullable=True)
    metrics_count = Column(Integer, default=0)  # Number of metrics collected
    
    # Relationship
    plugin = relationship("Plugin", back_populates="executions")


class PluginAPIKey(Base):
    """API keys for external plugin authentication"""
    __tablename__ = "plugin_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(String(100), ForeignKey('plugins.id'), nullable=False, index=True)
    key_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 hash
    name = Column(String(255), nullable=True)  # Descriptive name for the key
    
    # Permissions and restrictions
    permissions = Column(JSONB, default=["report_metrics", "update_health", "get_config"])
    
    # Usage tracking
    last_used = Column(DateTime(timezone=True), nullable=True)
    uses_count = Column(Integer, default=0)
    
    # Expiration and revocation
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(Integer, ForeignKey('users.id'), nullable=True)


# ==================
# CREDENTIAL MANAGEMENT (KC-Booth Integration)
# ==================

class SSHKey(Base):
    """SSH key pairs for server authentication"""
    __tablename__ = "ssh_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Keys (encrypted)
    public_key = Column(Text, nullable=False)
    private_key = Column(Text, nullable=False)  # Encrypted with Fernet
    
    # Key metadata
    key_type = Column(String(50), default="rsa")  # rsa, ed25519, etc.
    key_size = Column(Integer, nullable=True)  # 2048, 4096 for RSA
    fingerprint = Column(String(255), nullable=True)
    
    # Ownership and access
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)


class Certificate(Base):
    """SSL/TLS certificates"""
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Certificate data (encrypted)
    certificate = Column(Text, nullable=False)  # PEM format
    private_key = Column(Text, nullable=False)  # PEM format, encrypted
    certificate_chain = Column(Text, nullable=True)  # Full chain if available
    
    # Certificate metadata
    common_name = Column(String(255), nullable=True)
    subject_alt_names = Column(JSONB, default=[])  # List of SANs
    issuer = Column(String(255), nullable=True)
    
    # Validity
    not_before = Column(DateTime(timezone=True), nullable=True)
    not_after = Column(DateTime(timezone=True), nullable=True)
    is_expired = Column(Boolean, default=False)
    
    # Provider info
    provider = Column(String(50), default="manual")  # manual, step-ca, letsencrypt, etc.
    provider_order_id = Column(String(255), nullable=True)  # External provider reference
    
    # Auto-renewal
    auto_renew = Column(Boolean, default=False)
    renewal_days_before = Column(Integer, default=30)
    last_renewal_attempt = Column(DateTime(timezone=True), nullable=True)
    renewal_status = Column(String(50), nullable=True)  # success, failed, pending
    
    # Ownership
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ServerCredential(Base):
    """Server connection credentials"""
    __tablename__ = "server_credentials"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to Unity's ServerProfile
    server_profile_id = Column(Integer, ForeignKey('server_profiles.id'), nullable=False, unique=True)
    
    # Credentials (encrypted)
    username = Column(String(255), nullable=True)
    password = Column(Text, nullable=True)  # Encrypted with Fernet
    
    # SSH Key association
    ssh_key_id = Column(Integer, ForeignKey('ssh_keys.id'), nullable=True)
    
    # Additional connection details
    port = Column(Integer, default=22)
    connection_type = Column(String(50), default="ssh")  # ssh, winrm, etc.
    
    # Metadata
    notes = Column(Text, nullable=True)
    
    # Ownership
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)


class StepCAConfig(Base):
    """Step-CA certificate authority configuration"""
    __tablename__ = "step_ca_config"

    id = Column(Integer, primary_key=True)
    
    # Step-CA connection details
    ca_url = Column(String(255), nullable=False)
    ca_fingerprint = Column(String(255), nullable=False)
    provisioner_name = Column(String(255), nullable=False)
    provisioner_password = Column(Text, nullable=False)  # Encrypted
    
    # Configuration
    default_validity_days = Column(Integer, default=90)
    enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CredentialAuditLog(Base):
    """Audit log for credential operations"""
    __tablename__ = "credential_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Who
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(255), nullable=True)  # Denormalized for history
    
    # What
    action = Column(String(100), nullable=False, index=True)  # create, read, update, delete, rotate, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # ssh_key, certificate, credential
    resource_id = Column(Integer, nullable=True)
    resource_name = Column(String(255), nullable=True)
    
    # When
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # How
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Details
    details = Column(JSONB, default={})  # Additional context
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
