"""
Backup Monitor Plugin

Monitors backup job status for multiple backup solutions.
Because "I thought my backups were working" is not a recovery strategy.
"""

import os
import subprocess
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class BackupMonitorPlugin(PluginBase):
    """Monitors backup jobs from Restic, Borg, Duplicati, rsync, and more"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="backup-monitor",
            name="Backup Monitor",
            version="1.0.0",
            description="Monitors backup job status, last successful run, and backup health for Restic, Borg, Duplicati, rsync, and custom scripts",
            author="Unity Team",
            category=PluginCategory.STORAGE,
            tags=["backup", "restic", "borg", "duplicati", "rsync", "disaster-recovery"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=[],  # Checks for tools at runtime
            config_schema={
                "type": "object",
                "properties": {
                    "backup_jobs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["restic", "borg", "duplicati", "rsync", "script"]},
                                "repo_path": {"type": "string"},
                                "check_command": {"type": "string"},
                                "max_age_hours": {"type": "integer", "default": 24}
                            },
                            "required": ["name", "type"]
                        },
                        "default": [],
                        "description": "List of backup jobs to monitor"
                    },
                    "warning_age_hours": {
                        "type": "integer",
                        "default": 26,
                        "description": "Hours since last backup to trigger warning"
                    },
                    "critical_age_hours": {
                        "type": "integer",
                        "default": 48,
                        "description": "Hours since last backup to trigger critical alert"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect backup status for all configured jobs"""
        
        config = self.config or {}
        backup_jobs = config.get("backup_jobs", [])
        warning_age = config.get("warning_age_hours", 26)
        critical_age = config.get("critical_age_hours", 48)
        
        if not backup_jobs:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "No backup jobs configured",
                "jobs": []
            }
        
        jobs_status = []
        
        for job in backup_jobs:
            try:
                status = self._check_backup_job(job, warning_age, critical_age)
                jobs_status.append(status)
            except Exception as e:
                jobs_status.append({
                    "name": job.get("name", "unknown"),
                    "type": job.get("type", "unknown"),
                    "status": "error",
                    "error": str(e)
                })
        
        # Calculate summary
        total = len(jobs_status)
        healthy = sum(1 for j in jobs_status if j.get("health") == "healthy")
        warning = sum(1 for j in jobs_status if j.get("health") == "warning")
        critical = sum(1 for j in jobs_status if j.get("health") == "critical")
        failed = sum(1 for j in jobs_status if j.get("status") == "error")
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_jobs": total,
                "healthy": healthy,
                "warnings": warning,
                "critical": critical,
                "failed": failed
            },
            "jobs": jobs_status
        }
    
    def _check_backup_job(
        self,
        job: Dict[str, Any],
        warning_age: int,
        critical_age: int
    ) -> Dict[str, Any]:
        """Check status of a single backup job"""
        
        job_type = job.get("type", "").lower()
        name = job.get("name", "unnamed")
        
        if job_type == "restic":
            return self._check_restic(job, warning_age, critical_age)
        elif job_type == "borg":
            return self._check_borg(job, warning_age, critical_age)
        elif job_type == "duplicati":
            return self._check_duplicati(job, warning_age, critical_age)
        elif job_type == "rsync":
            return self._check_rsync(job, warning_age, critical_age)
        elif job_type == "script":
            return self._check_custom_script(job, warning_age, critical_age)
        else:
            return {
                "name": name,
                "type": job_type,
                "status": "error",
                "error": f"Unknown backup type: {job_type}"
            }
    
    def _check_restic(
        self,
        job: Dict[str, Any],
        warning_age: int,
        critical_age: int
    ) -> Dict[str, Any]:
        """Check Restic backup repository"""
        
        name = job.get("name")
        repo_path = job.get("repo_path")
        
        if not repo_path:
            return {
                "name": name,
                "type": "restic",
                "status": "error",
                "error": "repo_path not configured"
            }
        
        try:
            # Get snapshots list
            result = subprocess.run(
                ["restic", "-r", repo_path, "snapshots", "--json", "--last"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "RESTIC_PASSWORD": os.environ.get("RESTIC_PASSWORD", "")}
            )
            
            if result.returncode != 0:
                return {
                    "name": name,
                    "type": "restic",
                    "status": "error",
                    "error": "Failed to query repository"
                }
            
            snapshots = json.loads(result.stdout)
            if not snapshots:
                return {
                    "name": name,
                    "type": "restic",
                    "status": "error",
                    "error": "No snapshots found"
                }
            
            last_snapshot = snapshots[0]
            snapshot_time = datetime.fromisoformat(last_snapshot["time"].replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - snapshot_time).total_seconds() / 3600
            
            health = self._determine_health(age_hours, warning_age, critical_age)
            
            return {
                "name": name,
                "type": "restic",
                "status": "success",
                "health": health,
                "last_backup": snapshot_time.isoformat(),
                "age_hours": round(age_hours, 1),
                "snapshot_id": last_snapshot.get("short_id"),
                "repository": repo_path
            }
            
        except FileNotFoundError:
            return {
                "name": name,
                "type": "restic",
                "status": "error",
                "error": "restic command not found"
            }
        except json.JSONDecodeError:
            return {
                "name": name,
                "type": "restic",
                "status": "error",
                "error": "Failed to parse restic output"
            }
        except Exception as e:
            return {
                "name": name,
                "type": "restic",
                "status": "error",
                "error": str(e)
            }
    
    def _check_borg(
        self,
        job: Dict[str, Any],
        warning_age: int,
        critical_age: int
    ) -> Dict[str, Any]:
        """Check Borg backup repository"""
        
        name = job.get("name")
        repo_path = job.get("repo_path")
        
        if not repo_path:
            return {
                "name": name,
                "type": "borg",
                "status": "error",
                "error": "repo_path not configured"
            }
        
        try:
            # Get last archive
            result = subprocess.run(
                ["borg", "list", "--json", "--last", "1", repo_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "name": name,
                    "type": "borg",
                    "status": "error",
                    "error": "Failed to query repository"
                }
            
            data = json.loads(result.stdout)
            archives = data.get("archives", [])
            
            if not archives:
                return {
                    "name": name,
                    "type": "borg",
                    "status": "error",
                    "error": "No archives found"
                }
            
            last_archive = archives[0]
            archive_time = datetime.fromisoformat(last_archive["time"])
            age_hours = (datetime.now(timezone.utc) - archive_time).total_seconds() / 3600
            
            health = self._determine_health(age_hours, warning_age, critical_age)
            
            return {
                "name": name,
                "type": "borg",
                "status": "success",
                "health": health,
                "last_backup": archive_time.isoformat(),
                "age_hours": round(age_hours, 1),
                "archive_name": last_archive.get("name"),
                "repository": repo_path
            }
            
        except FileNotFoundError:
            return {
                "name": name,
                "type": "borg",
                "status": "error",
                "error": "borg command not found"
            }
        except Exception as e:
            return {
                "name": name,
                "type": "borg",
                "status": "error",
                "error": str(e)
            }
    
    def _check_duplicati(
        self,
        job: Dict[str, Any],
        warning_age: int,
        critical_age: int
    ) -> Dict[str, Any]:
        """Check Duplicati backup via database"""
        
        name = job.get("name")
        
        # Duplicati typically requires API access or database queries
        # This is a simplified check based on common patterns
        
        return {
            "name": name,
            "type": "duplicati",
            "status": "not_implemented",
            "error": "Duplicati monitoring requires API configuration"
        }
    
    def _check_rsync(
        self,
        job: Dict[str, Any],
        warning_age: int,
        critical_age: int
    ) -> Dict[str, Any]:
        """Check rsync backup by checking destination directory timestamp"""
        
        name = job.get("name")
        repo_path = job.get("repo_path")
        
        if not repo_path:
            return {
                "name": name,
                "type": "rsync",
                "status": "error",
                "error": "repo_path not configured"
            }
        
        try:
            path = Path(repo_path)
            if not path.exists():
                return {
                    "name": name,
                    "type": "rsync",
                    "status": "error",
                    "error": f"Backup path does not exist: {repo_path}"
                }
            
            # Get modification time of the backup directory
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
            
            health = self._determine_health(age_hours, warning_age, critical_age)
            
            return {
                "name": name,
                "type": "rsync",
                "status": "success",
                "health": health,
                "last_backup": mtime.isoformat(),
                "age_hours": round(age_hours, 1),
                "destination": repo_path
            }
            
        except Exception as e:
            return {
                "name": name,
                "type": "rsync",
                "status": "error",
                "error": str(e)
            }
    
    def _check_custom_script(
        self,
        job: Dict[str, Any],
        warning_age: int,
        critical_age: int
    ) -> Dict[str, Any]:
        """Check custom backup script"""
        
        name = job.get("name")
        check_command = job.get("check_command")
        
        if not check_command:
            return {
                "name": name,
                "type": "script",
                "status": "error",
                "error": "check_command not configured"
            }
        
        try:
            result = subprocess.run(
                check_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Custom scripts should return JSON with at least 'last_backup' timestamp
            try:
                data = json.loads(result.stdout)
                last_backup_str = data.get("last_backup")
                
                if not last_backup_str:
                    return {
                        "name": name,
                        "type": "script",
                        "status": "error",
                        "error": "Script did not return last_backup timestamp"
                    }
                
                last_backup = datetime.fromisoformat(last_backup_str)
                age_hours = (datetime.now(timezone.utc) - last_backup).total_seconds() / 3600
                
                health = self._determine_health(age_hours, warning_age, critical_age)
                
                return {
                    "name": name,
                    "type": "script",
                    "status": "success",
                    "health": health,
                    "last_backup": last_backup.isoformat(),
                    "age_hours": round(age_hours, 1),
                    **{k: v for k, v in data.items() if k != "last_backup"}
                }
                
            except json.JSONDecodeError:
                # If not JSON, assume script failed
                return {
                    "name": name,
                    "type": "script",
                    "status": "error",
                    "error": "Script output is not valid JSON"
                }
                
        except Exception as e:
            return {
                "name": name,
                "type": "script",
                "status": "error",
                "error": str(e)
            }
    
    def _determine_health(
        self,
        age_hours: float,
        warning_age: int,
        critical_age: int
    ) -> str:
        """Determine backup health based on age"""
        
        if age_hours >= critical_age:
            return "critical"
        elif age_hours >= warning_age:
            return "warning"
        else:
            return "healthy"
    
    async def health_check(self) -> bool:
        """Check if plugin can function"""
        return True  # Basic functionality always available
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        
        if not config:
            return False
        
        backup_jobs = config.get("backup_jobs", [])
        if not isinstance(backup_jobs, list):
            return False
        
        for job in backup_jobs:
            if not isinstance(job, dict):
                return False
            if "name" not in job or "type" not in job:
                return False
        
        return True
