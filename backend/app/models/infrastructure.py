import enum
from sqlalchemy import Enum, Column, Integer, BigInteger, String, DateTime, Text, Boolean, Float, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.database import Base



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


