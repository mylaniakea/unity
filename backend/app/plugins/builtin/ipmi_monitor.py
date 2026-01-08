"""
IPMI/BMC Monitor Plugin

Monitors server hardware via IPMI/BMC.
Out-of-band monitoring for in-band peace of mind!
"""

import subprocess
import re
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class IPMIMonitorPlugin(PluginBase):
    """Monitors server hardware via IPMI/iDRAC/iLO"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="ipmi-monitor",
            name="IPMI/BMC Monitor",
            version="1.0.0",
            description="Monitors server hardware via IPMI including temperatures, fans, power, and system events",
            author="Unity Team",
            category=PluginCategory.HARDWARE,
            tags=["ipmi", "bmc", "idrac", "ilo", "hardware", "sensors"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=["ipmitool"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "BMC IP address or hostname"
                    },
                    "username": {
                        "type": "string",
                        "description": "IPMI username"
                    },
                    "password": {
                        "type": "string",
                        "description": "IPMI password"
                    },
                    "interface": {
                        "type": "string",
                        "default": "lanplus",
                        "description": "IPMI interface (lan or lanplus)"
                    }
                },
                "required": ["host", "username", "password"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect IPMI metrics"""
        
        config = self.config or {}
        host = config.get("host")
        username = config.get("username")
        password = config.get("password")
        interface = config.get("interface", "lanplus")
        
        if not all([host, username, password]):
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "IPMI credentials not configured"
            }
        
        ipmi_base = [
            "ipmitool", "-I", interface, "-H", host,
            "-U", username, "-P", password
        ]
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "host": host
        }
        
        try:
            # Get sensor readings
            sensor_data = await self._get_sensors(ipmi_base)
            results["sensors"] = sensor_data
            
            # Get power status
            power_status = await self._get_power_status(ipmi_base)
            results["power"] = power_status
            
            # Get system event log count
            sel_info = await self._get_sel_info(ipmi_base)
            results["sel"] = sel_info
            
            # Calculate summary
            temp_sensors = [s for s in sensor_data if s.get("type") == "temperature"]
            fan_sensors = [s for s in sensor_data if s.get("type") == "fan"]
            
            results["summary"] = {
                "power_on": power_status.get("status") == "on",
                "temperature_sensors": len(temp_sensors),
                "fan_sensors": len(fan_sensors),
                "sel_entries": sel_info.get("entries", 0),
                "healthy": all(s.get("status") == "ok" for s in sensor_data)
            }
            
            return results
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "ipmitool command not found"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _get_sensors(self, ipmi_base: List[str]) -> List[Dict[str, Any]]:
        """Get sensor readings"""
        sensors = []
        
        try:
            result = subprocess.run(
                ipmi_base + ["sensor"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    # Parse sensor output: Name | Value | Units | Status | ...
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        name = parts[0]
                        value = parts[1]
                        units = parts[2]
                        status = parts[3]
                        
                        # Determine sensor type
                        sensor_type = "unknown"
                        if "Temp" in name or "temp" in name:
                            sensor_type = "temperature"
                        elif "Fan" in name or "fan" in name or "FAN" in name:
                            sensor_type = "fan"
                        elif "Volt" in name or "volt" in name:
                            sensor_type = "voltage"
                        elif "Power" in name or "Pwr" in name:
                            sensor_type = "power"
                        
                        sensors.append({
                            "name": name,
                            "value": value,
                            "units": units,
                            "status": status.lower(),
                            "type": sensor_type
                        })
        except Exception:
            pass
        
        return sensors
    
    async def _get_power_status(self, ipmi_base: List[str]) -> Dict[str, Any]:
        """Get chassis power status"""
        try:
            result = subprocess.run(
                ipmi_base + ["chassis", "power", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                if "Chassis Power is on" in result.stdout:
                    return {"status": "on"}
                elif "Chassis Power is off" in result.stdout:
                    return {"status": "off"}
        except Exception:
            pass
        
        return {"status": "unknown"}
    
    async def _get_sel_info(self, ipmi_base: List[str]) -> Dict[str, Any]:
        """Get system event log info"""
        try:
            result = subprocess.run(
                ipmi_base + ["sel", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                match = re.search(r'Entries\s*:\s*(\d+)', result.stdout)
                if match:
                    return {"entries": int(match.group(1))}
        except Exception:
            pass
        
        return {"entries": 0}
    
    async def health_check(self) -> bool:
        try:
            result = subprocess.run(["ipmitool", "-V"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        required = ["host", "username", "password"]
        return all(k in config for k in required)
