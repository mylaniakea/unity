"""
Plugin database models for Unity.

Core models for plugin management, metrics storage, and status tracking.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


# Portable JSON type that uses JSONB for PostgreSQL, JSON for others
class PortableJSON(TypeDecorator):
    """Platform-independent JSON type that uses JSONB on PostgreSQL."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB)
        else:
            return dialect.type_descriptor(JSON)


class Plugin(Base):
    """Plugin registration and configuration."""
    __tablename__ = "plugins"
    
    # Match existing database schema
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50))
    category = Column(String(50))
    description = Column(Text)
    author = Column(String(255))
    enabled = Column(Boolean, default=False)
    external = Column(Boolean, default=False)
    plugin_metadata = Column(PortableJSON)
    config = Column(PortableJSON)
    
    # Health tracking fields
    last_health_check = Column(DateTime(timezone=True))
    health_status = Column(String(50))
    health_message = Column(Text)
    last_error = Column(Text)
    
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    status = relationship("PluginStatus", back_populates="plugin", uselist=False)
    metrics = relationship("PluginMetric", back_populates="plugin")
    executions = relationship("PluginExecution", back_populates="plugin")
    alerts = relationship("PluginAlert", back_populates="plugin")
    
    def __repr__(self):
        return f"<Plugin(id={self.id}, name={self.name}, enabled={self.enabled})>"


class PluginMetric(Base):
    """Time-series metrics from plugins."""
    __tablename__ = "plugin_metrics"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    plugin_id = Column(String(100), ForeignKey("plugins.id"), primary_key=True, nullable=False)
    metric_name = Column(String(200), primary_key=True, nullable=False)
    value = Column(PortableJSON, nullable=False)
    tags = Column(PortableJSON)
    
    # Relationships
    plugin = relationship("Plugin", back_populates="metrics")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_metrics_plugin_time', 'plugin_id', 'time'),
        Index('idx_metrics_name', 'metric_name'),
        # Note: GIN index on tags only for PostgreSQL, will be ignored on SQLite
        Index('idx_metrics_tags', 'tags', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<PluginMetric(plugin={self.plugin_id}, metric={self.metric_name}, time={self.time})>"


class PluginStatus(Base):
    """Current status and health of each plugin."""
    __tablename__ = "plugin_status"
    
    plugin_id = Column(String(100), ForeignKey("plugins.id"), primary_key=True)
    last_run = Column(DateTime(timezone=True))
    last_success = Column(DateTime(timezone=True))
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    consecutive_errors = Column(Integer, default=0)
    health_status = Column(String(20), default="unknown")  # unknown, healthy, degraded, failing
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    plugin = relationship("Plugin", back_populates="status")
    
    def __repr__(self):
        return f"<PluginStatus(plugin={self.plugin_id}, health={self.health_status})>"


class PluginExecution(Base):
    """Individual plugin execution history."""
    __tablename__ = "plugin_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), ForeignKey("plugins.id"), nullable=False, index=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False, index=True, server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    status = Column(String(50), nullable=False, default='running')  # running, success, failed
    error_message = Column(Text)
    metrics_count = Column(Integer, default=0)
    
    # Relationships
    plugin = relationship("Plugin", back_populates="executions")
    
    __table_args__ = (
        Index('idx_executions_plugin_time', 'plugin_id', 'started_at'),
    )
    
    def __repr__(self):
        return f"<PluginExecution(plugin={self.plugin_id}, status={self.status}, started={self.started_at})>"


class PluginAlert(Base):
    """Alert configuration for monitoring."""
    __tablename__ = "plugin_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100), ForeignKey("plugins.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    condition = Column(PortableJSON, nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, error, critical
    enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    plugin = relationship("Plugin", back_populates="alerts")
    history = relationship("AlertHistory", back_populates="alert")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, name={self.name}, plugin={self.plugin_id})>"


class AlertHistory(Base):
    """Historical record of alert triggers."""
    __tablename__ = "alert_history"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    alert_id = Column(Integer, ForeignKey("plugin_alerts.id"), primary_key=True, nullable=False)
    triggered = Column(Boolean, nullable=False)
    value = Column(PortableJSON)
    message = Column(Text)
    
    # Relationships
    alert = relationship("PluginAlert", back_populates="history")
    
    # Index for queries
    __table_args__ = (
        Index('idx_alert_history_time', 'alert_id', 'time'),
    )
    
    def __repr__(self):
        return f"<AlertHistory(alert={self.alert_id}, time={self.time}, triggered={self.triggered})>"
