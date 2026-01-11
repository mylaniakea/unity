"""
Pydantic schemas for Docker Host Management API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ==================
# DOCKER HOST SCHEMAS
# ==================

class DockerHostBase(BaseModel):
    """Base Docker host schema"""
    name: str = Field(..., description="Host name")
    description: Optional[str] = Field(None, description="Host description")
    host_url: str = Field(..., description="Docker host URL (e.g., unix:///var/run/docker.sock)")
    is_active: bool = Field(True, description="Whether host is actively monitored")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional host-specific config")
    labels: Dict[str, Any] = Field(default_factory=dict, description="User-defined labels")


class DockerHostCreate(DockerHostBase):
    """Schema for creating a new Docker host"""
    pass


class DockerHostUpdate(BaseModel):
    """Schema for updating a Docker host"""
    name: Optional[str] = None
    description: Optional[str] = None
    host_url: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None


class DockerHostInfo(DockerHostBase):
    """Basic Docker host information"""
    id: int
    health_status: str
    health_message: Optional[str] = None
    last_health_check: Optional[datetime] = None
    container_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DockerHostDetail(DockerHostInfo):
    """Detailed Docker host information"""
    created_by: Optional[int] = None


class DockerHostListResponse(BaseModel):
    """Response for listing Docker hosts"""
    hosts: List[DockerHostInfo]
    total: int


class DockerHostHealthResponse(BaseModel):
    """Docker host health check response"""
    host_id: int
    host_name: str
    healthy: bool
    health_status: str
    message: Optional[str] = None
    container_count: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    checked_at: datetime


class DockerActionResponse(BaseModel):
    """Generic Docker action response"""
    success: bool
    message: str
    host_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
