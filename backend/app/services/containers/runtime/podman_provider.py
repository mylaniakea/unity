"""Podman runtime provider implementation."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

try:
    from podman import PodmanClient
    from podman.errors import PodmanError
    PODMAN_AVAILABLE = True
except ImportError:
    PODMAN_AVAILABLE = False
    PodmanClient = None
    PodmanError = Exception

from .provider import ContainerRuntimeProvider, RuntimeProviderFactory
import app.models as models

logger = logging.getLogger(__name__)


class PodmanProvider(ContainerRuntimeProvider):
    """Podman runtime provider using podman-py SDK."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        
        if not PODMAN_AVAILABLE:
            logger.warning("podman-py is not installed. Podman support is disabled.")
        
        self._clients: Dict[int, PodmanClient] = {}
    
    async def connect(self, host_id: int) -> PodmanClient:
        """Establish connection to Podman host."""
        if not PODMAN_AVAILABLE:
            raise RuntimeError("podman-py is not installed. Install with: pip install podman")
        
        # Return cached client if available
        if host_id in self._clients:
            try:
                # Test if client is still alive
                self._clients[host_id].ping()
                return self._clients[host_id]
            except Exception:
                # Client is dead, remove from cache
                del self._clients[host_id]
        
        # Get host configuration from database
        host = self.db.query(models.ContainerHost).filter(
            models.ContainerHost.id == host_id
        ).first()
        
        if not host:
            raise ValueError(f"Container host with ID {host_id} not found")
        
        if not host.enabled:
            raise ValueError(f"Container host '{host.name}' is disabled")
        
        if host.runtime_type != "podman":
            raise ValueError(f"Host {host_id} is not a Podman host (type: {host.runtime_type})")
        
        # Create new client
        try:
            # Podman uses socket-like connection, similar to Docker
            if host.connection_type == "socket":
                client = PodmanClient(base_url=host.connection_string)
            elif host.connection_type == "tcp":
                client = PodmanClient(base_url=host.connection_string)
            elif host.connection_type == "ssh":
                # SSH format for Podman: ssh://user@host:port
                base_url = f"ssh://{host.ssh_username}@{host.ssh_host}:{host.ssh_port}"
                client = PodmanClient(base_url=base_url)
            else:
                raise ValueError(f"Unsupported connection type: {host.connection_type}")
            
            # Test connection
            client.ping()
            
            # Cache the client
            self._clients[host_id] = client
            
            # Update host status
            host.last_seen = datetime.utcnow()
            host.status = "online"
            host.status_message = None
            self.db.commit()
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Podman host '{host.name}': {e}")
            host.status = "error"
            host.status_message = str(e)
            self.db.commit()
            raise
    
    async def get_host_info(self, host_id: int) -> Dict[str, Any]:
        """Get Podman host information."""
        try:
            client = await self.connect(host_id)
            info = client.info()
            version = client.version()
            
            return {
                "runtime_type": "podman",
                "podman_version": version.get("Version"),
                "api_version": version.get("ApiVersion"),
                "os": info.get("host", {}).get("os"),
                "architecture": info.get("host", {}).get("arch"),
                "cpus": info.get("host", {}).get("cpus"),
                "memory": info.get("host", {}).get("memTotal"),
                "containers": info.get("store", {}).get("containerStore", {}).get("number", 0),
                "images": info.get("store", {}).get("imageStore", {}).get("number", 0),
                "kernel_version": info.get("host", {}).get("kernel"),
                "conmon_version": info.get("host", {}).get("conmon", {}).get("version"),
            }
        except Exception as e:
            logger.error(f"Failed to get host info for host {host_id}: {e}")
            raise
    
    async def list_containers(self, host_id: int, all_containers: bool = True) -> List[Dict[str, Any]]:
        """List all containers on a Podman host."""
        try:
            client = await self.connect(host_id)
            containers = client.containers.list(all=all_containers)
            
            result = []
            for container in containers:
                result.append({
                    "id": container.id,
                    "short_id": container.short_id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.id,
                    "status": container.status,
                    "state": container.attrs.get("State"),
                    "created": container.attrs.get("Created"),
                    "labels": container.labels,
                    "ports": container.ports,
                })
            
            return result
        except Exception as e:
            logger.error(f"Failed to list containers for host {host_id}: {e}")
            raise
    
    async def get_container_details(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific container."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            
            # Parse image information
            image_full = container.image.tags[0] if container.image.tags else container.image.id
            image_parts = image_full.split(":")
            image_name = image_parts[0]
            image_tag = image_parts[1] if len(image_parts) > 1 else "latest"
            
            return {
                "id": container.id,
                "short_id": container.short_id,
                "name": container.name,
                "image": image_name,
                "image_id": container.image.id,
                "tag": image_tag,
                "status": container.status,
                "state": container.attrs.get("State", {}),
                "created": container.attrs.get("Created"),
                "started": container.attrs.get("State", {}).get("StartedAt"),
                "labels": container.labels,
                "environment": container.attrs.get("Config", {}).get("Env", []),
                "ports": container.ports,
                "volumes": container.attrs.get("Mounts", []),
                "networks": list(container.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
            }
        except Exception as e:
            logger.error(f"Failed to get container details: {e}")
            raise
    
    async def pull_image(self, host_id: int, image: str, tag: str = "latest") -> bool:
        """Pull a container image."""
        try:
            client = await self.connect(host_id)
            image_name = f"{image}:{tag}"
            client.images.pull(image, tag=tag)
            logger.info(f"Successfully pulled image {image_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull image {image}:{tag}: {e}")
            raise RuntimeError(f"Failed to pull image: {e}")
    
    async def create_container(
        self,
        host_id: int,
        image: str,
        name: str,
        config: Dict[str, Any]
    ) -> str:
        """Create a new Podman container."""
        try:
            client = await self.connect(host_id)
            
            # Podman API is Docker-compatible
            container_config = config.get("container_config", {})
            host_config = config.get("host_config", {})
            
            container = client.containers.create(
                image=image,
                name=name,
                **container_config,
                **host_config
            )
            
            logger.info(f"Created container {name} with ID {container.id}")
            return container.id
        except Exception as e:
            logger.error(f"Failed to create container {name}: {e}")
            raise RuntimeError(f"Failed to create container: {e}")
    
    async def start_container(self, host_id: int, container_id: str) -> bool:
        """Start a Podman container."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            container.start()
            logger.info(f"Started container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            raise
    
    async def stop_container(self, host_id: int, container_id: str, timeout: int = 10) -> bool:
        """Stop a Podman container."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            container.stop(timeout=timeout)
            logger.info(f"Stopped container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            raise
    
    async def remove_container(self, host_id: int, container_id: str, force: bool = False) -> bool:
        """Remove a Podman container."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            container.remove(force=force)
            logger.info(f"Removed container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove container {container_id}: {e}")
            raise
    
    async def rename_container(self, host_id: int, container_id: str, new_name: str) -> bool:
        """Rename a Podman container."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            container.rename(new_name)
            logger.info(f"Renamed container {container_id} to {new_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename container {container_id}: {e}")
            raise
    
    async def get_logs(
        self,
        host_id: int,
        container_id: str,
        tail: Optional[int] = None,
        since: Optional[str] = None
    ) -> str:
        """Get Podman container logs."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            
            kwargs = {}
            if tail:
                kwargs["tail"] = tail
            if since:
                kwargs["since"] = since
            
            logs = container.logs(**kwargs)
            return logs.decode("utf-8") if isinstance(logs, bytes) else logs
        except Exception as e:
            logger.error(f"Failed to get logs for container {container_id}: {e}")
            raise
    
    async def get_stats(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get Podman container resource usage statistics."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            
            # Get single stats reading
            stats = container.stats(stream=False)
            
            return {
                "cpu_stats": stats.get("cpu_stats", {}),
                "memory_stats": stats.get("memory_stats", {}),
                "networks": stats.get("networks", {}),
                "blkio_stats": stats.get("blkio_stats", {}),
            }
        except Exception as e:
            logger.error(f"Failed to get stats for container {container_id}: {e}")
            raise
    
    def close_all(self):
        """Close all Podman client connections."""
        for client in self._clients.values():
            try:
                client.close()
            except Exception as e:
                logger.error(f"Error closing Podman client: {e}")
        self._clients.clear()


# Register Podman provider with the factory (only if podman-py is available)
if PODMAN_AVAILABLE:
    RuntimeProviderFactory.register_provider("podman", PodmanProvider)
