"""
Reverse Proxy Monitor Plugin

Monitors Traefik and Caddy reverse proxy status, routes, and health.
The front door to your services - keep it monitored!
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class ReverseProxyMonitorPlugin(PluginBase):
    """Monitors Traefik and Caddy reverse proxies"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="reverse-proxy-monitor",
            name="Reverse Proxy Monitor",
            version="1.0.0",
            description="Monitors Traefik and Caddy reverse proxy status, routes, backends, and SSL termination",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["reverse-proxy", "traefik", "caddy", "proxy", "ssl", "routing"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "proxy_type": {
                        "type": "string",
                        "enum": ["traefik", "caddy"],
                        "description": "Type of reverse proxy to monitor"
                    },
                    "api_url": {
                        "type": "string",
                        "description": "API endpoint URL (e.g., http://localhost:8080 for Traefik, http://localhost:2019 for Caddy)"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "API authentication token (if required)"
                    },
                    "basic_auth": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"}
                        },
                        "description": "Basic authentication credentials (if required)"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 10,
                        "description": "API request timeout in seconds"
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "default": True,
                        "description": "Verify SSL certificates"
                    }
                },
                "required": ["proxy_type", "api_url"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect reverse proxy metrics"""
        
        config = self.config or {}
        proxy_type = config.get("proxy_type", "").lower()
        
        if proxy_type == "traefik":
            return self._monitor_traefik(config)
        elif proxy_type == "caddy":
            return self._monitor_caddy(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown or unsupported proxy type: {proxy_type}",
                "supported_types": ["traefik", "caddy"]
            }
    
    def _monitor_traefik(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Traefik reverse proxy"""
        
        api_url = config.get("api_url", "http://localhost:8080")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            # Prepare authentication
            auth = self._get_auth(config)
            headers = self._get_headers(config)
            
            # Get Traefik overview
            overview_response = requests.get(
                f"{api_url}/api/overview",
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify_ssl
            )
            overview_response.raise_for_status()
            overview = overview_response.json()
            
            # Get routers (HTTP)
            routers_response = requests.get(
                f"{api_url}/api/http/routers",
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify_ssl
            )
            routers_response.raise_for_status()
            routers = routers_response.json()
            
            # Get services (HTTP)
            services_response = requests.get(
                f"{api_url}/api/http/services",
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify_ssl
            )
            services_response.raise_for_status()
            services = services_response.json()
            
            # Parse routers
            parsed_routers = []
            for router in routers:
                parsed_routers.append({
                    "name": router.get("name"),
                    "status": router.get("status"),
                    "rule": router.get("rule"),
                    "service": router.get("service"),
                    "entrypoints": router.get("entryPoints", []),
                    "tls_enabled": bool(router.get("tls"))
                })
            
            # Parse services
            parsed_services = []
            for service in services:
                server_status = service.get("serverStatus", {})
                parsed_services.append({
                    "name": service.get("name"),
                    "status": service.get("status"),
                    "type": service.get("type"),
                    "servers_up": len([s for s in server_status.values() if s == "UP"]),
                    "servers_down": len([s for s in server_status.values() if s == "DOWN"]),
                    "servers_total": len(server_status)
                })
            
            # Calculate summary
            total_routers = len(parsed_routers)
            enabled_routers = sum(1 for r in parsed_routers if r.get("status") == "enabled")
            tls_routers = sum(1 for r in parsed_routers if r.get("tls_enabled"))
            
            total_services = len(parsed_services)
            healthy_services = sum(1 for s in parsed_services if s.get("servers_down", 0) == 0)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "proxy_type": "traefik",
                "api_url": api_url,
                "summary": {
                    "total_routers": total_routers,
                    "enabled_routers": enabled_routers,
                    "tls_enabled_routers": tls_routers,
                    "total_services": total_services,
                    "healthy_services": healthy_services,
                    "unhealthy_services": total_services - healthy_services
                },
                "routers": parsed_routers,
                "services": parsed_services,
                "overview": overview
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "proxy_type": "traefik",
                "error": f"Failed to connect to Traefik API: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "proxy_type": "traefik",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_caddy(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Caddy reverse proxy"""
        
        api_url = config.get("api_url", "http://localhost:2019")
        timeout = config.get("timeout_seconds", 10)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            # Prepare authentication
            auth = self._get_auth(config)
            headers = self._get_headers(config)
            
            # Get Caddy config
            config_response = requests.get(
                f"{api_url}/config/",
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify_ssl
            )
            config_response.raise_for_status()
            caddy_config = config_response.json()
            
            # Parse apps
            apps = caddy_config.get("apps", {})
            http_app = apps.get("http", {})
            
            # Get servers
            servers = http_app.get("servers", {})
            
            # Parse routes from all servers
            all_routes = []
            total_tls = 0
            
            for server_name, server_config in servers.items():
                routes = server_config.get("routes", [])
                
                for route in routes:
                    # Extract matcher info
                    matchers = route.get("match", [])
                    hosts = []
                    paths = []
                    
                    for matcher in matchers:
                        if "host" in matcher:
                            hosts.extend(matcher["host"])
                        if "path" in matcher:
                            paths.extend(matcher["path"])
                    
                    # Extract handler info
                    handlers = route.get("handle", [])
                    handler_types = [h.get("handler") for h in handlers]
                    
                    # Check for reverse proxy handler
                    is_reverse_proxy = "reverse_proxy" in handler_types
                    
                    # Get upstream info
                    upstreams = []
                    for handler in handlers:
                        if handler.get("handler") == "reverse_proxy":
                            upstream_list = handler.get("upstreams", [])
                            for upstream in upstream_list:
                                upstreams.append(upstream.get("dial", "unknown"))
                    
                    all_routes.append({
                        "server": server_name,
                        "hosts": hosts,
                        "paths": paths,
                        "handler_types": handler_types,
                        "is_reverse_proxy": is_reverse_proxy,
                        "upstreams": upstreams
                    })
                
                # Check for TLS
                tls_config = server_config.get("tls_connection_policies")
                if tls_config:
                    total_tls += 1
            
            # Get TLS app info
            tls_app = apps.get("tls", {})
            certificates = tls_app.get("certificates", {})
            
            # Calculate summary
            total_routes = len(all_routes)
            reverse_proxy_routes = sum(1 for r in all_routes if r.get("is_reverse_proxy"))
            total_servers = len(servers)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "proxy_type": "caddy",
                "api_url": api_url,
                "summary": {
                    "total_servers": total_servers,
                    "total_routes": total_routes,
                    "reverse_proxy_routes": reverse_proxy_routes,
                    "tls_enabled_servers": total_tls,
                    "total_certificates": len(certificates)
                },
                "routes": all_routes,
                "servers": list(servers.keys()),
                "tls_configured": total_tls > 0
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "proxy_type": "caddy",
                "error": f"Failed to connect to Caddy API: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "proxy_type": "caddy",
                "error": str(e),
                "api_url": api_url
            }
    
    def _get_auth(self, config: Dict[str, Any]) -> Optional[tuple]:
        """Get basic authentication tuple if configured"""
        
        basic_auth = config.get("basic_auth")
        if basic_auth:
            username = basic_auth.get("username")
            password = basic_auth.get("password")
            if username and password:
                return (username, password)
        
        return None
    
    def _get_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Get request headers including API token if configured"""
        
        headers = {}
        
        api_token = config.get("api_token")
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        
        return headers
    
    async def health_check(self) -> bool:
        """Check if the reverse proxy API is accessible"""
        
        config = self.config or {}
        api_url = config.get("api_url")
        
        if not api_url:
            return False
        
        try:
            auth = self._get_auth(config)
            headers = self._get_headers(config)
            verify_ssl = config.get("verify_ssl", True)
            
            response = requests.get(
                api_url,
                headers=headers,
                auth=auth,
                timeout=5,
                verify=verify_ssl
            )
            
            # Accept various success codes
            return response.status_code in [200, 401, 403]
            
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        proxy_type = config.get("proxy_type")
        if proxy_type not in ["traefik", "caddy"]:
            return False
        
        api_url = config.get("api_url")
        if not api_url or not isinstance(api_url, str):
            return False
        
        return True
