"""
Bitwarden/Vaultwarden Monitor Plugin

Monitors Bitwarden or Vaultwarden password manager instances.
Trust, but monitor your secrets vault!
"""

import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class BitwardenMonitorPlugin(PluginBase):
    """Monitors Bitwarden/Vaultwarden instances"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="bitwarden-monitor",
            name="Bitwarden/Vaultwarden Monitor",
            version="1.0.0",
            description="Monitors Bitwarden/Vaultwarden server health and API availability",
            author="Unity Team",
            category=PluginCategory.SECURITY,
            tags=["bitwarden", "vaultwarden", "passwords", "security", "vault"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Base URL of Bitwarden/Vaultwarden server"
                    },
                    "admin_token": {
                        "type": "string",
                        "description": "Admin token for accessing Vaultwarden diagnostics (optional)"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 10,
                        "description": "Request timeout in seconds"
                    }
                },
                "required": ["url"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Bitwarden/Vaultwarden metrics"""
        
        config = self.config or {}
        base_url = config.get("url", "").rstrip("/")
        admin_token = config.get("admin_token")
        timeout = config.get("timeout", 10)
        
        if not base_url:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Server URL not configured"
            }
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_url": base_url,
            "checks": {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check API alive endpoint
                try:
                    async with session.get(
                        f"{base_url}/alive",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        results["checks"]["alive"] = {
                            "status": response.status == 200,
                            "response_time_ms": response.headers.get("X-Response-Time", "N/A")
                        }
                except Exception as e:
                    results["checks"]["alive"] = {"status": False, "error": str(e)}
                
                # Check web vault availability
                try:
                    async with session.get(
                        f"{base_url}/",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        results["checks"]["web_vault"] = {
                            "status": response.status == 200,
                            "content_length": len(await response.read())
                        }
                except Exception as e:
                    results["checks"]["web_vault"] = {"status": False, "error": str(e)}
                
                # Check API identity endpoint
                try:
                    async with session.get(
                        f"{base_url}/identity/.well-known/openid-configuration",
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        results["checks"]["identity_api"] = {
                            "status": response.status == 200
                        }
                        if response.status == 200:
                            data = await response.json()
                            results["checks"]["identity_api"]["issuer"] = data.get("issuer")
                except Exception as e:
                    results["checks"]["identity_api"] = {"status": False, "error": str(e)}
                
                # Vaultwarden-specific admin endpoint (if token provided)
                if admin_token:
                    try:
                        headers = {"Authorization": f"Bearer {admin_token}"}
                        async with session.get(
                            f"{base_url}/admin/diagnostics",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=timeout)
                        ) as response:
                            if response.status == 200:
                                diag_data = await response.json()
                                results["checks"]["admin_diagnostics"] = {
                                    "status": True,
                                    "version": diag_data.get("server_version"),
                                    "database": diag_data.get("database_type")
                                }
                            else:
                                results["checks"]["admin_diagnostics"] = {
                                    "status": False,
                                    "http_status": response.status
                                }
                    except Exception as e:
                        results["checks"]["admin_diagnostics"] = {"status": False, "error": str(e)}
                
                # Calculate overall health
                total_checks = len(results["checks"])
                passed_checks = sum(1 for c in results["checks"].values() if c.get("status"))
                
                results["summary"] = {
                    "healthy": passed_checks >= total_checks - 1,  # Allow 1 failure
                    "checks_passed": passed_checks,
                    "checks_total": total_checks,
                    "availability_percent": round((passed_checks / total_checks) * 100, 2) if total_checks > 0 else 0
                }
                
                return results
                
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Monitoring error: {str(e)}"
            }
    
    async def health_check(self) -> bool:
        config = self.config or {}
        base_url = config.get("url")
        
        if not base_url:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url.rstrip('/')}/alive",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "url" in config and isinstance(config["url"], str)
