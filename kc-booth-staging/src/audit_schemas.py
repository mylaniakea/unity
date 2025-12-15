"""Pydantic schemas for audit logs."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    """Base audit log schema."""
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    details: Optional[str] = None


class AuditLog(AuditLogBase):
    """Audit log response schema."""
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    correlation_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
