"""
System Info Plugin

Collects basic system information using psutil.
This is an example built-in plugin.
"""

import psutil
import platform
from datetime import datetime
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class SystemInfoPlugin(PluginBase):
    """Collects basic system information"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="system-info",
            name="System Info",
            version="1.0.0",
            description="Collects basic system information (CPU, memory, disk usage)",
            author="Unity Team",
            category=PluginCategory.SYSTEM,
            tags=["system", "cpu", "memory", "disk"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psutil"],
            config_schema={
                "type": "object",
                "properties": {
                    "collect_network": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to collect network stats"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect system metrics"""
        
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory info
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk info
        disk = psutil.disk_usage('/')
        
        # Build result
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "usage_percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else None
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "percent": swap.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine()
            }
        }
        
        # Optional network stats
        if self.config.get("collect_network", True):
            net_io = psutil.net_io_counters()
            data["network"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if psutil is available and working"""
        try:
            # Try to get CPU info as a health check
            psutil.cpu_percent(interval=0.1)
            return {
                "healthy": True,
                "message": "System info collection is operational"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
