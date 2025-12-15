"""
Process Monitor Plugin

Monitors system processes, resource usage, and process count.
"""

import psutil
from datetime import datetime
from typing import Dict, Any, List

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class ProcessMonitorPlugin(PluginBase):
    """Monitors system processes and their resource usage"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="process-monitor",
            name="Process Monitor",
            version="1.0.0",
            description="Monitors system processes, resource usage, and top consumers",
            author="Unity Team",
            category=PluginCategory.SYSTEM,
            tags=["processes", "monitoring", "resources"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psutil"],
            config_schema={
                "type": "object",
                "properties": {
                    "top_processes_count": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of top processes to track"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["cpu", "memory"],
                        "default": "cpu",
                        "description": "Sort top processes by CPU or memory"
                    },
                    "include_cmdline": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include full command line (can be verbose)"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect process metrics"""
        
        top_count = self.config.get("top_processes_count", 10)
        sort_by = self.config.get("sort_by", "cpu")
        include_cmdline = self.config.get("include_cmdline", False)
        
        # Get all processes
        processes: List[Dict] = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                process_data = {
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "username": pinfo['username'],
                    "cpu_percent": pinfo['cpu_percent'],
                    "memory_percent": round(pinfo['memory_percent'], 2),
                    "status": pinfo['status']
                }
                
                if include_cmdline:
                    try:
                        process_data["cmdline"] = " ".join(proc.cmdline())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        process_data["cmdline"] = ""
                
                processes.append(process_data)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort and get top processes
        sort_key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        top_processes = sorted(processes, key=lambda x: x[sort_key], reverse=True)[:top_count]
        
        # Process count by status
        status_counts = {}
        for proc in processes:
            status = proc['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_processes": len(processes),
                "status_counts": status_counts
            },
            f"top_{top_count}_by_{sort_by}": top_processes
        }
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if process monitoring is working"""
        try:
            # Try to get process list
            procs = list(psutil.process_iter())
            return {
                "healthy": True,
                "message": f"Process monitoring operational ({len(procs)} processes)"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    async def on_config_change(self, new_config: Dict[str, Any]):
        """Validate config when changed"""
        await super().on_config_change(new_config)
        
        # Validate top_processes_count
        count = new_config.get("top_processes_count", 10)
        if not (1 <= count <= 100):
            raise ValueError("top_processes_count must be between 1 and 100")
