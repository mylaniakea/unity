"""
Plugin database models for Unity.

Core models for plugin management, metrics storage, and status tracking.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Plugin(Base):
    """Plugin registration and configuration."""
    __tablename__ = "plugins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plugin_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(String(50))
    description = Column(Text)
    category = Column(String(50))
    enabled = Column(Boolean, default=False, index=True)
    config = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    status = relationship("PluginStatus", back_populates="plugin", uselist=False)
    metrics = relationship("PluginMetric", back_populates="plugin")
    alerts = relationship("Alert", back_populates="plugin")
    
    def __repr__(self):
        return f"<Plugin(id={self.plugin_id}, name={self.name}, enabled={self.enabled})>"


class PluginMetric(Base):
    """Time-series metrics from plugins."""
    __tablename__ = "plugin_metrics"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    plugin_id = Column(String(100), ForeignKey("plugins.plugin_id"), primary_key=True, nullable=False)
    metric_name = Column(String(200), primary_key=True, nullable=False)
    value = Column(JSONB, nullable=False)
    tags = Column(JSONB)
    
    # Relationships
    plugin = relationship("Plugin", back_populates="metrics")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_metrics_plugin_time', 'plugin_id', 'time'),
        Index('idx_metrics_name', 'metric_name'),
        Index('idx_metrics_tags', 'tags', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<PluginMetric(plugin={self.plugin_id}, metric={self.metric_name}, time={self.time})>"


class PluginStatus(Base):
    """Current status and health of each plugin."""
    __tablename__ = "plugin_status"
    
    plugin_id = Column(String(100), ForeignKey("plugins.plugin_id"), primary_key=True)
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


class Alert(Base):
    """Alert configuration for monitoring."""
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plugin_id = Column(String(100), ForeignKey("plugins.plugin_id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    condition = Column(JSONB, nullable=False)
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
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), primary_key=True, nullable=False)
    triggered = Column(Boolean, nullable=False)
    value = Column(JSONB)
    message = Column(Text)
    
    # Relationships
    alert = relationship("Alert", back_populates="history")
    
    # Index for queries
    __table_args__ = (
        Index('idx_alert_history_time', 'alert_id', 'time'),
    )
    
    def __repr__(self):
        return f"<AlertHistory(alert={self.alert_id}, time={self.time}, triggered={self.triggered})>"
