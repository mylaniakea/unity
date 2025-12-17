"""
Network Monitor Plugin

Monitors network interface statistics including throughput, errors, and connections.
"""

import psutil
from datetime import datetime
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class NetworkMonitorPlugin(PluginBase):
    """Monitors network statistics and connections"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="network-monitor",
            name="Network Monitor",
            version="1.0.0",
            description="Monitors network interfaces, throughput, errors, and active connections",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["network", "throughput", "connections", "interfaces"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psutil"],
            config_schema={
                "type": "object",
                "properties": {
                    "interfaces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific interfaces to monitor (empty = all)"
                    },
                    "include_connections": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include active connections count"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect network metrics"""
        
        # Network I/O counters
        net_io = psutil.net_io_counters(pernic=True)
        
        # Filter interfaces if specified
        interfaces_filter = self.config.get("interfaces", [])
        
        interfaces_data = {}
        for interface, counters in net_io.items():
            if interfaces_filter and interface not in interfaces_filter:
                continue
                
            interfaces_data[interface] = {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errin": counters.errin,
                "errout": counters.errout,
                "dropin": counters.dropin,
                "dropout": counters.dropout
            }
        
        # Network addresses
        addresses = {}
        try:
            net_if_addrs = psutil.net_if_addrs()
            for interface, addrs in net_if_addrs.items():
                if interfaces_filter and interface not in interfaces_filter:
                    continue
                    
                addresses[interface] = []
                for addr in addrs:
                    addresses[interface].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
        except Exception:
            # Some systems may not support this
            pass
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "interfaces": interfaces_data,
            "addresses": addresses
        }
        
        # Optional: Active connections count
        if self.config.get("include_connections", True):
            try:
                connections = psutil.net_connections()
                connection_stats = {
                    "total": len(connections),
                    "established": sum(1 for c in connections if c.status == "ESTABLISHED"),
                    "listen": sum(1 for c in connections if c.status == "LISTEN"),
                    "time_wait": sum(1 for c in connections if c.status == "TIME_WAIT")
                }
                data["connections"] = connection_stats
            except (psutil.AccessDenied, Exception):
                # Requires elevated privileges on some systems
                data["connections"] = {"error": "Access denied - may require sudo"}
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if network monitoring is working"""
        try:
            # Try to get network I/O counters
            psutil.net_io_counters()
            return {
                "healthy": True,
                "message": "Network monitoring is operational"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
