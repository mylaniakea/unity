"""
Network Switch Monitor Plugin

Monitors network switches via SNMP.
For the homelabber who VLANs everything!
"""

import subprocess
import re
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class NetworkSwitchMonitorPlugin(PluginBase):
    """Monitors network switches via SNMP"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="network-switch-monitor",
            name="Network Switch Monitor",
            version="1.0.0",
            description="Monitors network switches via SNMP including port status, traffic, and uptime",
            author="Unity Team",
            category=PluginCategory.NETWORK,
            tags=["snmp", "switch", "network", "ports", "traffic"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=["snmpwalk", "snmpget"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Switch IP address or hostname"
                    },
                    "community": {
                        "type": "string",
                        "default": "public",
                        "description": "SNMP community string"
                    },
                    "version": {
                        "type": "string",
                        "default": "2c",
                        "description": "SNMP version (1, 2c, or 3)"
                    },
                    "port": {
                        "type": "integer",
                        "default": 161,
                        "description": "SNMP port"
                    }
                },
                "required": ["host"]
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect switch metrics via SNMP"""
        
        config = self.config or {}
        host = config.get("host")
        community = config.get("community", "public")
        version = config.get("version", "2c")
        port = config.get("port", 161)
        
        if not host:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Switch host not configured"
            }
        
        snmp_base = ["-v", version, "-c", community, f"{host}:{port}"]
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "host": host,
        }
        
        try:
            # Get system information
            system_info = await self._get_system_info(snmp_base)
            results.update(system_info)
            
            # Get interface stats
            interface_stats = await self._get_interface_stats(snmp_base)
            results["interfaces"] = interface_stats
            
            # Calculate summary
            total_ports = len(interface_stats)
            up_ports = sum(1 for iface in interface_stats if iface.get("status") == "up")
            
            results["summary"] = {
                "total_ports": total_ports,
                "up_ports": up_ports,
                "down_ports": total_ports - up_ports
            }
            
            return results
            
        except FileNotFoundError:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "SNMP tools not installed (snmpwalk, snmpget)"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    async def _get_system_info(self, snmp_base: List[str]) -> Dict[str, Any]:
        """Get system information via SNMP"""
        info = {}
        
        # sysDescr
        try:
            result = subprocess.run(
                ["snmpget", *snmp_base, "SNMPv2-MIB::sysDescr.0"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                match = re.search(r'STRING: (.+)', result.stdout)
                if match:
                    info["description"] = match.group(1).strip()
        except Exception:
            pass
        
        # sysUpTime
        try:
            result = subprocess.run(
                ["snmpget", *snmp_base, "DISMAN-EVENT-MIB::sysUpTimeInstance"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                match = re.search(r'Timeticks: \((\d+)\)', result.stdout)
                if match:
                    ticks = int(match.group(1))
                    info["uptime_seconds"] = ticks // 100
                    info["uptime_human"] = self._format_uptime(ticks // 100)
        except Exception:
            pass
        
        # sysName
        try:
            result = subprocess.run(
                ["snmpget", *snmp_base, "SNMPv2-MIB::sysName.0"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                match = re.search(r'STRING: (.+)', result.stdout)
                if match:
                    info["hostname"] = match.group(1).strip()
        except Exception:
            pass
        
        return info
    
    async def _get_interface_stats(self, snmp_base: List[str]) -> List[Dict[str, Any]]:
        """Get interface statistics via SNMP"""
        interfaces = []
        
        try:
            # Get interface names
            result = subprocess.run(
                ["snmpwalk", *snmp_base, "IF-MIB::ifDescr"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    match = re.search(r'IF-MIB::ifDescr\.(\d+) = STRING: (.+)', line)
                    if match:
                        index = match.group(1)
                        name = match.group(2).strip()
                        
                        # Get operational status
                        status_result = subprocess.run(
                            ["snmpget", *snmp_base, f"IF-MIB::ifOperStatus.{index}"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        status = "unknown"
                        if status_result.returncode == 0:
                            if "up(1)" in status_result.stdout:
                                status = "up"
                            elif "down(2)" in status_result.stdout:
                                status = "down"
                        
                        interfaces.append({
                            "index": index,
                            "name": name,
                            "status": status
                        })
        except Exception:
            pass
        
        return interfaces
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in human-readable format"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"
    
    async def health_check(self) -> bool:
        try:
            result = subprocess.run(["snmpget", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "host" in config and isinstance(config["host"], str)
