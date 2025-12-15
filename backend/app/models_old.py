from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
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
    enabled_plugins = Column(JSON().with_variant(JSONB, "postgresql"), default=[])   # List of enabled plugin IDs ["lm-sensors", "smartctl"]
    detected_plugins = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Detected plugins with status {"lm-sensors": True, "smartctl": False}
    
    # Store complex data as JSON for PostgreSQL
    hardware_info = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    os_info = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    packages = Column(JSON().with_variant(JSONB, "postgresql"), default=[])
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to Reports
    reports = relationship("Report", back_populates="server_profile")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True) # Singleton, always ID 1
    
    # Store provider keys/configs securely (encrypted in future, plain for now)
    providers = Column(JSON().with_variant(JSONB, "postgresql"), default={
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
    aggregated_data = Column(JSON().with_variant(JSONB, "postgresql"), default={}) # Store aggregated metrics, charts data etc.
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to ServerProfile
    server_profile = relationship("ServerProfile", back_populates="reports")

class KnowledgeItem(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    category = Column(String, index=True) # network, hardware, manual
    tags = Column(JSON().with_variant(JSONB, "postgresql"), default=[]) # Use JSON for tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ServerSnapshot(Base):
    __tablename__ = "server_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey('server_profiles.id'), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    data = Column(JSON().with_variant(JSONB, "postgresql"), default={}) # Comprehensive snapshot data

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
    plugin_metadata = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Full plugin metadata
    config = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Plugin-specific configuration
    
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

    id = Column(Integer, autoincrement=True, index=True)
    plugin_id = Column(String(100), ForeignKey('plugins.id'), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, server_default=func.now(), primary_key=True)
    data = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)  # The actual metrics data
    
    # Relationship
    plugin = relationship("Plugin", back_populates="metrics")

    __table_args__ = (
        # Composite primary key required for partitioned table
        PrimaryKeyConstraint('id', 'timestamp'),
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
    permissions = Column(JSON().with_variant(JSONB, "postgresql"), default=["report_metrics", "update_health", "get_config"])
    
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
    subject_alt_names = Column(JSON().with_variant(JSONB, "postgresql"), default=[])  # List of SANs
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
    details = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Additional context
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

# ============================================================================
# Infrastructure Monitoring Models (Phase 3: BD-Store Integration)
# ============================================================================

import enum
from sqlalchemy import Enum, BigInteger, Float

class ServerStatus(str, enum.Enum):
    """MonitoredServer connection status."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"

class DeviceType(str, enum.Enum):
    """Storage device type."""
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    UNKNOWN = "unknown"

class HealthStatus(str, enum.Enum):
    """Health status for devices and pools."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"
    UNKNOWN = "unknown"

class PoolType(str, enum.Enum):
    """Storage pool type."""
    ZFS = "zfs"
    LVM = "lvm"
    BTRFS = "btrfs"
    MDADM = "mdadm"
    OTHER = "other"

class DatabaseType(str, enum.Enum):
    """Database type enumeration."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    MINIO = "minio"
    MONGODB = "mongodb"
    REDIS = "redis"

class DatabaseStatus(str, enum.Enum):
    """Database connection status."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"

class MonitoredServer(Base):
    """
    Remote server model for infrastructure monitoring.
    
    Integrates with Unity's KC-Booth credential system via foreign keys.
    """
    
    __tablename__ = "monitored_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    ssh_port = Column(Integer, default=22, nullable=False)
    username = Column(String(255), nullable=False)
    
    # Unity KC-Booth credential integration
    ssh_key_id = Column(Integer, ForeignKey("ssh_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    credential_id = Column(Integer, ForeignKey("server_credentials.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Legacy encrypted credentials (for backward compatibility)
    ssh_password_encrypted = Column(Text, nullable=True)
    ssh_private_key_encrypted = Column(Text, nullable=True)
    
    # Connection status
    status = Column(
        Enum(ServerStatus),
        default=ServerStatus.UNKNOWN,
        nullable=False,
        index=True
    )
    last_seen = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Monitoring configuration
    monitoring_enabled = Column(Boolean, default=False, nullable=False, index=True)
    collection_interval = Column(Integer, nullable=True)  # seconds, null = use global default
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    storage_devices = relationship("StorageDevice", back_populates="server", cascade="all, delete-orphan")
    storage_pools = relationship("StoragePool", back_populates="server", cascade="all, delete-orphan")
    database_instances = relationship("DatabaseInstance", back_populates="server", cascade="all, delete-orphan")
    ssh_key = relationship("SSHKey", foreign_keys=[ssh_key_id])
    credential = relationship("ServerCredential", foreign_keys=[credential_id])
    
    def __repr__(self):
        return f"<MonitoredServer(id={self.id}, hostname='{self.hostname}', status='{self.status}')>"

class StorageDevice(Base):
    """Storage device model (disk/drive)."""
    
    __tablename__ = "storage_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("monitored_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Device identification
    device_name = Column(String(255), nullable=False)  # e.g., /dev/sda, /dev/nvme0n1
    device_path = Column(String(500), nullable=True)   # Full path
    serial_number = Column(String(255), nullable=True, index=True)
    model = Column(String(255), nullable=True)
    firmware_version = Column(String(100), nullable=True)
    
    # Device characteristics
    device_type = Column(Enum(DeviceType), default=DeviceType.UNKNOWN, nullable=False)
    size_bytes = Column(BigInteger, nullable=True)
    sector_size = Column(Integer, nullable=True)
    
    # Health metrics
    smart_status = Column(Enum(HealthStatus), default=HealthStatus.UNKNOWN, nullable=False, index=True)
    smart_passed = Column(String(10), nullable=True)  # "PASSED" or "FAILED"
    temperature_celsius = Column(Integer, nullable=True)
    power_on_hours = Column(Integer, nullable=True)
    
    # Wear indicators
    wear_level_percent = Column(Float, nullable=True)  # For SSDs/NVMe
    total_bytes_written = Column(BigInteger, nullable=True)
    total_bytes_read = Column(BigInteger, nullable=True)
    
    # Error counts
    reallocated_sectors = Column(Integer, nullable=True)
    pending_sectors = Column(Integer, nullable=True)
    uncorrectable_errors = Column(Integer, nullable=True)
    
    # Raw SMART data (JSON or text)
    smart_data_raw = Column(Text, nullable=True)
    
    # Status
    last_checked = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    server = relationship("MonitoredServer", back_populates="storage_devices")
    
    def __repr__(self):
        return f"<StorageDevice(id={self.id}, device='{self.device_name}', type='{self.device_type}')>"

class StoragePool(Base):
    """Storage pool model (ZFS, LVM, etc.)."""
    
    __tablename__ = "storage_pools"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("monitored_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Pool identification
    pool_name = Column(String(255), nullable=False)
    pool_type = Column(Enum(PoolType), nullable=False)
    
    # Capacity
    total_size_bytes = Column(BigInteger, nullable=True)
    used_size_bytes = Column(BigInteger, nullable=True)
    available_size_bytes = Column(BigInteger, nullable=True)
    fragmentation_percent = Column(Float, nullable=True)
    
    # Health
    health_status = Column(Enum(HealthStatus), default=HealthStatus.UNKNOWN, nullable=False, index=True)
    status_message = Column(Text, nullable=True)
    
    # Pool-specific data
    raid_level = Column(String(50), nullable=True)  # e.g., "raidz2", "mirror"
    device_count = Column(Integer, nullable=True)
    
    # Raw pool data (JSON or text)
    pool_data_raw = Column(Text, nullable=True)
    
    # Status
    last_checked = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    server = relationship("MonitoredServer", back_populates="storage_pools")
    
    def __repr__(self):
        return f"<StoragePool(id={self.id}, name='{self.pool_name}', type='{self.pool_type}')>"

class DatabaseInstance(Base):
    """Database instance model."""
    
    __tablename__ = "database_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("monitored_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Database identification
    db_type = Column(Enum(DatabaseType), nullable=False)
    db_name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    
    # Credentials (encrypted)
    username = Column(String(255), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    
    # Version and status
    version = Column(String(100), nullable=True)
    status = Column(Enum(DatabaseStatus), default=DatabaseStatus.UNKNOWN, nullable=False)
    last_checked = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Basic metrics
    size_bytes = Column(BigInteger, nullable=True)
    connection_count = Column(Integer, nullable=True)
    active_queries = Column(Integer, nullable=True)
    
    # Additional metrics
    idle_connections = Column(Integer, nullable=True)
    max_connections = Column(Integer, nullable=True)
    slow_queries = Column(Integer, nullable=True)
    cache_hit_ratio = Column(Integer, nullable=True)  # Stored as percentage (0-100)
    uptime_seconds = Column(BigInteger, nullable=True)
    last_metrics_collection = Column(DateTime(timezone=True), nullable=True)
    metrics_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    server = relationship("MonitoredServer", back_populates="database_instances")
    
    def __repr__(self):
        return f"<DatabaseInstance(id={self.id}, type='{self.db_type}', name='{self.db_name}')>"

# ============================================================================
# Alert Rule System (Phase 3.5: Complete BD-Store Integration)
# ============================================================================

class ResourceType(str, enum.Enum):
    """Resource types that can be monitored."""
    SERVER = "server"
    DEVICE = "device"
    POOL = "pool"
    DATABASE = "database"

class AlertCondition(str, enum.Enum):
    """Comparison operators for alert rules."""
    GT = "gt"  # greater than
    LT = "lt"  # less than
    GTE = "gte"  # greater than or equal
    LTE = "lte"  # less than or equal
    EQ = "eq"  # equal
    NE = "ne"  # not equal

class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertStatus(str, enum.Enum):
    """Alert lifecycle status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class AlertRule(Base):
    """Alert rule definition for infrastructure monitoring."""
    
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # What to monitor
    resource_type = Column(Enum(ResourceType), nullable=False)
    metric_name = Column(String(100), nullable=False)
    
    # Condition
    condition = Column(Enum(AlertCondition), nullable=False)
    threshold = Column(Float, nullable=False)
    
    # Alert settings
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    enabled = Column(Boolean, nullable=False, default=True)
    
    # Notification settings
    notification_channels = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)  # ["email", "webhook", "log"]
    cooldown_minutes = Column(Integer, nullable=False, default=15)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AlertRule(id={self.id}, name='{self.name}', {self.metric_name} {self.condition} {self.threshold})>"
