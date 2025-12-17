import docker
from docker.errors import DockerException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import app.models as models

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker client connections across multiple hosts"""
    
    def __init__(self, db: Session):
        self.db = db
        self._clients: Dict[int, docker.DockerClient] = {}
    
    def get_client(self, host_id: int) -> docker.DockerClient:
        """Get or create a Docker client for the specified host"""
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
        host = self.db.query(models.DockerHost).filter(
            models.DockerHost.id == host_id
        ).first()
        
        if not host:
            raise ValueError(f"Docker host with ID {host_id} not found")
        
        if not host.enabled:
            raise ValueError(f"Docker host '{host.name}' is disabled")
        
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
            logger.error(f"Failed to connect to host '{host.name}': {e}")
            host.status = "error"
            host.status_message = str(e)
            self.db.commit()
            raise
    
    def _create_socket_client(self, host: models.DockerHost) -> docker.DockerClient:
        """Create a Docker client using Unix socket"""
        try:
            client = docker.DockerClient(base_url=host.connection_string)
            client.ping()  # Test connection
            return client
        except Exception as e:
            raise DockerException(f"Failed to connect via socket: {e}")
    
    def _create_tcp_client(self, host: models.DockerHost) -> docker.DockerClient:
        """Create a Docker client using TCP connection"""
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
    
    def _create_ssh_client(self, host: models.DockerHost) -> docker.DockerClient:
        """Create a Docker client using SSH connection"""
        try:
            # SSH connection format: ssh://user@host:port
            if host.ssh_key_path:
                base_url = f"ssh://{host.ssh_username}@{host.ssh_host}:{host.ssh_port}"
            else:
                base_url = f"ssh://{host.ssh_username}@{host.ssh_host}:{host.ssh_port}"
            
            # Note: SSH connections may require additional configuration
            # such as SSH agent or key files
            client = docker.DockerClient(base_url=base_url)
            client.ping()  # Test connection
            return client
        except Exception as e:
            raise DockerException(f"Failed to connect via SSH: {e}")
    
    def get_host_info(self, host_id: int) -> Dict[str, Any]:
        """Get Docker host information"""
        try:
            client = self.get_client(host_id)
            info = client.info()
            version = client.version()
            
            return {
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
    
    def list_containers(self, host_id: int, all_containers: bool = True) -> List[Dict[str, Any]]:
        """List all containers on a Docker host"""
        try:
            client = self.get_client(host_id)
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
    
    def get_container_details(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific container"""
        try:
            client = self.get_client(host_id)
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
    
    def close_all(self):
        """Close all Docker client connections"""
        for client in self._clients.values():
            try:
                client.close()
            except Exception as e:
                logger.error(f"Error closing Docker client: {e}")
        self._clients.clear()
