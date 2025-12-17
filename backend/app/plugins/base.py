"""
Base Plugin Interface for Unity

All plugins (built-in and external) must inherit from PluginBase.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class PluginCategory(str, Enum):
    """Plugin categories for organization"""
    SYSTEM = "system"
    NETWORK = "network"
    STORAGE = "storage"
    THERMAL = "thermal"
    CONTAINER = "container"
    DATABASE = "database"
    APPLICATION = "application"
    SECURITY = "security"
    AI_ML = "ai_ml"
    CUSTOM = "custom"


class PluginMetadata(BaseModel):
    """Plugin metadata structure"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: PluginCategory
    tags: List[str] = []
    requires_sudo: bool = False
    supported_os: List[str] = ["linux", "darwin", "windows"]
    dependencies: List[str] = []
    config_schema: Optional[Dict[str, Any]] = None


class PluginBase(ABC):
    """
    Base class for all Unity plugins.
    
    Plugins can collect metrics, manage resources, or perform automation tasks.
    Each plugin has metadata, configuration, and implements data collection.
    """
    
    def __init__(self, hub_client=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin.
        
        Args:
            hub_client: HubClient instance for external plugins to communicate with hub
            config: Plugin-specific configuration dictionary
        """
        self.hub = hub_client
        self.config = config or {}
        self.enabled = False
        self._last_execution: Optional[datetime] = None
        self._execution_count = 0
        self._last_error: Optional[str] = None
        
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.
        
        Returns:
            PluginMetadata object with plugin information
        """
        pass
    
    @abstractmethod
    async def collect_data(self) -> Dict[str, Any]:
        """
        Collect data from the monitored system/service.
        
        Returns:
            Dictionary containing collected metrics/data
            
        Raises:
            Exception: If data collection fails
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if plugin is healthy and can execute.
        
        Returns:
            Dictionary with health status:
            {
                "healthy": bool,
                "message": str,
                "details": dict (optional)
            }
        """
        return {
            "healthy": True,
            "message": "Plugin is healthy"
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    async def on_enable(self):
        """Called when plugin is enabled."""
        self.enabled = True
        
    async def on_disable(self):
        """Called when plugin is disabled."""
        self.enabled = False
        
    async def on_error(self, error: Exception):
        """
        Called when plugin encounters an error.
        
        Args:
            error: The exception that occurred
        """
        self._last_error = str(error)
        
    async def on_config_change(self, new_config: Dict[str, Any]):
        """
        Called when plugin configuration changes.
        
        Args:
            new_config: New configuration dictionary
        """
        self.config = new_config
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current plugin status.
        
        Returns:
            Dictionary with plugin status information
        """
        metadata = self.get_metadata()
        return {
            "id": metadata.id,
            "name": metadata.name,
            "enabled": self.enabled,
            "last_execution": self._last_execution.isoformat() if self._last_execution else None,
            "execution_count": self._execution_count,
            "last_error": self._last_error
        }
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute plugin data collection with error handling and tracking.
        
        Returns:
            Collected data or error information
        """
        if not self.enabled:
            return {
                "error": "Plugin is disabled",
                "plugin_id": self.get_metadata().id
            }
        
        try:
            self._last_execution = datetime.utcnow()
            data = await self.collect_data()
            self._execution_count += 1
            self._last_error = None
            
            return {
                "success": True,
                "data": data,
                "timestamp": self._last_execution.isoformat(),
                "plugin_id": self.get_metadata().id
            }
            
        except Exception as e:
            await self.on_error(e)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "plugin_id": self.get_metadata().id
            }


class ExternalPluginBase(PluginBase):
    """
    Base class for external plugins that run as separate services.
    
    External plugins must register with the hub and use HubClient
    to report metrics and receive configuration updates.
    """
    
    def __init__(self, hub_url: str, api_key: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize external plugin.
        
        Args:
            hub_url: URL of the Unity hub API
            api_key: API key for authentication
            config: Plugin configuration
        """
        from .hub_client import HubClient
        hub_client = HubClient(hub_url, api_key)
        super().__init__(hub_client, config)
        
    async def start(self):
        """Start external plugin and register with hub."""
        metadata = self.get_metadata()
        await self.hub.register_plugin(metadata.dict())
        
    async def report_metrics(self, data: Dict[str, Any]):
        """
        Report collected metrics to hub.
        
        Args:
            data: Metrics data to report
        """
        metadata = self.get_metadata()
        await self.hub.report_metrics(metadata.id, data)
        
    async def fetch_config(self) -> Dict[str, Any]:
        """
        Fetch latest configuration from hub.
        
        Returns:
            Plugin configuration dictionary
        """
        metadata = self.get_metadata()
        return await self.hub.get_config(metadata.id)
