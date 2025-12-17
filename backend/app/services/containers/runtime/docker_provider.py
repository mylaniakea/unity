"""Docker runtime provider implementation."""

import docker
from docker.errors import DockerException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .provider import ContainerRuntimeProvider, RuntimeProviderFactory
import app.models as models

logger = logging.getLogger(__name__)


class DockerProvider(ContainerRuntimeProvider):
    """Docker runtime provider using docker-py SDK."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self._clients: Dict[int, docker.DockerClient] = {}
    
    async def connect(self, host_id: int) -> docker.DockerClient:
        """Establish connection to Docker host."""
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
        
        if host.runtime_type != "docker":
            raise ValueError(f"Host {host_id} is not a Docker host (type: {host.runtime_type})")
        
        # Create new client based on connection type
        try:
            if host.connection_type == "socket":
                client = self._create_socket_client(host)
            elif host.connection_type == "tcp":
                client = self._create_tcp_client(host)
            elif host.connection_type == "ssh":
                client = self._create_ssh_client(host)
            else:
                raise ValueError(f"Unsupported connection type: {host.connection_type}")
            
            # Cache the client
            self._clients[host_id] = client
            
            # Update host status
            host.last_seen = datetime.utcnow()
            host.status = "online"
            host.status_message = None
            self.db.commit()
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Docker host '{host.name}': {e}")
            host.status = "error"
            host.status_message = str(e)
            self.db.commit()
            raise
    
    def _create_socket_client(self, host: models.ContainerHost) -> docker.DockerClient:
        """Create a Docker client using Unix socket."""
        try:
            client = docker.DockerClient(base_url=host.connection_string)
            client.ping()  # Test connection
            return client
        except Exception as e:
            raise DockerException(f"Failed to connect via socket: {e}")
    
    def _create_tcp_client(self, host: models.ContainerHost) -> docker.DockerClient:
        """Create a Docker client using TCP connection."""
        try:
            tls_config = None
            if host.tls_enabled:
                tls_config = docker.tls.TLSConfig(
                    verify=host.tls_verify,
                    client_cert=(host.tls_cert_path,) if host.tls_cert_path else None
                )
            
            client = docker.DockerClient(
                base_url=host.connection_string,
                tls=tls_config
            )
            client.ping()  # Test connection
            return client
        except Exception as e:
            raise DockerException(f"Failed to connect via TCP: {e}")
    
    def _create_ssh_client(self, host: models.ContainerHost) -> docker.DockerClient:
        """Create a Docker client using SSH connection."""
        try:
            # SSH connection format: ssh://user@host:port
            base_url = f"ssh://{host.ssh_username}@{host.ssh_host}:{host.ssh_port}"
            
            client = docker.DockerClient(base_url=base_url)
            client.ping()  # Test connection
            return client
        except Exception as e:
            raise DockerException(f"Failed to connect via SSH: {e}")
    
    async def get_host_info(self, host_id: int) -> Dict[str, Any]:
        """Get Docker host information."""
        try:
            client = await self.connect(host_id)
            info = client.info()
            version = client.version()
            
            return {
                "runtime_type": "docker",
                "docker_version": version.get("Version"),
                "api_version": version.get("ApiVersion"),
                "os": info.get("OperatingSystem"),
                "architecture": info.get("Architecture"),
                "cpus": info.get("NCPU"),
                "memory": info.get("MemTotal"),
                "containers": info.get("Containers"),
                "containers_running": info.get("ContainersRunning"),
                "containers_paused": info.get("ContainersPaused"),
                "containers_stopped": info.get("ContainersStopped"),
                "images": info.get("Images"),
                "server_version": info.get("ServerVersion"),
                "kernel_version": info.get("KernelVersion"),
            }
        except Exception as e:
            logger.error(f"Failed to get host info for host {host_id}: {e}")
            raise
    
    async def list_containers(self, host_id: int, all_containers: bool = True) -> List[Dict[str, Any]]:
        """List all containers on a Docker host."""
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
                    "state": container.attrs.get("State", {}).get("Status"),
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
        """Pull a Docker image."""
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
        """Create a new Docker container."""
        try:
            client = await self.connect(host_id)
            
            # Extract Docker-specific config
            container_config = config.get("container_config", {})
            host_config = config.get("host_config", {})
            networking_config = config.get("networking_config", {})
            
            container = client.containers.create(
                image=image,
                name=name,
                **container_config,
                host_config=host_config,
                networking_config=networking_config
            )
            
            logger.info(f"Created container {name} with ID {container.id}")
            return container.id
        except Exception as e:
            logger.error(f"Failed to create container {name}: {e}")
            raise RuntimeError(f"Failed to create container: {e}")
    
    async def start_container(self, host_id: int, container_id: str) -> bool:
        """Start a Docker container."""
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
        """Stop a Docker container."""
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
        """Remove a Docker container."""
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
        """Rename a Docker container."""
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
        """Get Docker container logs."""
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
        """Get Docker container resource usage statistics."""
        try:
            client = await self.connect(host_id)
            container = client.containers.get(container_id)
            
            # Get single stats reading (stream=False)
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
        """Close all Docker client connections."""
        for client in self._clients.values():
            try:
                client.close()
            except Exception as e:
                logger.error(f"Error closing Docker client: {e}")
        self._clients.clear()


# Register Docker provider with the factory
RuntimeProviderFactory.register_provider("docker", DockerProvider)
