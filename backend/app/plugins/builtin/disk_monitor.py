"""
Disk Monitor Plugin

Monitors disk usage, I/O statistics, and mounted partitions.
"""

import psutil
from datetime import datetime
from typing import Dict, Any

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class DiskMonitorPlugin(PluginBase):
    """Monitors disk usage and I/O statistics"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="disk-monitor",
            name="Disk Monitor",
            version="1.0.0",
            description="Monitors disk usage, I/O statistics, and mounted partitions",
            author="Unity Team",
            category=PluginCategory.STORAGE,
            tags=["disk", "storage", "io", "partitions"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psutil"],
            config_schema={
                "type": "object",
                "properties": {
                    "exclude_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["tmpfs", "devtmpfs", "squashfs"],
                        "description": "Filesystem types to exclude"
                    },
                    "include_io_stats": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include disk I/O statistics"
                    },
                    "warn_threshold_percent": {
                        "type": "integer",
                        "default": 80,
                        "description": "Disk usage warning threshold (percentage)"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect disk metrics"""
        
        exclude_types = self.config.get("exclude_types", ["tmpfs", "devtmpfs", "squashfs"])
        warn_threshold = self.config.get("warn_threshold_percent", 80)
        
        # Get all disk partitions
        partitions = psutil.disk_partitions(all=False)
        
        partitions_data = []
        warnings = []
        
        for partition in partitions:
            # Skip excluded filesystem types
            if partition.fstype in exclude_types:
                continue
            
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                partition_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                }
                
                # Check warning threshold
                if usage.percent >= warn_threshold:
                    warnings.append({
                        "mountpoint": partition.mountpoint,
                        "usage_percent": usage.percent,
                        "message": f"Disk usage above {warn_threshold}%"
                    })
                
                partitions_data.append(partition_info)
                
            except (PermissionError, OSError):
                # Skip partitions we can't access
                continue
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "partitions": partitions_data,
            "warnings": warnings
        }
        
        # Optional: Disk I/O statistics
        if self.config.get("include_io_stats", True):
            try:
                disk_io = psutil.disk_io_counters(perdisk=False)
                if disk_io:
                    data["io_stats"] = {
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes,
                        "read_time_ms": disk_io.read_time,
                        "write_time_ms": disk_io.write_time
                    }
            except Exception:
                data["io_stats"] = {"error": "I/O stats not available"}
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if disk monitoring is working"""
        try:
            # Try to get disk partitions
            partitions = psutil.disk_partitions()
            if len(partitions) > 0:
                return {
                    "healthy": True,
                    "message": f"Disk monitoring operational ({len(partitions)} partitions found)"
                }
            else:
                return {
                    "healthy": False,
                    "message": "No disk partitions found"
                }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    async def on_config_change(self, new_config: Dict[str, Any]):
        """Validate config when changed"""
        await super().on_config_change(new_config)
        
        # Validate threshold
        threshold = new_config.get("warn_threshold_percent", 80)
        if not (0 <= threshold <= 100):
            raise ValueError("warn_threshold_percent must be between 0 and 100")
