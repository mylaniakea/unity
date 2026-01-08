"""
ZFS/BTRFS Monitor Plugin

Monitors ZFS and BTRFS advanced filesystems.
Advanced filesystems require advanced monitoring - data integrity matters!
"""

import subprocess
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class ZFSBTRFSMonitorPlugin(PluginBase):
    """Monitors ZFS and BTRFS filesystems"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="zfs-btrfs-monitor",
            name="ZFS/BTRFS Monitor",
            version="1.0.0",
            description="Monitors ZFS and BTRFS advanced filesystems including pool health, scrubs, compression ratios, and snapshots",
            author="Unity Team",
            category=PluginCategory.STORAGE,
            tags=["zfs", "btrfs", "filesystem", "storage", "snapshots", "scrub"],
            requires_sudo=True,  # ZFS and BTRFS commands often need sudo
            supported_os=["linux"],
            dependencies=[],  # Uses system commands
            config_schema={
                "type": "object",
                "properties": {
                    "filesystem_type": {
                        "type": "string",
                        "enum": ["zfs", "btrfs"],
                        "description": "Type of filesystem to monitor"
                    },
                    "pools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of pools/filesystems to monitor (leave empty for all)"
                    }
                },
                "required": ["filesystem_type"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect filesystem metrics"""
        
        config = self.config or {}
        fs_type = config.get("filesystem_type", "").lower()
        
        if fs_type == "zfs":
            return self._monitor_zfs(config)
        elif fs_type == "btrfs":
            return self._monitor_btrfs(config)
        else:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Unknown filesystem type: {fs_type}",
                "supported_types": ["zfs", "btrfs"]
            }
    
    def _monitor_zfs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor ZFS filesystems"""
        
        pools_filter = config.get("pools", [])
        
        try:
            # Get pool list
            result = subprocess.run(
                ["sudo", "zpool", "list", "-H", "-o", "name,size,alloc,free,health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "filesystem_type": "zfs",
                    "error": "Failed to get ZFS pool list"
                }
            
            pools = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 5:
                    continue
                
                pool_name = parts[0]
                
                # Filter if specified
                if pools_filter and pool_name not in pools_filter:
                    continue
                
                # Get detailed pool info
                pool_info = self._get_zfs_pool_details(pool_name)
                pools.append(pool_info)
            
            # Calculate summary
            total_pools = len(pools)
            healthy_pools = sum(1 for p in pools if p.get("health") == "ONLINE")
            degraded_pools = sum(1 for p in pools if p.get("health") == "DEGRADED")
            faulted_pools = sum(1 for p in pools if p.get("health") == "FAULTED")
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filesystem_type": "zfs",
                "summary": {
                    "total_pools": total_pools,
                    "healthy_pools": healthy_pools,
                    "degraded_pools": degraded_pools,
                    "faulted_pools": faulted_pools
                },
                "pools": pools
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filesystem_type": "zfs",
                "error": "zpool command not found - is ZFS installed?"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filesystem_type": "zfs",
                "error": str(e)
            }
    
    def _get_zfs_pool_details(self, pool_name: str) -> Dict[str, Any]:
        """Get detailed info for a ZFS pool"""
        
        pool_info = {"name": pool_name}
        
        try:
            # Get pool status
            status_result = subprocess.run(
                ["sudo", "zpool", "status", pool_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse status output
            for line in status_result.stdout.split('\n'):
                line = line.strip()
                if "state:" in line.lower():
                    pool_info["health"] = line.split(":")[-1].strip()
                elif "scan:" in line.lower():
                    pool_info["last_scan"] = line.split(":", 1)[-1].strip()
            
            # Get pool properties
            props_result = subprocess.run(
                ["sudo", "zpool", "get", "all", "-H", "-p", pool_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in props_result.stdout.split('\n'):
                parts = line.split('\t')
                if len(parts) >= 3:
                    prop_name = parts[1]
                    prop_value = parts[2]
                    
                    if prop_name == "size":
                        pool_info["size_bytes"] = int(prop_value)
                    elif prop_name == "allocated":
                        pool_info["allocated_bytes"] = int(prop_value)
                    elif prop_name == "free":
                        pool_info["free_bytes"] = int(prop_value)
                    elif prop_name == "fragmentation":
                        pool_info["fragmentation_percent"] = prop_value
                    elif prop_name == "capacity":
                        pool_info["capacity_percent"] = prop_value
            
            # Get compression ratio
            zfs_result = subprocess.run(
                ["sudo", "zfs", "get", "-H", "-o", "value", "compressratio", pool_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            pool_info["compression_ratio"] = zfs_result.stdout.strip()
            
        except Exception:
            pass
        
        return pool_info
    
    def _monitor_btrfs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor BTRFS filesystems"""
        
        try:
            # Get filesystem list
            result = subprocess.run(
                ["sudo", "btrfs", "filesystem", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "filesystem_type": "btrfs",
                    "error": "Failed to get BTRFS filesystem list"
                }
            
            filesystems = self._parse_btrfs_show(result.stdout)
            
            # Get usage info for each filesystem
            for fs in filesystems:
                mount_point = fs.get("mount_point")
                if mount_point:
                    usage = self._get_btrfs_usage(mount_point)
                    fs.update(usage)
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filesystem_type": "btrfs",
                "summary": {
                    "total_filesystems": len(filesystems)
                },
                "filesystems": filesystems
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filesystem_type": "btrfs",
                "error": "btrfs command not found - is BTRFS installed?"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filesystem_type": "btrfs",
                "error": str(e)
            }
    
    def _parse_btrfs_show(self, output: str) -> List[Dict[str, Any]]:
        """Parse btrfs filesystem show output"""
        
        filesystems = []
        current_fs = None
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Label:"):
                if current_fs:
                    filesystems.append(current_fs)
                
                # Parse label and UUID
                parts = line.split()
                label = parts[1].strip("'") if len(parts) > 1 else "none"
                uuid = None
                for i, part in enumerate(parts):
                    if part == "uuid:":
                        uuid = parts[i+1] if i+1 < len(parts) else None
                        break
                
                current_fs = {
                    "label": label,
                    "uuid": uuid,
                    "devices": []
                }
            
            elif line.startswith("Total devices"):
                if current_fs:
                    match = re.search(r'Total devices (\d+)', line)
                    if match:
                        current_fs["total_devices"] = int(match.group(1))
            
            elif line.startswith("devid"):
                if current_fs:
                    # Parse device line
                    device = re.search(r'path (.+)$', line)
                    if device:
                        current_fs["devices"].append(device.group(1))
        
        if current_fs:
            filesystems.append(current_fs)
        
        return filesystems
    
    def _get_btrfs_usage(self, mount_point: str) -> Dict[str, Any]:
        """Get BTRFS filesystem usage"""
        
        usage = {}
        
        try:
            result = subprocess.run(
                ["sudo", "btrfs", "filesystem", "usage", mount_point],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in result.stdout.split('\n'):
                if "Device size:" in line:
                    usage["device_size"] = line.split(":")[-1].strip()
                elif "Used:" in line:
                    usage["used"] = line.split(":")[-1].strip()
                elif "Free (estimated):" in line:
                    usage["free_estimated"] = line.split(":")[-1].strip()
            
        except Exception:
            pass
        
        return usage
    
    async def health_check(self) -> bool:
        """Check if filesystem tools are available"""
        
        config = self.config or {}
        fs_type = config.get("filesystem_type", "").lower()
        
        try:
            if fs_type == "zfs":
                result = subprocess.run(
                    ["zpool", "version"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            elif fs_type == "btrfs":
                result = subprocess.run(
                    ["btrfs", "version"],
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
        
        fs_type = config.get("filesystem_type")
        return fs_type in ["zfs", "btrfs"]
