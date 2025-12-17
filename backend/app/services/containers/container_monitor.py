from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any
import logging
import app.models as models
from app.services.containers.container_runtime_manager import DockerManager

logger = logging.getLogger(__name__)


class ContainerMonitor:
    """Service for discovering and monitoring containers across Docker hosts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.docker_manager = DockerManager(db)
    
    def discover_all_containers(self) -> Dict[str, Any]:
        """Discover containers across all enabled Docker hosts"""
        logger.info("Starting container discovery...")
        
        # Get all enabled hosts
        hosts = self.db.query(models.DockerHost).filter(
            models.DockerHost.enabled == True
        ).all()
        
        total_discovered = 0
        total_new = 0
        total_updated = 0
        hosts_scanned = 0
        errors = []
        
        for host in hosts:
            try:
                logger.info(f"Discovering containers on host: {host.name}")
                result = self.discover_host_containers(host.id)
                total_discovered += result["discovered"]
                total_new += result["new"]
                total_updated += result["updated"]
                hosts_scanned += 1
            except Exception as e:
                error_msg = f"Failed to discover containers on host '{host.name}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Container discovery complete. Scanned {hosts_scanned} hosts, "
                   f"discovered {total_discovered} containers ({total_new} new, {total_updated} updated)")
        
        return {
            "hosts_scanned": hosts_scanned,
            "total_discovered": total_discovered,
            "new_containers": total_new,
            "updated_containers": total_updated,
            "errors": errors
        }
    
    def discover_host_containers(self, host_id: int) -> Dict[str, Any]:
        """Discover containers on a specific Docker host"""
        discovered_count = 0
        new_count = 0
        updated_count = 0
        
        # Get containers from Docker API
        containers_data = self.docker_manager.list_containers(host_id, all_containers=True)
        discovered_count = len(containers_data)
        
        # Track container IDs we've seen
        seen_container_ids = set()
        
        for container_data in containers_data:
            container_id = container_data["id"]
            seen_container_ids.add(container_id)
            
            # Get detailed container information
            try:
                details = self.docker_manager.get_container_details(host_id, container_id)
                
                # Check if container already exists in database
                existing = self.db.query(models.Container).filter(
                    models.Container.container_id == container_id,
                    models.Container.host_id == host_id
                ).first()
                
                if existing:
                    # Update existing container
                    self._update_container(existing, details)
                    updated_count += 1
                else:
                    # Create new container record
                    self._create_container(host_id, details)
                    new_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process container {container_id}: {e}")
        
        # Mark containers that no longer exist as stopped
        self._mark_missing_containers(host_id, seen_container_ids)
        
        return {
            "discovered": discovered_count,
            "new": new_count,
            "updated": updated_count
        }
    
    def _create_container(self, host_id: int, details: Dict[str, Any]):
        """Create a new container record"""
        container = models.Container(
            container_id=details["id"],
            host_id=host_id,
            name=details["name"],
            image=details["image"],
            image_id=details["image_id"],
            status=details["status"],
            current_tag=details["tag"],
            labels=details["labels"],
            environment=details["environment"],
            ports=details["ports"],
            volumes=details["volumes"],
            networks=details["networks"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )
        
        self.db.add(container)
        self.db.commit()
        logger.info(f"Created new container record: {container.name}")
    
    def _update_container(self, container: models.Container, details: Dict[str, Any]):
        """Update an existing container record"""
        container.name = details["name"]
        container.image = details["image"]
        container.image_id = details["image_id"]
        container.status = details["status"]
        container.current_tag = details["tag"]
        container.labels = details["labels"]
        container.environment = details["environment"]
        container.ports = details["ports"]
        container.volumes = details["volumes"]
        container.networks = details["networks"]
        container.last_seen = datetime.utcnow()
        
        self.db.commit()
    
    def _mark_missing_containers(self, host_id: int, seen_ids: set):
        """Mark containers that were not discovered as no longer running"""
        # Get all containers for this host that we didn't see
        missing = self.db.query(models.Container).filter(
            models.Container.host_id == host_id,
            models.Container.container_id.notin_(seen_ids)
        ).all()
        
        for container in missing:
            # Only update if it's been more than 5 minutes since last seen
            if container.last_seen:
                minutes_ago = (datetime.utcnow() - container.last_seen).total_seconds() / 60
                if minutes_ago > 5:
                    logger.info(f"Container {container.name} no longer found on host, marking as stopped")
                    container.status = "removed"
                    self.db.commit()
