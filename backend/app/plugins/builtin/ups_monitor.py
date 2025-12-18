"""
UPS Monitor Plugin

Monitors UPS (Uninterruptible Power Supply) status via Network UPS Tools (NUT).
Because power outages at 3 AM shouldn't be a mystery, and battery deaths shouldn't be a surprise.
"""

import subprocess
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class UPSMonitorPlugin(PluginBase):
    """Monitors UPS battery health, runtime, and power events via NUT"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="ups-monitor",
            name="UPS Monitor",
            version="1.0.0",
            description="Monitors UPS battery health, runtime estimates, power events, and load via Network UPS Tools (NUT)",
            author="Unity Team",
            category=PluginCategory.POWER,
            tags=["ups", "power", "battery", "nut", "backup-power", "runtime"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=["nut-client"],  # Network UPS Tools client
            config_schema={
                "type": "object",
                "properties": {
                    "ups_name": {
                        "type": "string",
                        "default": "ups",
                        "description": "UPS name as configured in NUT (default: 'ups')"
                    },
                    "nut_server": {
                        "type": "string",
                        "default": "localhost",
                        "description": "NUT server hostname or IP"
                    },
                    "battery_warning_percent": {
                        "type": "integer",
                        "default": 50,
                        "description": "Battery charge percentage to trigger warnings"
                    },
                    "runtime_warning_minutes": {
                        "type": "integer",
                        "default": 10,
                        "description": "Runtime minutes remaining to trigger warnings"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect UPS metrics from NUT"""
        
        config = self.config or {}
        ups_name = config.get("ups_name", "ups")
        nut_server = config.get("nut_server", "localhost")
        battery_warning = config.get("battery_warning_percent", 50)
        runtime_warning = config.get("runtime_warning_minutes", 10)
        
        try:
            # Get UPS variables from NUT
            ups_vars = self._get_ups_variables(ups_name, nut_server)
            
            if not ups_vars:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": f"Could not connect to UPS '{ups_name}' on {nut_server}",
                    "status": "unknown"
                }
            
            # Parse and structure the data
            parsed_data = self._parse_ups_data(ups_vars)
            
            # Add warning flags
            parsed_data["warnings"] = self._generate_warnings(
                parsed_data,
                battery_warning,
                runtime_warning
            )
            
            # Add timestamp
            parsed_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            parsed_data["ups_name"] = ups_name
            parsed_data["server"] = nut_server
            
            return parsed_data
            
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "status": "error"
            }
    
    def _get_ups_variables(self, ups_name: str, server: str) -> Dict[str, str]:
        """Get all UPS variables via upsc command"""
        
        try:
            # Run upsc command to get UPS variables
            result = subprocess.run(
                ["upsc", f"{ups_name}@{server}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {}
            
            # Parse output into dict
            ups_vars = {}
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    ups_vars[key.strip()] = value.strip()
            
            return ups_vars
            
        except subprocess.TimeoutExpired:
            raise Exception("Timeout connecting to NUT server")
        except FileNotFoundError:
            raise Exception("upsc command not found - is NUT client installed?")
        except Exception as e:
            raise Exception(f"Failed to query UPS: {str(e)}")
    
    def _parse_ups_data(self, ups_vars: Dict[str, str]) -> Dict[str, Any]:
        """Parse raw UPS variables into structured data"""
        
        # Extract battery information
        battery = {
            "charge_percent": self._to_float(ups_vars.get("battery.charge")),
            "voltage": self._to_float(ups_vars.get("battery.voltage")),
            "voltage_nominal": self._to_float(ups_vars.get("battery.voltage.nominal")),
            "runtime_seconds": self._to_int(ups_vars.get("battery.runtime")),
            "runtime_minutes": self._to_int(ups_vars.get("battery.runtime")) // 60 if ups_vars.get("battery.runtime") else None,
            "type": ups_vars.get("battery.type"),
            "temperature": self._to_float(ups_vars.get("battery.temperature"))
        }
        
        # Extract input power information
        input_power = {
            "voltage": self._to_float(ups_vars.get("input.voltage")),
            "voltage_nominal": self._to_float(ups_vars.get("input.voltage.nominal")),
            "frequency": self._to_float(ups_vars.get("input.frequency")),
            "transfer_high": self._to_float(ups_vars.get("input.transfer.high")),
            "transfer_low": self._to_float(ups_vars.get("input.transfer.low"))
        }
        
        # Extract output power information
        output_power = {
            "voltage": self._to_float(ups_vars.get("output.voltage")),
            "voltage_nominal": self._to_float(ups_vars.get("output.voltage.nominal")),
            "frequency": self._to_float(ups_vars.get("output.frequency")),
            "current": self._to_float(ups_vars.get("output.current"))
        }
        
        # Extract load and power
        load_percent = self._to_float(ups_vars.get("ups.load"))
        power_nominal = self._to_float(ups_vars.get("ups.power.nominal"))
        power_actual = (load_percent / 100 * power_nominal) if (load_percent and power_nominal) else None
        
        # Extract UPS status
        status_str = ups_vars.get("ups.status", "UNKNOWN")
        status = self._parse_status(status_str)
        
        # Device information
        device_info = {
            "manufacturer": ups_vars.get("device.mfr") or ups_vars.get("ups.mfr"),
            "model": ups_vars.get("device.model") or ups_vars.get("ups.model"),
            "serial": ups_vars.get("device.serial") or ups_vars.get("ups.serial"),
            "firmware": ups_vars.get("ups.firmware"),
            "type": ups_vars.get("ups.type")
        }
        
        return {
            "status": status,
            "battery": battery,
            "input": input_power,
            "output": output_power,
            "load": {
                "percent": load_percent,
                "watts": power_actual,
                "nominal_watts": power_nominal
            },
            "device": device_info,
            "raw_status": status_str
        }
    
    def _parse_status(self, status_str: str) -> Dict[str, Any]:
        """Parse UPS status string into components"""
        
        # Common NUT status codes
        status_map = {
            "OL": "online",           # On line (mains is present)
            "OB": "on_battery",       # On battery
            "LB": "low_battery",      # Low battery
            "RB": "replace_battery",  # Battery needs replacement
            "CHRG": "charging",       # Battery is charging
            "DISCHRG": "discharging", # Battery is discharging
            "BYPASS": "bypass",       # UPS is bypassed
            "CAL": "calibrating",     # UPS is calibrating
            "OFF": "offline",         # UPS is offline
            "OVER": "overloaded",     # UPS is overloaded
            "TRIM": "trimming",       # UPS is trimming voltage
            "BOOST": "boosting"       # UPS is boosting voltage
        }
        
        codes = status_str.split()
        parsed = {
            "online": "OL" in codes,
            "on_battery": "OB" in codes,
            "low_battery": "LB" in codes,
            "replace_battery": "RB" in codes,
            "charging": "CHRG" in codes,
            "discharging": "DISCHRG" in codes,
            "bypassed": "BYPASS" in codes,
            "calibrating": "CAL" in codes,
            "offline": "OFF" in codes,
            "overloaded": "OVER" in codes
        }
        
        # Determine overall health status
        if "RB" in codes:
            health = "critical"
        elif "LB" in codes or "OB" in codes:
            health = "warning"
        elif "OVER" in codes:
            health = "error"
        elif "OL" in codes:
            health = "healthy"
        else:
            health = "unknown"
        
        parsed["health"] = health
        parsed["codes"] = codes
        
        return parsed
    
    def _generate_warnings(
        self,
        data: Dict[str, Any],
        battery_warning: int,
        runtime_warning: int
    ) -> List[str]:
        """Generate warning messages based on UPS state"""
        
        warnings = []
        
        # Check battery charge
        battery_charge = data["battery"].get("charge_percent")
        if battery_charge is not None and battery_charge < battery_warning:
            warnings.append(f"Battery charge low: {battery_charge}%")
        
        # Check runtime
        runtime_minutes = data["battery"].get("runtime_minutes")
        if runtime_minutes is not None and runtime_minutes < runtime_warning:
            warnings.append(f"Runtime low: {runtime_minutes} minutes remaining")
        
        # Check status flags
        status = data["status"]
        if status.get("replace_battery"):
            warnings.append("Battery replacement recommended")
        if status.get("low_battery"):
            warnings.append("UPS reports low battery")
        if status.get("on_battery"):
            warnings.append("UPS is running on battery power")
        if status.get("overloaded"):
            warnings.append("UPS is overloaded")
        
        return warnings
    
    def _to_float(self, value: Optional[str]) -> Optional[float]:
        """Safely convert string to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _to_int(self, value: Optional[str]) -> Optional[int]:
        """Safely convert string to int"""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    async def health_check(self) -> bool:
        """Check if the plugin can communicate with NUT"""
        try:
            result = subprocess.run(
                ["upsc", "-l"],
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
        
        ups_name = config.get("ups_name")
        if ups_name and not isinstance(ups_name, str):
            return False
        
        return True
