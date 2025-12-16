from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.core.database import Base



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


