"""
Photo Management Monitor Plugin

Monitors photo management platforms (PhotoPrism/Immich).
Your memories, meticulously monitored!
"""

import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class PhotoManagerMonitorPlugin(PluginBase):
    """Monitors photo management platforms"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="photo-manager-monitor",
            name="Photo Manager Monitor",
            version="1.0.0",
            description="Monitors photo management platforms including PhotoPrism and Immich",
            author="Unity Team",
            category=PluginCategory.MEDIA,
            tags=["photos", "photoprism", "immich", "media", "gallery"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["photoprism", "immich"],
                        "description": "Photo platform type"
                    },
                    "url": {
                        "type": "string",
                        "description": "Base URL of the platform"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key (if required)"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for authentication"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for authentication"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 10,
                        "description": "Request timeout in seconds"
                    }
                },
                "required": ["platform", "url"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect photo platform metrics"""
        
        config = self.config or {}
        platform = config.get("platform")
        base_url = config.get("url", "").rstrip("/")
        timeout = config.get("timeout", 10)
        
        if not platform or not base_url:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Platform and URL required"
            }
        
        if platform == "photoprism":
            return await self._check_photoprism(base_url, timeout, config)
        elif platform == "immich":
            return await self._check_immich(base_url, timeout, config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown platform: {platform}"
            }
    
    async def _check_photoprism(self, base_url: str, timeout: int, config: Dict) -> Dict[str, Any]:
        """Check PhotoPrism instance"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check health endpoint
                try:
                    async with session.get(
                        f"{base_url}/api/v1/status",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            return {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "platform": "photoprism",
                                "url": base_url,
                                "summary": {
                                    "online": True,
                                    "healthy": True
                                },
                                "info": {
                                    "version": data.get("version", "unknown")
                                }
                            }
                        else:
                            return {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "platform": "photoprism",
                                "url": base_url,
                                "summary": {
                                    "online": True,
                                    "healthy": False,
                                    "http_status": response.status
                                }
                            }
                except Exception as e:
                    return {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "platform": "photoprism",
                        "url": base_url,
                        "summary": {
                            "online": False,
                            "error": str(e)
                        }
                    }
                    
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _check_immich(self, base_url: str, timeout: int, config: Dict) -> Dict[str, Any]:
        """Check Immich instance"""
        api_key = config.get("api_key")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if api_key:
                    headers["x-api-key"] = api_key
                
                # Check server info endpoint
                try:
                    async with session.get(
                        f"{base_url}/api/server-info/ping",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Get version if possible
                            version = "unknown"
                            try:
                                async with session.get(
                                    f"{base_url}/api/server-info/version",
                                    headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=timeout)
                                ) as ver_response:
                                    if ver_response.status == 200:
                                        ver_data = await ver_response.json()
                                        version = ver_data.get("major", "") + "." + ver_data.get("minor", "")
                            except Exception:
                                pass
                            
                            return {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "platform": "immich",
                                "url": base_url,
                                "summary": {
                                    "online": True,
                                    "healthy": data.get("res") == "pong"
                                },
                                "info": {
                                    "version": version
                                }
                            }
                        else:
                            return {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "platform": "immich",
                                "url": base_url,
                                "summary": {
                                    "online": True,
                                    "healthy": False,
                                    "http_status": response.status
                                }
                            }
                except Exception as e:
                    return {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "platform": "immich",
                        "url": base_url,
                        "summary": {
                            "online": False,
                            "error": str(e)
                        }
                    }
                    
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        config = self.config or {}
        base_url = config.get("url")
        
        if not base_url:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    base_url.rstrip("/"),
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status in [200, 401, 403]  # Accept auth challenges
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "platform" in config and "url" in config
