"""
Firewall Monitor Plugin

Monitors firewall rules, blocked connections, and security events.
Supports iptables, ufw, firewalld on Linux.

Author: Unity Team
Created: 2025-12-17
"""

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import subprocess
import re
import os
from collections import defaultdict

logger = logging.getLogger(__name__)


class FirewallMonitorPlugin(PluginBase):
    """Firewall monitoring and security analysis plugin"""
    
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        self.firewall_type = None
        self.blocked_ips = defaultdict(int)
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            id="firewall-monitor",
            name="Firewall Monitor",
            version="1.0.0",
            description="Monitors firewall rules, blocked connections, and security events",
            author="Unity Team",
            category=PluginCategory.SECURITY,
            tags=["security", "firewall", "iptables", "ufw", "firewalld", "network"],
            requires_sudo=True,
            supported_os=["linux"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "firewall_type": {
                        "type": "string",
                        "enum": ["auto", "iptables", "ufw", "firewalld"],
                        "default": "auto",
                        "description": "Firewall type to monitor (auto-detect if not specified)"
                    },
                    "monitor_logs": {
                        "type": "boolean",
                        "default": True,
                        "description": "Monitor firewall logs for blocked connections"
                    },
                    "log_files": {
                        "type": "array",
                        "default": ["/var/log/ufw.log", "/var/log/kern.log", "/var/log/messages"],
                        "description": "Log files to monitor for firewall events"
                    },
                    "collect_rules": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect current firewall rules"
                    },
                    "collect_stats": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect firewall statistics (packet/byte counts)"
                    },
                    "top_blocked_limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Number of top blocked IPs to report"
                    }
                },
                "required": []
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """
        Collect firewall data and analyze security events.
        
        Returns:
            Dictionary containing firewall metrics and alerts
            
        Raises:
            Exception: If data collection fails
        """
        try:
            logger.info("Collecting firewall data")
            
            # Detect firewall type if auto
            if not self.firewall_type:
                self.firewall_type = self._detect_firewall()
            
            if not self.firewall_type:
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "no_firewall",
                    "message": "No supported firewall detected"
                }
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active",
                "firewall_type": self.firewall_type,
                "firewall_status": self._get_firewall_status()
            }
            
            # Collect rules
            if self.config.get("collect_rules", True):
                data["rules"] = self._get_firewall_rules()
            
            # Collect statistics
            if self.config.get("collect_stats", True):
                data["statistics"] = self._get_firewall_stats()
            
            # Monitor logs for blocked connections
            if self.config.get("monitor_logs", True):
                blocked_data = self._analyze_blocked_connections()
                data["blocked_connections"] = blocked_data["blocked_connections"]
                data["top_blocked_ips"] = blocked_data["top_blocked_ips"]
                data["alerts"] = blocked_data["alerts"]
            
            return data
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing firewall: {e}")
            self._last_error = str(e)
            raise Exception("This plugin requires sudo/root access to monitor firewall")
        except Exception as e:
            logger.error(f"Data collection failed: {str(e)}", exc_info=True)
            self._last_error = str(e)
            raise
    
    def _detect_firewall(self) -> Optional[str]:
        """Auto-detect active firewall"""
        
        # Check for ufw
        try:
            result = subprocess.run(
                ["which", "ufw"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Check if ufw is active
                result = subprocess.run(
                    ["sudo", "ufw", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "Status: active" in result.stdout:
                    return "ufw"
        except:
            pass
        
        # Check for firewalld
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "firewalld"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "active" in result.stdout:
                return "firewalld"
        except:
            pass
        
        # Check for iptables
        try:
            result = subprocess.run(
                ["which", "iptables"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "iptables"
        except:
            pass
        
        return None
    
    def _get_firewall_status(self) -> Dict[str, Any]:
        """Get firewall status"""
        
        try:
            if self.firewall_type == "ufw":
                result = subprocess.run(
                    ["sudo", "ufw", "status", "verbose"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                status = {
                    "enabled": "Status: active" in result.stdout,
                    "default_incoming": "deny" if "deny (incoming)" in result.stdout else "allow",
                    "default_outgoing": "allow" if "allow (outgoing)" in result.stdout else "deny",
                    "raw_output": result.stdout
                }
                
            elif self.firewall_type == "firewalld":
                result = subprocess.run(
                    ["sudo", "firewall-cmd", "--state"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                status = {
                    "enabled": result.returncode == 0 and "running" in result.stdout,
                    "raw_output": result.stdout
                }
                
            elif self.firewall_type == "iptables":
                result = subprocess.run(
                    ["sudo", "iptables", "-L", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                status = {
                    "enabled": result.returncode == 0,
                    "chains": len(re.findall(r'^Chain', result.stdout, re.MULTILINE)),
                    "rules": len(result.stdout.splitlines()) - status.get("chains", 0)
                }
            else:
                status = {"enabled": False, "message": "Unknown firewall type"}
            
            return status
            
        except Exception as e:
            logger.warning(f"Error getting firewall status: {e}")
            return {"enabled": False, "error": str(e)}
    
    def _get_firewall_rules(self) -> List[Dict[str, Any]]:
        """Get firewall rules"""
        
        rules = []
        
        try:
            if self.firewall_type == "ufw":
                result = subprocess.run(
                    ["sudo", "ufw", "status", "numbered"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Parse ufw rules
                for line in result.stdout.splitlines():
                    if line.strip() and not line.startswith("Status:") and not line.startswith("To"):
                        rules.append({"rule": line.strip()})
                
            elif self.firewall_type == "firewalld":
                result = subprocess.run(
                    ["sudo", "firewall-cmd", "--list-all"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Parse firewalld output
                for line in result.stdout.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        rules.append({
                            "type": key.strip(),
                            "value": value.strip()
                        })
                
            elif self.firewall_type == "iptables":
                result = subprocess.run(
                    ["sudo", "iptables", "-L", "-n", "-v"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Parse iptables rules (simplified)
                current_chain = None
                for line in result.stdout.splitlines():
                    if line.startswith("Chain"):
                        current_chain = line.split()[1]
                    elif line.strip() and not line.startswith("pkts") and current_chain:
                        parts = line.split()
                        if len(parts) >= 4:
                            rules.append({
                                "chain": current_chain,
                                "packets": parts[0],
                                "bytes": parts[1],
                                "target": parts[2],
                                "prot": parts[3] if len(parts) > 3 else "all"
                            })
        
        except Exception as e:
            logger.warning(f"Error getting firewall rules: {e}")
        
        return rules
    
    def _get_firewall_stats(self) -> Dict[str, Any]:
        """Get firewall statistics"""
        
        stats = {
            "total_rules": 0,
            "chains": {},
            "packet_counts": {},
            "byte_counts": {}
        }
        
        try:
            if self.firewall_type == "iptables":
                result = subprocess.run(
                    ["sudo", "iptables", "-L", "-n", "-v", "-x"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                current_chain = None
                total_pkts = 0
                total_bytes = 0
                
                for line in result.stdout.splitlines():
                    if line.startswith("Chain"):
                        current_chain = line.split()[1]
                        stats["chains"][current_chain] = {"rules": 0, "packets": 0, "bytes": 0}
                    elif line.strip() and not line.startswith("pkts") and current_chain:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pkts = int(parts[0])
                                bytes_val = int(parts[1])
                                stats["chains"][current_chain]["rules"] += 1
                                stats["chains"][current_chain]["packets"] += pkts
                                stats["chains"][current_chain]["bytes"] += bytes_val
                                total_pkts += pkts
                                total_bytes += bytes_val
                            except ValueError:
                                pass
                
                stats["total_rules"] = sum(c["rules"] for c in stats["chains"].values())
                stats["total_packets"] = total_pkts
                stats["total_bytes"] = total_bytes
        
        except Exception as e:
            logger.warning(f"Error getting firewall stats: {e}")
        
        return stats
    
    def _analyze_blocked_connections(self) -> Dict[str, Any]:
        """Analyze blocked connections from firewall logs"""
        
        log_files = self.config.get("log_files", ["/var/log/ufw.log", "/var/log/kern.log"])
        blocked_connections = []
        blocked_by_ip = defaultdict(int)
        alerts = []
        
        # Patterns for blocked connections
        patterns = {
            "ufw": re.compile(r'\[UFW BLOCK\].*SRC=(\S+).*DST=(\S+).*PROTO=(\w+).*DPT=(\d+)'),
            "iptables": re.compile(r'IN=\S+.*SRC=(\S+).*DST=(\S+).*PROTO=(\w+).*DPT=(\d+)'),
        }
        
        for log_file in log_files:
            if not os.path.exists(log_file) or not os.access(log_file, os.R_OK):
                continue
            
            try:
                with open(log_file, 'r') as f:
                    # Read last N lines efficiently
                    lines = f.readlines()[-1000:]  # Last 1000 lines
                    
                    for line in lines:
                        for fw_type, pattern in patterns.items():
                            match = pattern.search(line)
                            if match:
                                src_ip = match.group(1)
                                dst_ip = match.group(2)
                                proto = match.group(3)
                                port = match.group(4)
                                
                                blocked_connections.append({
                                    "source_ip": src_ip,
                                    "destination_ip": dst_ip,
                                    "protocol": proto,
                                    "port": port,
                                    "timestamp": datetime.utcnow().isoformat()  # Simplified
                                })
                                
                                blocked_by_ip[src_ip] += 1
            
            except Exception as e:
                logger.warning(f"Error reading log file {log_file}: {e}")
        
        # Generate alerts for high-frequency blockers
        alert_threshold = 50  # Alert if IP blocked 50+ times
        for ip, count in blocked_by_ip.items():
            if count >= alert_threshold:
                alerts.append({
                    "severity": "high" if count >= 100 else "medium",
                    "type": "repeated_blocks",
                    "source_ip": ip,
                    "count": count,
                    "message": f"IP {ip} blocked {count} times - possible scan/attack"
                })
        
        # Top blocked IPs
        top_limit = self.config.get("top_blocked_limit", 20)
        top_blocked = sorted(
            blocked_by_ip.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_limit]
        
        return {
            "blocked_connections": len(blocked_connections),
            "unique_blocked_ips": len(blocked_by_ip),
            "top_blocked_ips": [
                {"ip": ip, "count": count}
                for ip, count in top_blocked
            ],
            "recent_blocks": blocked_connections[-50:],  # Last 50 blocks
            "alerts": alerts
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if firewall monitoring is operational.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Detect firewall if not already done
            if not self.firewall_type:
                self.firewall_type = self._detect_firewall()
            
            if not self.firewall_type:
                return {
                    "healthy": False,
                    "message": "No supported firewall detected",
                    "details": {
                        "checked": ["ufw", "firewalld", "iptables"]
                    }
                }
            
            # Test firewall access
            status = self._get_firewall_status()
            
            if not status.get("enabled"):
                return {
                    "healthy": True,  # Health check passes but firewall is disabled
                    "message": f"{self.firewall_type} detected but not enabled",
                    "details": {
                        "firewall_type": self.firewall_type,
                        "enabled": False
                    }
                }
            
            return {
                "healthy": True,
                "message": f"Firewall monitoring operational ({self.firewall_type})",
                "details": {
                    "firewall_type": self.firewall_type,
                    "firewall_enabled": True,
                    "last_execution": self._last_execution.isoformat() if self._last_execution else None,
                    "execution_count": self._execution_count
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        # Validate firewall type
        if "firewall_type" in config:
            valid_types = ["auto", "iptables", "ufw", "firewalld"]
            if config["firewall_type"] not in valid_types:
                return False
        
        # Validate log files
        if "log_files" in config:
            if not isinstance(config["log_files"], list):
                return False
            if not all(isinstance(f, str) for f in config["log_files"]):
                return False
        
        # Validate numeric limits
        if "top_blocked_limit" in config:
            if not isinstance(config["top_blocked_limit"], int) or config["top_blocked_limit"] < 1:
                return False
        
        return True
    
    async def on_enable(self):
        """Called when plugin is enabled"""
        await super().on_enable()
        logger.info("firewall-monitor plugin enabled")
        
        # Detect firewall type
        self.firewall_type = self.config.get("firewall_type")
        if not self.firewall_type or self.firewall_type == "auto":
            self.firewall_type = self._detect_firewall()
        
        if self.firewall_type:
            logger.info(f"Monitoring {self.firewall_type} firewall")
    
    async def on_disable(self):
        """Called when plugin is disabled"""
        logger.info("firewall-monitor plugin disabled")
        self.blocked_ips.clear()
        await super().on_disable()
