"""
DNS Monitor Plugin

Monitors Pi-hole, AdGuard Home, and Unbound DNS servers.
Because when DNS is slow or broken, the entire internet "feels" broken.
"""

import requests
import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class DNSMonitorPlugin(PluginBase):
    """Monitors DNS servers (Pi-hole, AdGuard Home, Unbound)"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="dns-monitor",
            name="DNS Monitor",
            version="1.0.0",
            description="Monitors Pi-hole, AdGuard Home, and Unbound DNS servers including query stats, block rates, and performance",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["dns", "pi-hole", "adguard", "unbound", "blocking", "queries"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=["requests"],
            config_schema={
                "type": "object",
                "properties": {
                    "dns_type": {
                        "type": "string",
                        "enum": ["pihole", "adguard", "unbound"],
                        "description": "Type of DNS server to monitor"
                    },
                    "api_url": {
                        "type": "string",
                        "description": "API URL (e.g., http://pi.hole/admin for Pi-hole, http://localhost:3000 for AdGuard)"
                    },
                    "api_token": {
                        "type": "string",
                        "description": "API authentication token"
                    },
                    "password": {
                        "type": "string",
                        "description": "Admin password (for Pi-hole web password auth)"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 10,
                        "description": "API request timeout"
                    }
                },
                "required": ["dns_type", "api_url"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect DNS server metrics"""
        
        config = self.config or {}
        dns_type = config.get("dns_type", "").lower()
        
        if dns_type == "pihole":
            return self._monitor_pihole(config)
        elif dns_type == "adguard":
            return self._monitor_adguard(config)
        elif dns_type == "unbound":
            return self._monitor_unbound(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown DNS type: {dns_type}",
                "supported_types": ["pihole", "adguard", "unbound"]
            }
    
    def _monitor_pihole(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Pi-hole DNS server"""
        
        api_url = config.get("api_url", "http://pi.hole/admin")
        api_token = config.get("api_token")
        password = config.get("password")
        timeout = config.get("timeout_seconds", 10)
        
        # Remove trailing /api if present
        api_url = api_url.rstrip("/api").rstrip("/")
        
        try:
            # Build auth parameter
            auth_param = ""
            if api_token:
                auth_param = f"&auth={api_token}"
            elif password:
                auth_param = f"&auth={password}"
            
            # Get summary stats
            summary_response = requests.get(
                f"{api_url}/api.php?summary{auth_param}",
                timeout=timeout
            )
            summary_response.raise_for_status()
            summary = summary_response.json()
            
            # Get top blocked domains
            top_blocked_response = requests.get(
                f"{api_url}/api.php?topItems=5{auth_param}",
                timeout=timeout
            )
            top_blocked_response.raise_for_status()
            top_data = top_blocked_response.json()
            
            # Parse data
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "pihole",
                "api_url": api_url,
                "summary": {
                    "queries_today": summary.get("dns_queries_today", 0),
                    "blocked_today": summary.get("ads_blocked_today", 0),
                    "percent_blocked": round(summary.get("ads_percentage_today", 0), 2),
                    "domains_on_blocklist": summary.get("domains_being_blocked", 0),
                    "unique_clients": summary.get("unique_clients", 0),
                    "status": summary.get("status", "unknown")
                },
                "top_blocked_domains": top_data.get("top_ads", {}),
                "top_queries": top_data.get("top_queries", {}),
                "gravity_last_updated": summary.get("gravity_last_updated", {})
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "pihole",
                "error": f"Failed to connect to Pi-hole: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "pihole",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_adguard(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor AdGuard Home DNS server"""
        
        api_url = config.get("api_url", "http://localhost:3000")
        api_token = config.get("api_token")
        timeout = config.get("timeout_seconds", 10)
        
        # Remove trailing slash
        api_url = api_url.rstrip("/")
        
        try:
            headers = {}
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
            
            # Get stats
            stats_response = requests.get(
                f"{api_url}/control/stats",
                headers=headers,
                timeout=timeout
            )
            stats_response.raise_for_status()
            stats = stats_response.json()
            
            # Get status
            status_response = requests.get(
                f"{api_url}/control/status",
                headers=headers,
                timeout=timeout
            )
            status_response.raise_for_status()
            status = status_response.json()
            
            # Calculate percentages
            total_queries = stats.get("num_dns_queries", 0)
            blocked_queries = stats.get("num_blocked_filtering", 0)
            percent_blocked = (blocked_queries / total_queries * 100) if total_queries > 0 else 0
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "adguard",
                "api_url": api_url,
                "summary": {
                    "queries_total": total_queries,
                    "blocked_filtering": blocked_queries,
                    "blocked_safebrowsing": stats.get("num_blocked_safebrowsing", 0),
                    "blocked_parental": stats.get("num_blocked_parental", 0),
                    "percent_blocked": round(percent_blocked, 2),
                    "avg_processing_time_ms": round(stats.get("avg_processing_time", 0) * 1000, 2),
                    "running": status.get("running", False),
                    "protection_enabled": status.get("protection_enabled", False)
                },
                "top_queried_domains": stats.get("top_queried_domains", []),
                "top_blocked_domains": stats.get("top_blocked_domains", []),
                "top_clients": stats.get("top_clients", []),
                "filters": {
                    "filters_updated": status.get("filters", {}).get("updated", False),
                    "user_rules": status.get("user_rules", 0)
                }
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "adguard",
                "error": f"Failed to connect to AdGuard Home: {str(e)}",
                "api_url": api_url
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "adguard",
                "error": str(e),
                "api_url": api_url
            }
    
    def _monitor_unbound(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor Unbound DNS server via unbound-control"""
        
        try:
            # Run unbound-control stats
            result = subprocess.run(
                ["unbound-control", "stats_noreset"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dns_type": "unbound",
                    "error": "Failed to execute unbound-control",
                    "stderr": result.stderr
                }
            
            # Parse stats
            stats = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    try:
                        stats[key] = float(value)
                    except ValueError:
                        stats[key] = value
            
            # Calculate useful metrics
            total_queries = stats.get("total.num.queries", 0)
            cache_hits = stats.get("total.num.cachehits", 0)
            cache_misses = stats.get("total.num.cachemiss", 0)
            
            cache_hit_percent = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "unbound",
                "summary": {
                    "total_queries": int(total_queries),
                    "cache_hits": int(cache_hits),
                    "cache_misses": int(cache_misses),
                    "cache_hit_percent": round(cache_hit_percent, 2),
                    "recursion_time_avg_ms": round(stats.get("total.recursion.time.avg", 0), 2),
                    "num_queries_ip_ratelimited": int(stats.get("total.num.queries_ip_ratelimited", 0)),
                    "uptime_seconds": stats.get("time.up", 0)
                },
                "memory": {
                    "cache_rrset_mb": round(stats.get("mem.cache.rrset", 0) / 1024 / 1024, 2),
                    "cache_message_mb": round(stats.get("mem.cache.message", 0) / 1024 / 1024, 2),
                    "mod_iterator_mb": round(stats.get("mem.mod.iterator", 0) / 1024 / 1024, 2)
                },
                "threads": {
                    "num_threads": int(stats.get("thread0.num.queries", 0) > 0)  # Simplified
                }
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "unbound",
                "error": "unbound-control command not found"
            }
        except subprocess.TimeoutExpired:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "unbound",
                "error": "unbound-control timeout"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dns_type": "unbound",
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """Check if DNS server is accessible"""
        
        config = self.config or {}
        dns_type = config.get("dns_type", "").lower()
        api_url = config.get("api_url")
        
        if dns_type in ["pihole", "adguard"] and api_url:
            try:
                response = requests.get(api_url, timeout=5)
                return response.status_code in [200, 401, 403]
            except Exception:
                return False
        elif dns_type == "unbound":
            try:
                result = subprocess.run(
                    ["unbound-control", "status"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except Exception:
                return False
        
        return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        dns_type = config.get("dns_type")
        if dns_type not in ["pihole", "adguard", "unbound"]:
            return False
        
        # Unbound doesn't need API URL
        if dns_type == "unbound":
            return True
        
        api_url = config.get("api_url")
        if not api_url or not isinstance(api_url, str):
            return False
        
        return True
