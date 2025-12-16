import enum
from sqlalchemy import Enum, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.core.database import Base



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


