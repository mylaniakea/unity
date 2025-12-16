"""
Alert and threshold schema definitions.

Alert management, channels, thresholds, and notification logs.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# Threshold Rule Schemas
class ThresholdRuleBase(BaseModel):
    server_id: Optional[int] = None
    name: str
    metric: str
    condition: str
    threshold_value: int
    severity: str = "warning"
    enabled: bool = True

class ThresholdRuleCreate(ThresholdRuleBase):
    pass

class ThresholdRuleUpdate(BaseModel):
    name: Optional[str] = None
    metric: Optional[str] = None
    condition: Optional[str] = None
    threshold_value: Optional[int] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    muted_until: Optional[datetime] = None # New: Time until rule is muted

class ThresholdRule(ThresholdRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Alert Schemas
class AlertBase(BaseModel):
    rule_id: int
    server_id: int
    severity: str
    message: str
    metric_value: int

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    acknowledged: Optional[bool] = None
    resolved: Optional[bool] = None
    snoozed_until: Optional[datetime] = None # New: Time until alert is snoozed or None to clear

class Alert(AlertBase):
    id: int
    triggered_at: datetime
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    resolved: bool
    resolved_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None # New: Time until alert is snoozed

    class Config:
        from_attributes = True

# Alert Channel Schemas
class AlertChannelBase(BaseModel):
    name: str
    channel_type: str
    enabled: bool = False
    config: Dict[str, Any] = {}
    template: Optional[str] = None # New: Customizable message template

class AlertChannelCreate(AlertChannelBase):
    pass

class AlertChannelUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    template: Optional[str] = None # New: Customizable message template

class AlertChannel(AlertChannelBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Notification Log Schemas
class NotificationLogBase(BaseModel):
    alert_id: Optional[int] = None
    channel_id: Optional[int] = None
    success: bool
    message: Optional[str] = None

class NotificationLogResponse(NotificationLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
