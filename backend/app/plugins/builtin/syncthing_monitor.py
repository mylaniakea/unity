"""
Syncthing Monitor Plugin

Monitors Syncthing P2P file synchronization.
Decentralized sync, centralized monitoring!
"""

import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class SyncthingMonitorPlugin(PluginBase):
    """Monitors Syncthing instances"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="syncthing-monitor",
            name="Syncthing Monitor",
            version="1.0.0",
            description="Monitors Syncthing P2P file synchronization status, devices, and folders",
            author="Unity Team",
            category=PluginCategory.STORAGE,
            tags=["syncthing", "sync", "p2p", "files", "replication"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Syncthing API URL"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "Syncthing API key"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 10,
                        "description": "Request timeout in seconds"
                    }
                },
                "required": ["url", "api_key"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Syncthing metrics"""
        
        config = self.config or {}
        base_url = config.get("url", "").rstrip("/")
        api_key = config.get("api_key")
        timeout = config.get("timeout", 10)
        
        if not base_url or not api_key:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "URL and API key required"
            }
        
        headers = {"X-API-Key": api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get system status
                async with session.get(
                    f"{base_url}/rest/system/status",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response.raise_for_status()
                    system_status = await response.json()
                
                # Get system connections
                async with session.get(
                    f"{base_url}/rest/system/connections",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response.raise_for_status()
                    connections = await response.json()
                
                # Get folder stats
                async with session.get(
                    f"{base_url}/rest/stats/folder",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response.raise_for_status()
                    folder_stats = await response.json()
                
                # Process devices
                devices_info = []
                total_devices = len(connections.get("connections", {}))
                connected_devices = 0
                
                for device_id, conn in connections.get("connections", {}).items():
                    connected = conn.get("connected", False)
                    if connected:
                        connected_devices += 1
                    
                    devices_info.append({
                        "id": device_id[:7] + "...",  # Truncate for display
                        "connected": connected,
                        "address": conn.get("address", "N/A")
                    })
                
                # Process folders
                folders_info = []
                total_folders = len(folder_stats)
                
                for folder_id, stats in folder_stats.items():
                    folders_info.append({
                        "id": folder_id,
                        "last_file_at": stats.get("lastFile", {}).get("at", "N/A")
                    })
                
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "summary": {
                        "my_id": system_status.get("myID", "unknown")[:7] + "...",
                        "uptime_seconds": system_status.get("uptime", 0),
                        "total_devices": total_devices,
                        "connected_devices": connected_devices,
                        "total_folders": total_folders,
                        "syncing": system_status.get("cpuPercent", 0) > 5  # Simple heuristic
                    },
                    "system": {
                        "version": system_status.get("version", "unknown"),
                        "cpu_percent": system_status.get("cpuPercent", 0),
                        "goroutines": system_status.get("goroutines", 0),
                        "sys_ram_mb": system_status.get("sys", 0) / (1024 * 1024)
                    },
                    "devices": devices_info,
                    "folders": folders_info
                }
                
        except aiohttp.ClientError as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"HTTP error: {str(e)}"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        config = self.config or {}
        base_url = config.get("url")
        api_key = config.get("api_key")
        
        if not base_url or not api_key:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-API-Key": api_key}
                async with session.get(
                    f"{base_url.rstrip('/')}/rest/system/ping",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    data = await response.json()
                    return data.get("ping") == "pong"
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "url" in config and "api_key" in config
