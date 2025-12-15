"""
Hub Client for External Plugins

Provides API client for external plugins to communicate with Unity hub.
"""

import httpx
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class HubClient:
    """
    Client for external plugins to communicate with Unity hub.
    
    Handles:
    - Plugin registration
    - Metric reporting
    - Configuration fetching
    - Health status updates
    """
    
    def __init__(self, hub_url: str, api_key: str, timeout: int = 30):
        """
        Initialize hub client.
        
        Args:
            hub_url: Base URL of the Unity hub API
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.hub_url = hub_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._client = None
        
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _ensure_client(self):
        """Ensure async HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def register_plugin(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register plugin with hub.
        
        Args:
            metadata: Plugin metadata dictionary
            
        Returns:
            Registration response from hub
            
        Raises:
            httpx.HTTPError: If registration fails
        """
        await self._ensure_client()
        
        try:
            response = await self._client.post(
                f"{self.hub_url}/api/plugins/register",
                json=metadata,
                headers=self._get_headers()
            )
            response.raise_for_status()
            logger.info(f"Plugin {metadata.get('id')} registered successfully")
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to register plugin: {e}")
            raise
    
    async def report_metrics(self, plugin_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Report plugin metrics to hub.
        
        Args:
            plugin_id: Plugin identifier
            data: Metrics data
            
        Returns:
            Response from hub
            
        Raises:
            httpx.HTTPError: If reporting fails
        """
        await self._ensure_client()
        
        try:
            response = await self._client.post(
                f"{self.hub_url}/api/plugins/{plugin_id}/metrics",
                json=data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to report metrics for {plugin_id}: {e}")
            raise
    
    async def get_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Fetch plugin configuration from hub.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin configuration dictionary
            
        Raises:
            httpx.HTTPError: If fetch fails
        """
        await self._ensure_client()
        
        try:
            response = await self._client.get(
                f"{self.hub_url}/api/plugins/{plugin_id}/config",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get config for {plugin_id}: {e}")
            raise
    
    async def update_health(self, plugin_id: str, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update plugin health status.
        
        Args:
            plugin_id: Plugin identifier
            health_data: Health status data
            
        Returns:
            Response from hub
            
        Raises:
            httpx.HTTPError: If update fails
        """
        await self._ensure_client()
        
        try:
            response = await self._client.post(
                f"{self.hub_url}/api/plugins/{plugin_id}/health",
                json=health_data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to update health for {plugin_id}: {e}")
            raise
    
    async def get_plugin_info(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get plugin information from hub.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin information dictionary
            
        Raises:
            httpx.HTTPError: If fetch fails
        """
        await self._ensure_client()
        
        try:
            response = await self._client.get(
                f"{self.hub_url}/api/plugins/{plugin_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get plugin info for {plugin_id}: {e}")
            raise
    
    async def list_plugins(self) -> Dict[str, Any]:
        """
        List all plugins registered with hub.
        
        Returns:
            List of plugins
            
        Raises:
            httpx.HTTPError: If fetch fails
        """
        await self._ensure_client()
        
        try:
            response = await self._client.get(
                f"{self.hub_url}/api/plugins",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to list plugins: {e}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
