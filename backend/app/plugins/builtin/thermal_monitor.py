"""
Thermal Monitor Plugin

Monitors CPU and GPU temperatures using platform-specific sensors.
Requires psutil and platform-specific tools (lm-sensors on Linux).
"""

import psutil
import platform
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class ThermalMonitorPlugin(PluginBase):
    """Monitors system temperatures (CPU, GPU, etc.)"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="thermal-monitor",
            name="Thermal Monitor",
            version="1.0.0",
            description="Monitors CPU, GPU, and system temperatures using hardware sensors",
            author="Unity Team",
            category=PluginCategory.THERMAL,
            tags=["thermal", "temperature", "cpu", "gpu", "sensors"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psutil"],
            config_schema={
                "type": "object",
                "properties": {
                    "temp_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                        "description": "Temperature unit to use"
                    },
                    "critical_temp_celsius": {
                        "type": "number",
                        "default": 85.0,
                        "description": "Critical temperature threshold in Celsius"
                    },
                    "warning_temp_celsius": {
                        "type": "number",
                        "default": 75.0,
                        "description": "Warning temperature threshold in Celsius"
                    },
                    "include_per_core": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include per-core temperature readings"
                    }
                }
            }
        )
    
    def _celsius_to_fahrenheit(self, celsius: float) -> float:
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32
    
    def _format_temp(self, celsius: float) -> Dict[str, float]:
        """Format temperature based on config"""
        unit = self.config.get("temp_unit", "celsius")
        if unit == "fahrenheit":
            return {
                "value": round(self._celsius_to_fahrenheit(celsius), 2),
                "unit": "F"
            }
        return {
            "value": round(celsius, 2),
            "unit": "C"
        }
    
    def _get_temp_status(self, celsius: float) -> str:
        """Determine temperature status"""
        critical = self.config.get("critical_temp_celsius", 85.0)
        warning = self.config.get("warning_temp_celsius", 75.0)
        
        if celsius >= critical:
            return "critical"
        elif celsius >= warning:
            return "warning"
        return "normal"
    
    def _get_psutil_temps(self) -> Dict[str, Any]:
        """Get temperatures using psutil"""
        temps = {}
        
        try:
            # Get all temperature sensors
            if hasattr(psutil, "sensors_temperatures"):
                sensors = psutil.sensors_temperatures()
                
                if sensors:
                    for name, entries in sensors.items():
                        sensor_temps = []
                        for entry in entries:
                            temp_data = {
                                "label": entry.label or name,
                                "temperature": self._format_temp(entry.current),
                                "status": self._get_temp_status(entry.current)
                            }
                            
                            # Add high/critical thresholds if available
                            if entry.high:
                                temp_data["high_threshold"] = self._format_temp(entry.high)
                            if entry.critical:
                                temp_data["critical_threshold"] = self._format_temp(entry.critical)
                            
                            sensor_temps.append(temp_data)
                        
                        temps[name] = sensor_temps
        except Exception as e:
            temps["error"] = f"Failed to read psutil temperatures: {str(e)}"
        
        return temps
    
    def _get_linux_cpu_temps(self) -> Optional[Dict[str, Any]]:
        """Get CPU temperatures on Linux using /sys/class/thermal"""
        try:
            cpu_temps = []
            thermal_zones = []
            
            # Find thermal zones
            import os
            thermal_base = "/sys/class/thermal"
            if os.path.exists(thermal_base):
                for zone in os.listdir(thermal_base):
                    if zone.startswith("thermal_zone"):
                        zone_path = os.path.join(thermal_base, zone)
                        type_file = os.path.join(zone_path, "type")
                        temp_file = os.path.join(zone_path, "temp")
                        
                        if os.path.exists(type_file) and os.path.exists(temp_file):
                            with open(type_file, 'r') as f:
                                zone_type = f.read().strip()
                            with open(temp_file, 'r') as f:
                                # Temperature is in millidegrees
                                temp_millidegrees = int(f.read().strip())
                                temp_celsius = temp_millidegrees / 1000.0
                                
                                cpu_temps.append({
                                    "label": f"{zone_type} ({zone})",
                                    "temperature": self._format_temp(temp_celsius),
                                    "status": self._get_temp_status(temp_celsius)
                                })
            
            if cpu_temps:
                return {"thermal_zones": cpu_temps}
        except Exception as e:
            return {"error": f"Failed to read Linux thermal zones: {str(e)}"}
        
        return None
    
    def _get_nvidia_gpu_temps(self) -> Optional[Dict[str, Any]]:
        """Get NVIDIA GPU temperatures using nvidia-smi"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                gpus = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 3:
                            index, name, temp = parts[0], parts[1], float(parts[2])
                            gpus.append({
                                "index": int(index),
                                "name": name,
                                "temperature": self._format_temp(temp),
                                "status": self._get_temp_status(temp)
                            })
                
                if gpus:
                    return {"nvidia_gpus": gpus}
        except FileNotFoundError:
            # nvidia-smi not available
            pass
        except Exception as e:
            return {"error": f"Failed to query NVIDIA GPU: {str(e)}"}
        
        return None
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect thermal data from all available sources"""
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "platform": platform.system().lower(),
            "sensors": {}
        }
        
        # Get psutil temperatures (works on most platforms)
        psutil_temps = self._get_psutil_temps()
        if psutil_temps:
            data["sensors"]["psutil"] = psutil_temps
        
        # Platform-specific collection
        if platform.system().lower() == "linux":
            # Try Linux thermal zones
            linux_temps = self._get_linux_cpu_temps()
            if linux_temps:
                data["sensors"]["linux_thermal"] = linux_temps
        
        # Try NVIDIA GPU (all platforms)
        nvidia_temps = self._get_nvidia_gpu_temps()
        if nvidia_temps:
            data["sensors"]["nvidia"] = nvidia_temps
        
        # Calculate summary statistics
        all_temps = []
        for source in data["sensors"].values():
            if isinstance(source, dict):
                self._extract_temps(source, all_temps)
        
        if all_temps:
            data["summary"] = {
                "max_temperature": self._format_temp(max(all_temps)),
                "avg_temperature": self._format_temp(sum(all_temps) / len(all_temps)),
                "min_temperature": self._format_temp(min(all_temps)),
                "sensor_count": len(all_temps),
                "critical_count": sum(1 for t in all_temps if self._get_temp_status(t) == "critical"),
                "warning_count": sum(1 for t in all_temps if self._get_temp_status(t) == "warning")
            }
        
        return data
    
    def _extract_temps(self, obj: Any, temps: List[float]) -> None:
        """Recursively extract temperature values in Celsius"""
        if isinstance(obj, dict):
            if "temperature" in obj and isinstance(obj["temperature"], dict):
                # Convert back to Celsius for comparison
                temp_value = obj["temperature"]["value"]
                if obj["temperature"]["unit"] == "F":
                    temp_value = (temp_value - 32) * 5/9
                temps.append(temp_value)
            
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    self._extract_temps(value, temps)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_temps(item, temps)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if thermal sensors are available"""
        try:
            # Try to collect data
            data = await self.collect_data()
            
            # Check if we got any sensor data
            has_sensors = bool(data.get("sensors"))
            sensor_count = len(data.get("sensors", {}))
            
            if has_sensors:
                return {
                    "healthy": True,
                    "message": f"Thermal monitoring operational with {sensor_count} sensor source(s)",
                    "details": {
                        "sensor_sources": list(data.get("sensors", {}).keys()),
                        "total_sensors": data.get("summary", {}).get("sensor_count", 0)
                    }
                }
            else:
                return {
                    "healthy": False,
                    "message": "No thermal sensors detected",
                    "details": {
                        "platform": platform.system(),
                        "suggestion": "Install lm-sensors (Linux) or check sensor availability"
                    }
                }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
