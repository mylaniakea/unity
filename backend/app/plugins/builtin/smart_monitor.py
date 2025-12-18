"""
SMART Disk Health Monitor Plugin

Monitors disk health via SMART attributes to predict failures before data loss.
The question is not if drives will fail, but when - and will you know in time?
"""

import subprocess
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class SMARTMonitorPlugin(PluginBase):
    """Monitors disk health using SMART attributes"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="smart-monitor",
            name="SMART Disk Health Monitor",
            version="1.0.0",
            description="Monitors disk health via SMART attributes including reallocated sectors, pending sectors, temperature, and predictive failure warnings",
            author="Unity Team",
            category=PluginCategory.STORAGE,
            tags=["smart", "disk", "health", "hdd", "ssd", "failure-prediction"],
            requires_sudo=True,  # smartctl requires sudo
            supported_os=["linux", "darwin"],
            dependencies=["smartmontools"],  # smartctl command
            config_schema={
                "type": "object",
                "properties": {
                    "devices": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "List of devices to monitor (e.g., ['/dev/sda', '/dev/nvme0n1']). Leave empty to auto-detect."
                    },
                    "temperature_warning": {
                        "type": "integer",
                        "default": 50,
                        "description": "Temperature (°C) to trigger warning"
                    },
                    "temperature_critical": {
                        "type": "integer",
                        "default": 60,
                        "description": "Temperature (°C) to trigger critical alert"
                    },
                    "include_attributes": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include detailed SMART attributes in output"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect SMART data for all configured disks"""
        
        config = self.config or {}
        devices = config.get("devices", [])
        temp_warning = config.get("temperature_warning", 50)
        temp_critical = config.get("temperature_critical", 60)
        include_attributes = config.get("include_attributes", True)
        
        # Auto-detect devices if none specified
        if not devices:
            devices = self._detect_devices()
        
        if not devices:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "No devices found or configured",
                "disks": []
            }
        
        disks_data = []
        
        for device in devices:
            try:
                disk_info = self._check_disk(
                    device,
                    temp_warning,
                    temp_critical,
                    include_attributes
                )
                disks_data.append(disk_info)
            except Exception as e:
                disks_data.append({
                    "device": device,
                    "status": "error",
                    "error": str(e)
                })
        
        # Calculate summary
        total = len(disks_data)
        healthy = sum(1 for d in disks_data if d.get("health") == "PASSED")
        warning = sum(1 for d in disks_data if d.get("warnings"))
        failed = sum(1 for d in disks_data if d.get("health") == "FAILED")
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_disks": total,
                "healthy": healthy,
                "warnings": warning,
                "failed": failed
            },
            "disks": disks_data
        }
    
    def _detect_devices(self) -> List[str]:
        """Auto-detect storage devices"""
        
        try:
            result = subprocess.run(
                ["smartctl", "--scan"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            devices = []
            for line in result.stdout.strip().split('\n'):
                if line and not line.startswith('#'):
                    # Extract device path (first field)
                    device = line.split()[0]
                    devices.append(device)
            
            return devices
            
        except Exception:
            return []
    
    def _check_disk(
        self,
        device: str,
        temp_warning: int,
        temp_critical: int,
        include_attributes: bool
    ) -> Dict[str, Any]:
        """Check SMART status for a single disk"""
        
        try:
            # Run smartctl with JSON output
            result = subprocess.run(
                ["sudo", "smartctl", "-a", "-j", device],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            data = json.loads(result.stdout)
            
            # Extract basic info
            device_info = data.get("device", {})
            model = data.get("model_name") or device_info.get("name", "Unknown")
            serial = data.get("serial_number", "Unknown")
            
            # Get SMART health status
            smart_status = data.get("smart_status", {})
            health = "PASSED" if smart_status.get("passed") else "FAILED"
            
            # Get temperature
            temperature = self._extract_temperature(data)
            
            # Get power-on hours
            power_on_hours = self._extract_power_on_hours(data)
            
            # Check for critical SMART attributes
            warnings = []
            critical_attrs = self._check_critical_attributes(data, warnings)
            
            # Temperature warnings
            if temperature:
                if temperature >= temp_critical:
                    warnings.append(f"Critical temperature: {temperature}°C")
                elif temperature >= temp_warning:
                    warnings.append(f"High temperature: {temperature}°C")
            
            disk_data = {
                "device": device,
                "model": model,
                "serial": serial,
                "health": health,
                "temperature_celsius": temperature,
                "power_on_hours": power_on_hours,
                "warnings": warnings if warnings else None
            }
            
            # Add detailed attributes if requested
            if include_attributes:
                disk_data["attributes"] = self._extract_attributes(data)
            
            return disk_data
            
        except FileNotFoundError:
            raise Exception("smartctl command not found - is smartmontools installed?")
        except json.JSONDecodeError:
            raise Exception("Failed to parse smartctl output")
        except Exception as e:
            raise Exception(f"Failed to check disk: {str(e)}")
    
    def _extract_temperature(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract disk temperature from SMART data"""
        
        # Try temperature field
        temp = data.get("temperature", {}).get("current")
        if temp is not None:
            return temp
        
        # Try ata_smart_attributes
        attrs = data.get("ata_smart_attributes", {}).get("table", [])
        for attr in attrs:
            if attr.get("name") == "Temperature_Celsius":
                return attr.get("raw", {}).get("value")
        
        # Try nvme_smart_health_information_log
        nvme_temp = data.get("nvme_smart_health_information_log", {}).get("temperature")
        if nvme_temp is not None:
            return nvme_temp
        
        return None
    
    def _extract_power_on_hours(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract power-on hours from SMART data"""
        
        # Try power_on_time field
        power_on = data.get("power_on_time", {}).get("hours")
        if power_on is not None:
            return power_on
        
        # Try ata_smart_attributes
        attrs = data.get("ata_smart_attributes", {}).get("table", [])
        for attr in attrs:
            if attr.get("name") == "Power_On_Hours":
                return attr.get("raw", {}).get("value")
        
        # Try nvme_smart_health_information_log
        nvme_hours = data.get("nvme_smart_health_information_log", {}).get("power_on_hours")
        if nvme_hours is not None:
            return nvme_hours
        
        return None
    
    def _check_critical_attributes(
        self,
        data: Dict[str, Any],
        warnings: List[str]
    ) -> bool:
        """Check for critical SMART attributes that indicate drive problems"""
        
        has_critical = False
        
        # Check ATA SMART attributes
        attrs = data.get("ata_smart_attributes", {}).get("table", [])
        
        critical_attrs = {
            "Reallocated_Sector_Ct": "Reallocated sectors detected",
            "Current_Pending_Sector": "Pending sectors detected",
            "Offline_Uncorrectable": "Uncorrectable sectors detected",
            "UDMA_CRC_Error_Count": "CRC errors detected"
        }
        
        for attr in attrs:
            attr_name = attr.get("name")
            raw_value = attr.get("raw", {}).get("value", 0)
            
            if attr_name in critical_attrs and raw_value > 0:
                warnings.append(f"{critical_attrs[attr_name]}: {raw_value}")
                has_critical = True
        
        # Check NVMe critical warnings
        nvme_warnings = data.get("nvme_smart_health_information_log", {}).get("critical_warning")
        if nvme_warnings and nvme_warnings > 0:
            warnings.append("NVMe critical warning flag set")
            has_critical = True
        
        return has_critical
    
    def _extract_attributes(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract detailed SMART attributes"""
        
        attributes = []
        
        # ATA SMART attributes
        ata_attrs = data.get("ata_smart_attributes", {}).get("table", [])
        for attr in ata_attrs:
            attributes.append({
                "id": attr.get("id"),
                "name": attr.get("name"),
                "value": attr.get("value"),
                "worst": attr.get("worst"),
                "thresh": attr.get("thresh"),
                "raw_value": attr.get("raw", {}).get("value"),
                "when_failed": attr.get("when_failed", "")
            })
        
        # NVMe attributes
        nvme_log = data.get("nvme_smart_health_information_log", {})
        if nvme_log:
            attributes.append({
                "name": "NVMe Health",
                "available_spare": nvme_log.get("available_spare"),
                "percentage_used": nvme_log.get("percentage_used"),
                "data_units_read": nvme_log.get("data_units_read"),
                "data_units_written": nvme_log.get("data_units_written")
            })
        
        return attributes
    
    async def health_check(self) -> bool:
        """Check if smartctl is available"""
        try:
            result = subprocess.run(
                ["sudo", "smartctl", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        if not config:
            return True  # Use defaults
        
        devices = config.get("devices")
        if devices and not isinstance(devices, list):
            return False
        
        return True
