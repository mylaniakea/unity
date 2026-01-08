"""
Authentication Monitor Plugin

Monitors authentication attempts, failures, and suspicious patterns
across various authentication sources (SSH, PAM, web services).

Author: Unity Team
Created: 2025-12-17
"""

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging
import re
import os
from collections import defaultdict

logger = logging.getLogger(__name__)


class AuthMonitorPlugin(PluginBase):
    """Authentication monitoring and security analysis plugin"""
    
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        self.auth_cache = defaultdict(list)
        self.failed_attempts = defaultdict(int)
        self.last_check_time = None
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            id="auth-monitor",
            name="Authentication Monitor",
            version="1.0.0",
            description="Monitors authentication attempts, failures, and suspicious patterns",
            author="Unity Team",
            category=PluginCategory.SECURITY,
            tags=["security", "authentication", "ssh", "pam", "login"],
            requires_sudo=True,
            supported_os=["linux", "darwin"],
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "log_files": {
                        "type": "array",
                        "default": ["/var/log/auth.log", "/var/log/secure"],
                        "description": "Authentication log files to monitor"
                    },
                    "failed_threshold": {
                        "type": "integer",
                        "default": 5,
                        "description": "Failed attempts threshold for alerting"
                    },
                    "time_window_minutes": {
                        "type": "integer",
                        "default": 10,
                        "description": "Time window for counting failed attempts"
                    },
                    "monitor_ssh": {
                        "type": "boolean",
                        "default": True,
                        "description": "Monitor SSH authentication"
                    },
                    "monitor_sudo": {
                        "type": "boolean",
                        "default": True,
                        "description": "Monitor sudo authentication"
                    },
                    "track_successful": {
                        "type": "boolean",
                        "default": True,
                        "description": "Track successful logins"
                    }
                },
                "required": []
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """
        Collect authentication data and analyze patterns.
        
        Returns:
            Dictionary containing auth metrics and alerts
            
        Raises:
            Exception: If data collection fails
        """
        try:
            logger.info("Collecting authentication data")
            
            # Get configuration
            log_files = self.config.get("log_files", ["/var/log/auth.log", "/var/log/secure"])
            failed_threshold = self.config.get("failed_threshold", 5)
            time_window = timedelta(minutes=self.config.get("time_window_minutes", 10))
            monitor_ssh = self.config.get("monitor_ssh", True)
            monitor_sudo = self.config.get("monitor_sudo", True)
            track_successful = self.config.get("track_successful", True)
            
            # Find available log files
            available_logs = [f for f in log_files if os.path.exists(f) and os.access(f, os.R_OK)]
            
            if not available_logs:
                logger.warning(f"No readable auth log files found in {log_files}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "no_logs",
                    "message": "No readable authentication logs available"
                }
            
            # Parse logs
            auth_events = []
            for log_file in available_logs:
                events = self._parse_auth_log(log_file, time_window)
                auth_events.extend(events)
            
            # Analyze events
            analysis = self._analyze_auth_events(
                auth_events,
                failed_threshold,
                time_window,
                monitor_ssh,
                monitor_sudo,
                track_successful
            )
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active",
                "log_files": available_logs,
                "time_window_minutes": self.config.get("time_window_minutes", 10),
                "statistics": analysis["statistics"],
                "failed_attempts": analysis["failed_attempts"],
                "successful_logins": analysis["successful_logins"] if track_successful else [],
                "suspicious_activity": analysis["suspicious_activity"],
                "alerts": analysis["alerts"]
            }
            
            return data
            
        except PermissionError as e:
            logger.error(f"Permission denied reading auth logs: {e}")
            self._last_error = str(e)
            raise Exception("This plugin requires sudo/root access to read authentication logs")
        except Exception as e:
            logger.error(f"Data collection failed: {str(e)}", exc_info=True)
            self._last_error = str(e)
            raise
    
    def _parse_auth_log(self, log_file: str, time_window: timedelta) -> List[Dict[str, Any]]:
        """Parse authentication log file"""
        events = []
        cutoff_time = datetime.utcnow() - time_window
        
        # Patterns for different auth events
        patterns = {
            "ssh_failed": re.compile(r'Failed password for (?:invalid user )?(\S+) from (\S+) port (\d+)'),
            "ssh_success": re.compile(r'Accepted (?:password|publickey) for (\S+) from (\S+) port (\d+)'),
            "sudo_failed": re.compile(r'sudo.*authentication failure.*user=(\S+)'),
            "sudo_success": re.compile(r'sudo.*(\S+) : TTY=.*COMMAND='),
            "pam_failed": re.compile(r'pam_unix.*authentication failure.*user=(\S+)'),
        }
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    # Try to parse timestamp (simplified - works for most syslog formats)
                    for event_type, pattern in patterns.items():
                        match = pattern.search(line)
                        if match:
                            events.append({
                                "type": event_type,
                                "timestamp": datetime.utcnow(),  # Simplified
                                "user": match.group(1) if match.groups() else "unknown",
                                "source": match.group(2) if len(match.groups()) > 1 else "local",
                                "raw": line.strip()
                            })
        except Exception as e:
            logger.warning(f"Error parsing {log_file}: {e}")
        
        return events
    
    def _analyze_auth_events(
        self,
        events: List[Dict[str, Any]],
        failed_threshold: int,
        time_window: timedelta,
        monitor_ssh: bool,
        monitor_sudo: bool,
        track_successful: bool
    ) -> Dict[str, Any]:
        """Analyze authentication events for patterns and anomalies"""
        
        # Count events by type
        failed_ssh = [e for e in events if "failed" in e["type"] and "ssh" in e["type"]]
        success_ssh = [e for e in events if "success" in e["type"] and "ssh" in e["type"]]
        failed_sudo = [e for e in events if "failed" in e["type"] and "sudo" in e["type"]]
        success_sudo = [e for e in events if "success" in e["type"] and "sudo" in e["type"]]
        
        # Count by user
        failed_by_user = defaultdict(int)
        for event in events:
            if "failed" in event["type"]:
                failed_by_user[event["user"]] += 1
        
        # Count by source
        failed_by_source = defaultdict(int)
        for event in events:
            if "failed" in event["type"]:
                failed_by_source[event["source"]] += 1
        
        # Identify suspicious activity
        suspicious = []
        alerts = []
        
        # Alert on multiple failed attempts
        for user, count in failed_by_user.items():
            if count >= failed_threshold:
                alert = {
                    "severity": "high" if count >= failed_threshold * 2 else "medium",
                    "type": "multiple_failed_attempts",
                    "user": user,
                    "count": count,
                    "message": f"User '{user}' has {count} failed authentication attempts"
                }
                alerts.append(alert)
                suspicious.append(alert)
        
        # Alert on suspicious sources
        for source, count in failed_by_source.items():
            if count >= failed_threshold and source not in ["local", "localhost", "127.0.0.1"]:
                alert = {
                    "severity": "high",
                    "type": "suspicious_source",
                    "source": source,
                    "count": count,
                    "message": f"Multiple failed attempts from source '{source}' ({count} attempts)"
                }
                alerts.append(alert)
                suspicious.append(alert)
        
        # Compile statistics
        statistics = {
            "total_events": len(events),
            "ssh_failed": len(failed_ssh),
            "ssh_successful": len(success_ssh),
            "sudo_failed": len(failed_sudo),
            "sudo_successful": len(success_sudo),
            "unique_users": len(set(e["user"] for e in events)),
            "unique_sources": len(set(e["source"] for e in events)),
            "failed_by_user": dict(failed_by_user),
            "failed_by_source": dict(failed_by_source)
        }
        
        # Top failed attempts
        top_failed_users = sorted(
            failed_by_user.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        top_failed_sources = sorted(
            failed_by_source.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "statistics": statistics,
            "failed_attempts": {
                "by_user": [{"user": u, "count": c} for u, c in top_failed_users],
                "by_source": [{"source": s, "count": c} for s, c in top_failed_sources]
            },
            "successful_logins": [
                {
                    "user": e["user"],
                    "source": e["source"],
                    "timestamp": e["timestamp"].isoformat()
                }
                for e in (success_ssh + success_sudo)[:20]  # Limit to recent 20
            ] if track_successful else [],
            "suspicious_activity": suspicious,
            "alerts": alerts
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if plugin can access auth logs.
        
        Returns:
            Dictionary with health status
        """
        try:
            log_files = self.config.get("log_files", ["/var/log/auth.log", "/var/log/secure"])
            available_logs = [f for f in log_files if os.path.exists(f)]
            readable_logs = [f for f in available_logs if os.access(f, os.R_OK)]
            
            if not available_logs:
                return {
                    "healthy": False,
                    "message": "No authentication log files found",
                    "details": {
                        "searched_paths": log_files
                    }
                }
            
            if not readable_logs:
                return {
                    "healthy": False,
                    "message": "Authentication logs exist but are not readable (requires sudo)",
                    "details": {
                        "found_logs": available_logs,
                        "readable": False
                    }
                }
            
            return {
                "healthy": True,
                "message": "Authentication monitoring is operational",
                "details": {
                    "monitoring_logs": readable_logs,
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
        # Check log files
        if "log_files" in config:
            if not isinstance(config["log_files"], list):
                return False
            if not all(isinstance(f, str) for f in config["log_files"]):
                return False
        
        # Check numeric thresholds
        if "failed_threshold" in config:
            if not isinstance(config["failed_threshold"], int) or config["failed_threshold"] < 1:
                return False
        
        if "time_window_minutes" in config:
            if not isinstance(config["time_window_minutes"], int) or config["time_window_minutes"] < 1:
                return False
        
        return True
    
    async def on_enable(self):
        """Called when plugin is enabled"""
        await super().on_enable()
        logger.info("auth-monitor plugin enabled")
        self.last_check_time = datetime.utcnow()
    
    async def on_disable(self):
        """Called when plugin is disabled"""
        logger.info("auth-monitor plugin disabled")
        self.auth_cache.clear()
        self.failed_attempts.clear()
        await super().on_disable()
