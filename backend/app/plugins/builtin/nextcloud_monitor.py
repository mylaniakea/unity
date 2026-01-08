"""
Nextcloud Monitor Plugin

Monitors Nextcloud instance status and health.
Self-hosted cloud storage is the dream - monitoring makes it reliable!
"""

import requests
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class NextcloudMonitorPlugin(PluginBase):
    """Monitors Nextcloud instance"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="nextcloud-monitor",
            name="Nextcloud Monitor",
            version="1.0.0",
            description="Monitors Nextcloud instance including users, storage, apps, and system status",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["nextcloud", "cloud", "storage", "sync", "files"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "api_url": {
                        "type": "string",
                        "description": "Nextcloud URL (e.g., https://cloud.example.com)"
                    },
                    "username": {
                        "type": "string",
                        "description": "Admin username"
                    },
                    "password": {
                        "type": "string",
                        "description": "Admin password or app password"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 10,
                        "description": "API request timeout"
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "default": True,
                        "description": "Verify SSL certificates"
                    }
                },
                "required": ["api_url", "username", "password"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Nextcloud metrics"""
        
        config = self.config or {}
        api_url = config.get("api_url", "").rstrip("/")
        username = config.get("username")
        password = config.get("password")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        if not all([api_url, username, password]):
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "api_url, username, and password are required"
            }
        
        try:
            auth = (username, password)
            headers = {"OCS-APIRequest": "true"}
            
            # Get server info
            serverinfo_response = requests.get(
                f"{api_url}/ocs/v2.php/apps/serverinfo/api/v1/info?format=json",
                auth=auth,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            serverinfo_response.raise_for_status()
            serverinfo = serverinfo_response.json().get("ocs", {}).get("data", {})
            
            # Get capabilities
            capabilities_response = requests.get(
                f"{api_url}/ocs/v2.php/cloud/capabilities?format=json",
                auth=auth,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            capabilities_response.raise_for_status()
            capabilities = capabilities_response.json().get("ocs", {}).get("data", {})
            
            # Get users list (count)
            users_response = requests.get(
                f"{api_url}/ocs/v2.php/cloud/users?format=json",
                auth=auth,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl
            )
            users_response.raise_for_status()
            users_data = users_response.json().get("ocs", {}).get("data", {})
            users = users_data.get("users", [])
            
            # Parse data
            nextcloud_info = serverinfo.get("nextcloud", {})
            system_info = serverinfo.get("system", {})
            storage_info = serverinfo.get("storage", {})
            
            version = capabilities.get("version", {})
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_url": api_url,
                "summary": {
                    "version": f"{version.get('major', '')}.{version.get('minor', '')}.{version.get('micro', '')}",
                    "version_string": version.get("string"),
                    "total_users": len(users),
                    "active_users_5min": nextcloud_info.get("storage", {}).get("num_users", 0),
                    "num_files": nextcloud_info.get("storage", {}).get("num_files", 0),
                    "num_storages": nextcloud_info.get("storage", {}).get("num_storages", 0)
                },
                "storage": {
                    "free_space_bytes": storage_info.get("free_space", 0),
                    "total_space_bytes": storage_info.get("total_space", 0),
                    "used_space_bytes": storage_info.get("total_space", 0) - storage_info.get("free_space", 0),
                    "percent_used": round((1 - storage_info.get("free_space", 0) / max(storage_info.get("total_space", 1), 1)) * 100, 2)
                },
                "system": {
                    "os": system_info.get("os"),
                    "php_version": system_info.get("php", {}).get("version"),
                    "database": system_info.get("database", {}).get("type"),
                    "database_version": system_info.get("database", {}).get("version"),
                    "webserver": system_info.get("webserver"),
                    "mem_free_mb": round(system_info.get("mem_free", 0) / 1024 / 1024, 2),
                    "mem_total_mb": round(system_info.get("mem_total", 0) / 1024 / 1024, 2)
                },
                "apps": {
                    "num_installed": nextcloud_info.get("system", {}).get("apps", {}).get("num_installed", 0),
                    "num_updates_available": nextcloud_info.get("system", {}).get("apps", {}).get("num_updates_available", 0)
                }
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Failed to connect to Nextcloud: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "api_url": api_url
            }
    
    async def health_check(self) -> bool:
        """Check if Nextcloud is accessible"""
        
        config = self.config or {}
        api_url = config.get("api_url")
        
        if not api_url:
            return False
        
        try:
            response = requests.get(f"{api_url}/status.php", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        api_url = config.get("api_url")
        username = config.get("username")
        password = config.get("password")
        
        return bool(api_url and username and password)
