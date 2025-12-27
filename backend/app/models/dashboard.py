"""
Dashboard Configuration Models

Models for storing custom dashboard layouts and configurations.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.plugin import PortableJSON


class Dashboard(Base):
    """Custom dashboard configuration."""
    __tablename__ = "dashboards"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(String(255), nullable=True)  # Null = shared dashboard
    
    # Layout configuration
    layout = Column(PortableJSON, nullable=False)  # Grid layout configuration
    widgets = Column(PortableJSON, nullable=False)  # List of widget configurations
    
    # Settings
    is_default = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=30)  # Seconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Dashboard(id={self.id}, name={self.name}, user_id={self.user_id})>"


class DashboardWidget(Base):
    """Widget configuration for dashboards."""
    __tablename__ = "dashboard_widgets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=False)
    
    # Widget identification
    widget_type = Column(String(100), nullable=False)  # metric_chart, stat_card, alert_list, etc.
    widget_id = Column(String(100), nullable=False)  # Unique ID within dashboard
    
    # Position and size
    x = Column(Integer, nullable=False)  # Grid X position
    y = Column(Integer, nullable=False)  # Grid Y position
    w = Column(Integer, nullable=False)  # Width in grid units
    h = Column(Integer, nullable=False)  # Height in grid units
    
    # Configuration
    config = Column(PortableJSON, default={})  # Widget-specific configuration
    title = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    dashboard = relationship("Dashboard", backref="widget_instances")
    
    def __repr__(self):
        return f"<DashboardWidget(id={self.id}, type={self.widget_type}, dashboard={self.dashboard_id})>"

