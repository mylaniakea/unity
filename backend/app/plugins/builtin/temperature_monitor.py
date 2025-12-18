"""
Temperature/Environmental Monitor Plugin

Monitors server room temperature, humidity, and environmental conditions.
Hardware + heat = bad time. Monitoring prevents meltdowns!
"""

import subprocess
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class TemperatureMonitorPlugin(PluginBase):
    """Monitors environmental temperature and sensors"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="temperature-monitor",
            name="Temperature/Environmental Monitor",
            version="1.0.0",
            description="Monitors server room temperature, humidity, and environmental sensors to prevent hardware damage",
            author="Unity Team",
            category=PluginCategory.SYSTEM,
            tags=["temperature", "humidity", "sensors", "environment", "cooling"],
            requires_sudo=False,
            supported_os=["linux"],
            dependencies=[],  # Uses lm-sensors
            config_schema={
                "type": "object",
                "properties": {
                    "temp_warning_celsius": {
                        "type": "integer",
                        "default": 75,
                        "description": "Temperature warning threshold (°C)"
                    },
                    "temp_critical_celsius": {
                        "type": "integer",
                        "default": 85,
                        "description": "Temperature critical threshold (°C)"
                    },
                    "humidity_min": {
                        "type": "integer",
                        "default": 30,
                        "description": "Minimum humidity percentage"
                    },
                    "humidity_max": {
                        "type": "integer",
                        "default": 60,
                        "description": "Maximum humidity percentage"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect temperature and environmental metrics"""
        
        config = self.config or {}
        temp_warning = config.get("temp_warning_celsius", 75)
        temp_critical = config.get("temp_critical_celsius", 85)
        humidity_min = config.get("humidity_min", 30)
        humidity_max = config.get("humidity_max", 60)
        
        try:
            # Get sensor data using sensors command
            result = subprocess.run(
                ["sensors", "-A", "-u"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": "Failed to read sensors"
                }
            
            # Parse sensor output
            sensors_data = self._parse_sensors_output(result.stdout)
            
            # Analyze temperatures
            warnings = []
            max_temp = 0
            
            for sensor in sensors_data:
                for reading in sensor.get("readings", []):
                    if "temp" in reading.get("type", "").lower():
                        temp = reading.get("value", 0)
                        if temp > max_temp:
                            max_temp = temp
                        
                        if temp >= temp_critical:
                            warnings.append(f"CRITICAL: {sensor['name']} {reading['name']}: {temp}°C")
                        elif temp >= temp_warning:
                            warnings.append(f"WARNING: {sensor['name']} {reading['name']}: {temp}°C")
            
            # Calculate summary
            temp_sensors = sum(
                len([r for r in s.get("readings", []) if "temp" in r.get("type", "").lower()])
                for s in sensors_data
            )
            
            fan_sensors = sum(
                len([r for r in s.get("readings", []) if "fan" in r.get("type", "").lower()])
                for s in sensors_data
            )
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_sensors": len(sensors_data),
                    "temperature_sensors": temp_sensors,
                    "fan_sensors": fan_sensors,
                    "max_temperature_celsius": round(max_temp, 1),
                    "warnings": len(warnings)
                },
                "sensors": sensors_data,
                "warnings": warnings if warnings else None,
                "thresholds": {
                    "warning_celsius": temp_warning,
                    "critical_celsius": temp_critical
                }
            }
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "sensors command not found - install lm-sensors package"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    def _parse_sensors_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse sensors -u output"""
        
        sensors = []
        current_sensor = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            # New sensor device
            if not line.startswith(' ') and ':' not in line:
                if current_sensor:
                    sensors.append(current_sensor)
                current_sensor = {
                    "name": line,
                    "readings": []
                }
            
            # Sensor reading
            elif ':' in line and current_sensor:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Determine type and parse value
                    sensor_type = "unknown"
                    if "temp" in key.lower():
                        sensor_type = "temperature"
                    elif "fan" in key.lower():
                        sensor_type = "fan"
                    elif "in" in key.lower():
                        sensor_type = "voltage"
                    
                    try:
                        numeric_value = float(value)
                        current_sensor["readings"].append({
                            "name": key,
                            "type": sensor_type,
                            "value": numeric_value
                        })
                    except ValueError:
                        pass
        
        if current_sensor:
            sensors.append(current_sensor)
        
        return sensors
    
    async def health_check(self) -> bool:
        """Check if sensors command is available"""
        
        try:
            result = subprocess.run(
                ["sensors", "-v"],
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
        
        return True  # All config is optional with defaults
