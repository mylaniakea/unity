"""
Log Monitor Plugin

Monitors log files - pattern matching, error rate tracking, alerting.
Essential for application debugging and system monitoring.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class LogMonitorPlugin(PluginBase):
    """Monitors log files for patterns and errors"""
    
    def __init__(self):
        super().__init__()
        self._file_positions: Dict[str, int] = {}  # Track file read positions
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="log-monitor",
            name="Log Monitor",
            version="1.0.0",
            description="Monitors log files for patterns, errors, and anomalies with regex support",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["logs", "monitoring", "errors", "regex", "parsing"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],  # Built-in Python
            config_schema={
                "type": "object",
                "properties": {
                    "log_files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "path": {"type": "string"},
                                "patterns": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "regex": {"type": "string"},
                                            "severity": {"type": "string", "enum": ["debug", "info", "warning", "error", "critical"]},
                                            "alert": {"type": "boolean", "default": False}
                                        },
                                        "required": ["name", "regex"]
                                    }
                                },
                                "encoding": {"type": "string", "default": "utf-8"}
                            },
                            "required": ["name", "path"]
                        },
                        "default": [],
                        "description": "List of log files to monitor"
                    },
                    "max_lines_per_check": {
                        "type": "integer",
                        "default": 1000,
                        "description": "Maximum lines to read per check"
                    },
                    "tail_only": {
                        "type": "boolean",
                        "default": True,
                        "description": "Only read new lines (tail mode)"
                    },
                    "default_patterns": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include default error/warning patterns"
                    }
                },
                "required": []
            }
        )
    
    def _get_default_patterns(self) -> List[Dict[str, Any]]:
        """Get default log patterns"""
        return [
            {"name": "Error", "regex": r"\b(error|err|exception|fail)\b", "severity": "error"},
            {"name": "Warning", "regex": r"\b(warning|warn)\b", "severity": "warning"},
            {"name": "Critical", "regex": r"\b(critical|fatal|panic)\b", "severity": "critical"},
            {"name": "Stack Trace", "regex": r"(Traceback|at .+\(.+:\d+\))", "severity": "error"},
            {"name": "Connection Failed", "regex": r"(connection (refused|failed|timeout)|unable to connect)", "severity": "error"},
            {"name": "Out of Memory", "regex": r"(out of memory|oom|memory exhausted)", "severity": "critical"},
            {"name": "Permission Denied", "regex": r"(permission denied|access denied)", "severity": "error"}
        ]
    
    def _read_log_file(self, log_config: Dict[str, Any]) -> Dict[str, Any]:
        """Read and analyze a log file"""
        
        name = log_config.get("name", "Unknown")
        path = log_config.get("path")
        encoding = log_config.get("encoding", "utf-8")
        patterns = log_config.get("patterns", [])
        
        # Add default patterns if enabled
        if self.config.get("default_patterns", True):
            patterns = self._get_default_patterns() + patterns
        
        result = {
            "name": name,
            "path": path,
            "exists": os.path.exists(path)
        }
        
        if not result["exists"]:
            result["error"] = "File does not exist"
            return result
        
        try:
            # Get file stats
            stat_info = os.stat(path)
            result["file_size_bytes"] = stat_info.st_size
            result["last_modified"] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            
            # Determine read position
            tail_only = self.config.get("tail_only", True)
            max_lines = self.config.get("max_lines_per_check", 1000)
            
            current_position = 0
            if tail_only and path in self._file_positions:
                # Resume from last position
                current_position = self._file_positions.get(path, 0)
                # If file was truncated/rotated, start from beginning
                if current_position > stat_info.st_size:
                    current_position = 0
            
            # Read file
            with open(path, 'r', encoding=encoding, errors='replace') as f:
                f.seek(current_position)
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip('\n'))
                
                # Update position
                new_position = f.tell()
                self._file_positions[path] = new_position
            
            result["lines_read"] = len(lines)
            result["new_position"] = new_position
            
            # Pattern matching
            matches = []
            match_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            alerts = []
            
            for line_num, line in enumerate(lines, start=1):
                for pattern in patterns:
                    pattern_name = pattern.get("name", "Unknown")
                    regex = pattern.get("regex")
                    severity = pattern.get("severity", "info")
                    alert = pattern.get("alert", False)
                    
                    try:
                        if re.search(regex, line, re.IGNORECASE):
                            match_counts[pattern_name] += 1
                            severity_counts[severity] += 1
                            
                            match_info = {
                                "line_number": line_num,
                                "pattern": pattern_name,
                                "severity": severity,
                                "line": line[:200]  # Truncate long lines
                            }
                            
                            matches.append(match_info)
                            
                            if alert:
                                alerts.append(match_info)
                    except re.error as e:
                        result[f"regex_error_{pattern_name}"] = str(e)
            
            result["matches"] = matches[:100]  # Limit to 100 matches
            result["match_summary"] = {
                "total_matches": len(matches),
                "by_pattern": dict(match_counts),
                "by_severity": dict(severity_counts)
            }
            
            if alerts:
                result["alerts"] = alerts
                result["alert_count"] = len(alerts)
            
        except PermissionError:
            result["error"] = "Permission denied"
        except UnicodeDecodeError as e:
            result["error"] = f"Encoding error: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect log monitoring data"""
        
        log_files = self.config.get("log_files", [])
        
        if not log_files:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "No log files configured",
                "message": "Please configure log_files in plugin config"
            }
        
        results = []
        total_matches = 0
        total_alerts = 0
        severity_totals = defaultdict(int)
        
        for log_config in log_files:
            result = self._read_log_file(log_config)
            results.append(result)
            
            if "match_summary" in result:
                total_matches += result["match_summary"]["total_matches"]
                for severity, count in result["match_summary"]["by_severity"].items():
                    severity_totals[severity] += count
            
            if "alert_count" in result:
                total_alerts += result["alert_count"]
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_log_files": len(log_files),
                "total_matches": total_matches,
                "total_alerts": total_alerts,
                "by_severity": dict(severity_totals)
            },
            "log_files": results
        }
        
        return data
    
    async def health_check(self) -> Dict[str, Any]:
        """Check log monitor health"""
        
        log_files = self.config.get("log_files", [])
        
        if not log_files:
            return {
                "healthy": False,
                "message": "No log files configured",
                "details": {
                    "suggestion": "Configure log_files in plugin config"
                }
            }
        
        # Check if configured files exist
        accessible_count = 0
        for log_config in log_files:
            path = log_config.get("path")
            if path and os.path.exists(path):
                accessible_count += 1
        
        if accessible_count == 0:
            return {
                "healthy": False,
                "message": "None of the configured log files are accessible",
                "details": {
                    "configured_files": len(log_files)
                }
            }
        
        return {
            "healthy": True,
            "message": "Log monitor is configured",
            "details": {
                "configured_files": len(log_files),
                "accessible_files": accessible_count
            }
        }
