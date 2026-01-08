"""
Nginx Proxy Manager Monitor Plugin

Monitors Nginx Proxy Manager (NPM) status, proxy hosts, and SSL certificates.
The reverse proxy is your front door - keep it healthy!
"""

import subprocess
import requests
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class NginxProxyManagerMonitorPlugin(PluginBase):
    """Monitors Nginx Proxy Manager status and configuration"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="nginx-proxy-manager-monitor",
            name="Nginx Proxy Manager Monitor",
            version="1.0.0",
            description="Monitors Nginx Proxy Manager proxy hosts, SSL certificates, and service health",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["nginx", "npm", "reverse-proxy", "proxy", "ssl", "web"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "npm_url": {
                        "type": "string",
                        "default": "http://localhost:81",
                        "description": "NPM admin interface URL"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "NPM API token for authentication"
                    },
                    "username": {
                        "type": "string",
                        "description": "NPM admin username (alternative to token)"
                    },
                    "password": {
                        "type": "string",
                        "description": "NPM admin password (alternative to token)"
                    },
                    "database_path": {
                        "type": "string",
                        "default": "/data/database.sqlite",
                        "description": "Path to NPM SQLite database (for direct access)"
                    },
                    "use_api": {
                        "type": "boolean",
                        "default": True,
                        "description": "Use NPM API (true) or direct database access (false)"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect NPM status and configuration"""
        
        config = self.config or {}
        use_api = config.get("use_api", True)
        
        if use_api:
            return await self._collect_via_api(config)
        else:
            return self._collect_via_database(config)
    
    async def _collect_via_api(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data via NPM API"""
        
        npm_url = config.get("npm_url", "http://localhost:81")
        api_token = config.get("api_token")
        username = config.get("username")
        password = config.get("password")
        
        try:
            # Get or create auth token
            if not api_token:
                if username and password:
                    api_token = self._login(npm_url, username, password)
                else:
                    return {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": "No authentication configured (api_token or username/password required)"
                    }
            
            headers = {"Authorization": f"Bearer {api_token}"}
            
            # Get proxy hosts
            proxy_hosts = self._get_proxy_hosts(npm_url, headers)
            
            # Get SSL certificates
            certificates = self._get_certificates(npm_url, headers)
            
            # Calculate summary
            total_hosts = len(proxy_hosts)
            enabled_hosts = sum(1 for h in proxy_hosts if h.get("enabled"))
            ssl_enabled = sum(1 for h in proxy_hosts if h.get("certificate_id"))
            
            total_certs = len(certificates)
            expiring_soon = sum(1 for c in certificates if self._is_expiring_soon(c))
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "npm_url": npm_url,
                "summary": {
                    "total_proxy_hosts": total_hosts,
                    "enabled_hosts": enabled_hosts,
                    "ssl_enabled_hosts": ssl_enabled,
                    "total_certificates": total_certs,
                    "certificates_expiring_soon": expiring_soon
                },
                "proxy_hosts": proxy_hosts,
                "certificates": certificates
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "npm_url": npm_url
            }
    
    def _collect_via_database(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data via direct database access"""
        
        db_path = config.get("database_path", "/data/database.sqlite")
        
        try:
            if not Path(db_path).exists():
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": f"Database not found: {db_path}"
                }
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get proxy hosts
            cursor.execute("""
                SELECT 
                    id, domain_names, forward_host, forward_port,
                    certificate_id, ssl_forced, enabled, meta
                FROM proxy_host
            """)
            
            proxy_hosts = []
            for row in cursor.fetchall():
                proxy_hosts.append({
                    "id": row["id"],
                    "domain_names": row["domain_names"].split(",") if row["domain_names"] else [],
                    "forward_host": row["forward_host"],
                    "forward_port": row["forward_port"],
                    "certificate_id": row["certificate_id"],
                    "ssl_forced": bool(row["ssl_forced"]),
                    "enabled": bool(row["enabled"])
                })
            
            # Get certificates
            cursor.execute("""
                SELECT 
                    id, nice_name, domain_names, expires_on, meta
                FROM certificate
            """)
            
            certificates = []
            for row in cursor.fetchall():
                cert = {
                    "id": row["id"],
                    "nice_name": row["nice_name"],
                    "domain_names": row["domain_names"].split(",") if row["domain_names"] else [],
                    "expires_on": row["expires_on"]
                }
                
                if row["expires_on"]:
                    expires = datetime.fromisoformat(row["expires_on"].replace("Z", "+00:00"))
                    days_until_expiry = (expires - datetime.now(timezone.utc)).days
                    cert["days_until_expiry"] = days_until_expiry
                    cert["expiring_soon"] = days_until_expiry < 30
                
                certificates.append(cert)
            
            conn.close()
            
            # Calculate summary
            total_hosts = len(proxy_hosts)
            enabled_hosts = sum(1 for h in proxy_hosts if h.get("enabled"))
            ssl_enabled = sum(1 for h in proxy_hosts if h.get("certificate_id"))
            
            total_certs = len(certificates)
            expiring_soon = sum(1 for c in certificates if c.get("expiring_soon"))
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database_path": db_path,
                "summary": {
                    "total_proxy_hosts": total_hosts,
                    "enabled_hosts": enabled_hosts,
                    "ssl_enabled_hosts": ssl_enabled,
                    "total_certificates": total_certs,
                    "certificates_expiring_soon": expiring_soon
                },
                "proxy_hosts": proxy_hosts,
                "certificates": certificates
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "database_path": db_path
            }
    
    def _login(self, npm_url: str, username: str, password: str) -> str:
        """Login to NPM and get API token"""
        
        response = requests.post(
            f"{npm_url}/api/tokens",
            json={
                "identity": username,
                "secret": password
            },
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        return data.get("token")
    
    def _get_proxy_hosts(self, npm_url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get all proxy hosts from NPM API"""
        
        response = requests.get(
            f"{npm_url}/api/nginx/proxy-hosts",
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        hosts = response.json()
        
        # Simplify host data
        simplified = []
        for host in hosts:
            simplified.append({
                "id": host.get("id"),
                "domain_names": host.get("domain_names", []),
                "forward_host": host.get("forward_host"),
                "forward_port": host.get("forward_port"),
                "certificate_id": host.get("certificate_id"),
                "ssl_forced": host.get("ssl_forced"),
                "enabled": host.get("enabled")
            })
        
        return simplified
    
    def _get_certificates(self, npm_url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Get all SSL certificates from NPM API"""
        
        response = requests.get(
            f"{npm_url}/api/nginx/certificates",
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        certs = response.json()
        
        # Simplify certificate data
        simplified = []
        for cert in certs:
            cert_data = {
                "id": cert.get("id"),
                "nice_name": cert.get("nice_name"),
                "domain_names": cert.get("domain_names", []),
                "expires_on": cert.get("expires_on")
            }
            
            if cert.get("expires_on"):
                expires = datetime.fromisoformat(cert["expires_on"].replace("Z", "+00:00"))
                days_until_expiry = (expires - datetime.now(timezone.utc)).days
                cert_data["days_until_expiry"] = days_until_expiry
                cert_data["expiring_soon"] = days_until_expiry < 30
            
            simplified.append(cert_data)
        
        return simplified
    
    def _is_expiring_soon(self, cert: Dict[str, Any], days: int = 30) -> bool:
        """Check if certificate is expiring soon"""
        
        days_until_expiry = cert.get("days_until_expiry")
        return days_until_expiry is not None and days_until_expiry < days
    
    async def health_check(self) -> bool:
        """Check if NPM is accessible"""
        config = self.config or {}
        npm_url = config.get("npm_url", "http://localhost:81")
        
        try:
            response = requests.get(npm_url, timeout=5)
            return response.status_code in [200, 302, 401]  # 401 is ok, just means auth required
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return True  # Use defaults
        
        use_api = config.get("use_api", True)
        
        if use_api:
            # API mode requires authentication
            has_token = config.get("api_token")
            has_creds = config.get("username") and config.get("password")
            return has_token or has_creds
        else:
            # Database mode requires database path
            return bool(config.get("database_path"))
