"""HTTP Service Monitor Template

Copy this template to create a plugin that monitors HTTP/HTTPS endpoints.
"""
import httpx
import time
from typing import Dict, Any
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class HTTPServiceMonitorPlugin(PluginBase):
    """Template for monitoring HTTP/HTTPS services."""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="http-service-template",
            name="HTTP Service Monitor",
            version="1.0.0",
            description="Monitors HTTP/HTTPS endpoints for availability and performance",
            author="Your Name",
            category=PluginCategory.APPLICATION,
            tags=["http", "web", "api", "template"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["httpx"],
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to monitor"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "HEAD"],
                        "default": "GET"
                    },
                    "timeout": {
                        "type": "number",
                        "default": 5.0,
                        "minimum": 1.0
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "default": True
                    },
                    "expected_status": {
                        "type": "integer",
                        "default": 200
                    }
                },
                "required": ["url"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect HTTP service metrics."""
        config = self.config or {}
        
        # Validate configuration
        url = config.get("url")
        if not url:
            return {"error": "URL not configured", "status": "error"}
        
        method = config.get("method", "GET")
        timeout = config.get("timeout", 5.0)
        verify_ssl = config.get("verify_ssl", True)
        expected_status = config.get("expected_status", 200)
        
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url)
                elif method == "HEAD":
                    response = await client.head(url)
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "status": "up" if response.status_code == expected_status else "degraded",
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "is_healthy": response.status_code == expected_status,
                "url": url,
                "method": method,
                "ssl_verified": verify_ssl
            }
        
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "error": f"Request timed out after {timeout}s",
                "url": url
            }
        except httpx.ConnectError:
            return {
                "status": "down",
                "error": "Connection refused",
                "url": url
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "url": url
            }


# Example usage:
# plugin = HTTPServiceMonitorPlugin(config={
#     "url": "https://api.example.com/health",
#     "timeout": 10.0
# })
# data = await plugin.collect_data()
