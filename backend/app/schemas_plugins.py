"""
Pydantic schemas for Plugin API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class PluginMetadataSchema(BaseModel):
    """Plugin metadata"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    tags: List[str] = []
    requires_sudo: bool = False
    supported_os: List[str] = []
    dependencies: List[str] = []
    config_schema: Optional[Dict[str, Any]] = None


class PluginInfo(BaseModel):
    """Basic plugin information"""
    id: str
    name: str
    version: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    enabled: bool
    external: bool
    health_status: str
    last_health_check: Optional[str] = None


class PluginDetailInfo(PluginInfo):
    """Detailed plugin information"""
    author: Optional[str] = None
    metadata: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    health_message: Optional[str] = None
    last_error: Optional[str] = None
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None


class PluginListResponse(BaseModel):
    """Response for listing plugins"""
    plugins: List[PluginInfo]
    total: int


class PluginRegisterRequest(BaseModel):
    """Request to register an external plugin"""
    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Plugin display name")
    version: str = Field(default="1.0.0", description="Plugin version")
    category: str = Field(default="custom", description="Plugin category")
    description: str = Field(default="", description="Plugin description")
    author: str = Field(default="Unknown", description="Plugin author")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class PluginConfigUpdate(BaseModel):
    """Request to update plugin configuration"""
    config: Dict[str, Any] = Field(..., description="New plugin configuration")


class PluginMetricData(BaseModel):
    """Plugin metric data"""
    data: Dict[str, Any] = Field(..., description="Metric data")
    timestamp: Optional[datetime] = None


class PluginMetricsResponse(BaseModel):
    """Response for plugin metrics query"""
    plugin_id: str
    metrics: List[Dict[str, Any]]
    total: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class PluginHealthResponse(BaseModel):
    """Plugin health check response"""
    plugin_id: str
    healthy: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    checked_at: str


class PluginExecutionResponse(BaseModel):
    """Plugin execution result"""
    success: bool
    plugin_id: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PluginEnableRequest(BaseModel):
    """Request to enable/disable a plugin"""
    enabled: bool = Field(..., description="Enable or disable the plugin")


class PluginActionResponse(BaseModel):
    """Generic action response"""
    success: bool
    message: str
    plugin_id: Optional[str] = None
