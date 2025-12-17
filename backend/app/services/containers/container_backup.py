import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session
import app.models as models

logger = logging.getLogger(__name__)


class ContainerBackup:
    """Service for backing up and restoring container configurations"""
    
    def __init__(self, docker_client, db: Session, backup_dir: str = "/app/backups"):
        self.docker_client = docker_client
        self.db = db
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    async def backup_container(
        self,
        container_id: str,
        backup_type: str = "config"
    ) -> Optional[models.BackupRecord]:
        """
        Create a backup of a container's configuration.
        
        Args:
            container_id: Docker container ID
            backup_type: "config" for configuration only, "full" for config + volumes
        
        Returns:
            BackupRecord instance or None on failure
        """
        try:
            logger.info(f"Creating {backup_type} backup for container {container_id}")
            
            # Get container from Docker
            docker_container = self.docker_client.containers.get(container_id)
            
            # Get container record from database
            db_container = self.db.query(models.Container).filter(
                models.Container.container_id == container_id
            ).first()
            
            if not db_container:
                logger.error(f"Container {container_id} not found in database")
                return None
            
            # Create backup directory for this container
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            container_backup_dir = self.backup_dir / f"{db_container.name}_{timestamp}"
            container_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract container configuration
            config = docker_container.attrs
            
            # Build backup metadata
            metadata = {
                "container_id": container_id,
                "container_name": docker_container.name,
                "image": config.get("Config", {}).get("Image"),
                "created": config.get("Created"),
                "config": {
                    "Env": config.get("Config", {}).get("Env", []),
                    "Cmd": config.get("Config", {}).get("Cmd", []),
                    "Entrypoint": config.get("Config", {}).get("Entrypoint", []),
                    "WorkingDir": config.get("Config", {}).get("WorkingDir", ""),
                    "User": config.get("Config", {}).get("User", ""),
                    "Labels": config.get("Config", {}).get("Labels", {}),
                    "ExposedPorts": config.get("Config", {}).get("ExposedPorts", {}),
                },
                "host_config": {
                    "Binds": config.get("HostConfig", {}).get("Binds", []),
                    "PortBindings": config.get("HostConfig", {}).get("PortBindings", {}),
                    "RestartPolicy": config.get("HostConfig", {}).get("RestartPolicy", {}),
                    "NetworkMode": config.get("HostConfig", {}).get("NetworkMode", ""),
                    "Privileged": config.get("HostConfig", {}).get("Privileged", False),
                    "CapAdd": config.get("HostConfig", {}).get("CapAdd", []),
                    "CapDrop": config.get("HostConfig", {}).get("CapDrop", []),
                },
                "network_settings": {
                    "Networks": config.get("NetworkSettings", {}).get("Networks", {}),
                },
                "mounts": config.get("Mounts", []),
                "backup_type": backup_type,
                "timestamp": timestamp
            }
            
            # Save configuration to file
            config_file = container_backup_dir / "container_config.json"
            with open(config_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Calculate backup size
            backup_size = sum(
                f.stat().st_size 
                for f in container_backup_dir.rglob("*") 
                if f.is_file()
            )
            
            # Create backup record in database
            backup_record = models.BackupRecord(
                container_id=db_container.id,
                backup_type=backup_type,
                backup_path=str(container_backup_dir),
                backup_metadata=metadata,
                size_bytes=backup_size,
                status="complete"
            )
            
            self.db.add(backup_record)
            self.db.commit()
            self.db.refresh(backup_record)
            
            logger.info(
                f"Backup created successfully for {db_container.name} "
                f"(ID: {backup_record.id}, Size: {backup_size} bytes)"
            )
            
            return backup_record
            
        except Exception as e:
            logger.error(f"Error creating backup for container {container_id}: {e}")
            
            # Create failed backup record
            try:
                backup_record = models.BackupRecord(
                    container_id=db_container.id if db_container else None,
                    backup_type=backup_type,
                    backup_path="",
                    backup_metadata={},
                    status="failed",
                    error_message=str(e)
                )
                self.db.add(backup_record)
                self.db.commit()
            except Exception as db_error:
                logger.error(f"Failed to save backup error to database: {db_error}")
            
            return None
    
    async def restore_container(
        self,
        backup_record: models.BackupRecord,
        force: bool = False
    ) -> bool:
        """
        Restore a container from backup.
        
        Args:
            backup_record: BackupRecord instance
            force: If True, stop and remove existing container before restore
        
        Returns:
            True if restore successful, False otherwise
        """
        try:
            logger.info(f"Restoring container from backup {backup_record.id}")
            
            metadata = backup_record.backup_metadata
            container_name = metadata.get("container_name")
            
            if not container_name:
                logger.error("Container name not found in backup metadata")
                return False
            
            # Check if container with same name exists
            try:
                existing = self.docker_client.containers.get(container_name)
                if force:
                    logger.info(f"Stopping and removing existing container {container_name}")
                    existing.stop(timeout=10)
                    existing.remove()
                else:
                    logger.error(
                        f"Container {container_name} already exists. "
                        "Use force=True to replace it."
                    )
                    return False
            except Exception:
                # Container doesn't exist, proceed with restore
                pass
            
            # Extract configuration from metadata
            config = metadata.get("config", {})
            host_config = metadata.get("host_config", {})
            network_settings = metadata.get("network_settings", {})
            
            # Recreate container
            container = self.docker_client.containers.create(
                image=metadata.get("image"),
                name=container_name,
                command=config.get("Cmd"),
                entrypoint=config.get("Entrypoint"),
                environment=config.get("Env", []),
                ports=host_config.get("PortBindings", {}),
                volumes=host_config.get("Binds", []),
                network_mode=host_config.get("NetworkMode", "bridge"),
                restart_policy=host_config.get("RestartPolicy", {}),
                labels=config.get("Labels", {}),
                working_dir=config.get("WorkingDir"),
                user=config.get("User"),
                privileged=host_config.get("Privileged", False),
                cap_add=host_config.get("CapAdd"),
                cap_drop=host_config.get("CapDrop"),
                detach=True
            )
            
            # Start the container
            container.start()
            
            logger.info(f"Container {container_name} restored successfully from backup")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring container from backup: {e}")
            return False
    
    def get_latest_backup(
        self,
        container_id: int,
        backup_type: Optional[str] = None
    ) -> Optional[models.BackupRecord]:
        """
        Get the most recent successful backup for a container.
        
        Args:
            container_id: Database container ID
            backup_type: Optional filter by backup type
        
        Returns:
            BackupRecord or None
        """
        query = self.db.query(models.BackupRecord).filter(
            models.BackupRecord.container_id == container_id,
            models.BackupRecord.status == "complete"
        )
        
        if backup_type:
            query = query.filter(models.BackupRecord.backup_type == backup_type)
        
        return query.order_by(
            models.BackupRecord.created_at.desc()
        ).first()
    
    def cleanup_old_backups(
        self,
        container_id: int,
        keep_count: int = 5
    ) -> int:
        """
        Remove old backup records and files, keeping only the most recent ones.
        
        Args:
            container_id: Database container ID
            keep_count: Number of backups to keep
        
        Returns:
            Number of backups removed
        """
        try:
            backups = self.db.query(models.BackupRecord).filter(
                models.BackupRecord.container_id == container_id
            ).order_by(
                models.BackupRecord.created_at.desc()
            ).all()
            
            if len(backups) <= keep_count:
                return 0
            
            backups_to_remove = backups[keep_count:]
            removed_count = 0
            
            for backup in backups_to_remove:
                # Remove backup directory
                backup_path = Path(backup.backup_path)
                if backup_path.exists():
                    import shutil
                    shutil.rmtree(backup_path, ignore_errors=True)
                
                # Remove database record
                self.db.delete(backup)
                removed_count += 1
            
            self.db.commit()
            logger.info(f"Cleaned up {removed_count} old backups for container {container_id}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
            return 0
