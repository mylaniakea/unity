"""
Docker Monitor Plugin

Monitors Docker containers - stats, health, resource usage.
Requires docker Python SDK.
"""

import docker
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class DockerMonitorPlugin(PluginBase):
    """Monitors Docker containers and their resource usage"""
    
    def __init__(self):
        super().__init__()
        self._client: Optional[docker.DockerClient] = None
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="docker-monitor",
            name="Docker Monitor",
            version="1.0.0",
            description="Monitors Docker containers, images, and resource usage",
            author="Unity Team",
            category=PluginCategory.CONTAINER,
            tags=["docker", "containers", "orchestration"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["docker"],
            config_schema={
                "type": "object",
                "properties": {
                    "docker_url": {
                        "type": "string",
                        "default": "unix://var/run/docker.sock",
                        "description": "Docker daemon URL"
                    },
                    "include_stopped": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include stopped containers in results"
                    },
                    "collect_stats": {
                        "type": "boolean",
                        "default": True,
                        "description": "Collect resource usage statistics"
                    },
                    "max_containers": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum number of containers to monitor"
                    }
                }
            }
        )
    
    def _get_client(self) -> docker.DockerClient:
        """Get or create Docker client"""
        if self._client is None:
            docker_url = self.config.get("docker_url", "unix://var/run/docker.sock")
            if docker_url.startswith("unix://"):
                self._client = docker.DockerClient(base_url=docker_url)
            else:
                self._client = docker.from_env()
        return self._client
    
    def _format_bytes(self, bytes_value: int) -> Dict[str, Any]:
        """Format bytes to human-readable form"""
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(bytes_value)
        unit_index = 0
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        return {
            "bytes": bytes_value,
            "formatted": f"{value:.2f} {units[unit_index]}",
            "value": round(value, 2),
            "unit": units[unit_index]
        }
    
    def _get_container_info(self, container: Any, collect_stats: bool = True) -> Dict[str, Any]:
        """Extract container information"""
        info = {
            "id": container.short_id,
            "name": container.name,
            "image": container.image.tags[0] if container.image.tags else container.image.short_id,
            "status": container.status,
            "state": {
                "running": container.status == "running",
                "paused": container.status == "paused",
                "restarting": container.status == "restarting",
                "dead": container.status == "dead",
                "exited": container.status == "exited"
            },
            "created": container.attrs.get("Created"),
            "ports": {}
        }
        
        # Extract port mappings
        if container.ports:
            for container_port, host_bindings in container.ports.items():
                if host_bindings:
                    info["ports"][container_port] = [
                        f"{binding['HostIp']}:{binding['HostPort']}" 
                        for binding in host_bindings
                    ]
        
        # Collect stats if requested and container is running
        if collect_stats and container.status == "running":
            try:
                stats = container.stats(stream=False)
                
                # CPU stats
                cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                           stats["precpu_stats"]["cpu_usage"]["total_usage"]
                system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                              stats["precpu_stats"]["system_cpu_usage"]
                cpu_count = stats["cpu_stats"]["online_cpus"]
                
                cpu_percent = 0.0
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
                
                # Memory stats
                memory_usage = stats["memory_stats"].get("usage", 0)
                memory_limit = stats["memory_stats"].get("limit", 0)
                memory_percent = 0.0
                if memory_limit > 0:
                    memory_percent = (memory_usage / memory_limit) * 100.0
                
                # Network stats
                network_rx = 0
                network_tx = 0
                if "networks" in stats:
                    for net_stats in stats["networks"].values():
                        network_rx += net_stats.get("rx_bytes", 0)
                        network_tx += net_stats.get("tx_bytes", 0)
                
                # Block I/O stats
                block_read = 0
                block_write = 0
                if "blkio_stats" in stats and "io_service_bytes_recursive" in stats["blkio_stats"]:
                    for entry in stats["blkio_stats"]["io_service_bytes_recursive"] or []:
                        if entry["op"] == "read":
                            block_read += entry["value"]
                        elif entry["op"] == "write":
                            block_write += entry["value"]
                
                info["stats"] = {
                    "cpu_percent": round(cpu_percent, 2),
                    "memory": {
                        "usage": self._format_bytes(memory_usage),
                        "limit": self._format_bytes(memory_limit),
                        "percent": round(memory_percent, 2)
                    },
                    "network": {
                        "rx": self._format_bytes(network_rx),
                        "tx": self._format_bytes(network_tx)
                    },
                    "block_io": {
                        "read": self._format_bytes(block_read),
                        "write": self._format_bytes(block_write)
                    }
                }
            except Exception as e:
                info["stats_error"] = str(e)
        
        return info
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect Docker monitoring data"""
        
        try:
            client = self._get_client()
            
            # Get Docker version info
            version = client.version()
            
            # Get Docker info
            docker_info = client.info()
            
            # Container filters
            include_stopped = self.config.get("include_stopped", False)
            max_containers = self.config.get("max_containers", 50)
            collect_stats = self.config.get("collect_stats", True)
            
            # Get containers
            all_containers = include_stopped
            containers_list = client.containers.list(all=all_containers, limit=max_containers)
            
            # Collect container information
            containers = []
            running_count = 0
            stopped_count = 0
            
            for container in containers_list:
                container_info = self._get_container_info(container, collect_stats)
                containers.append(container_info)
                
                if container.status == "running":
                    running_count += 1
                else:
                    stopped_count += 1
            
            # Get images
            images = []
            for image in client.images.list():
                images.append({
                    "id": image.short_id,
                    "tags": image.tags,
                    "size": self._format_bytes(image.attrs.get("Size", 0))
                })
            
            # Get volumes
            volumes = []
            for volume in client.volumes.list():
                volumes.append({
                    "name": volume.name,
                    "driver": volume.attrs.get("Driver"),
                    "mountpoint": volume.attrs.get("Mountpoint")
                })
            
            # Get networks
            networks = []
            for network in client.networks.list():
                networks.append({
                    "id": network.short_id,
                    "name": network.name,
                    "driver": network.attrs.get("Driver"),
                    "scope": network.attrs.get("Scope")
                })
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "docker_version": version.get("Version"),
                "api_version": version.get("ApiVersion"),
                "system": {
                    "containers_total": docker_info.get("Containers", 0),
                    "containers_running": running_count,
                    "containers_stopped": stopped_count,
                    "containers_paused": docker_info.get("ContainersPaused", 0),
                    "images": docker_info.get("Images", 0),
                    "server_version": docker_info.get("ServerVersion"),
                    "storage_driver": docker_info.get("Driver"),
                    "memory_total": self._format_bytes(docker_info.get("MemTotal", 0)),
                    "cpus": docker_info.get("NCPU", 0)
                },
                "containers": containers[:max_containers],
                "images": images,
                "volumes": volumes,
                "networks": networks
            }
            
            return data
            
        except docker.errors.DockerException as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Docker connection failed",
                "message": str(e),
                "docker_available": False
            }
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Unexpected error",
                "message": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Docker daemon connectivity"""
        try:
            client = self._get_client()
            client.ping()
            
            # Get basic info
            info = client.info()
            version = client.version()
            
            return {
                "healthy": True,
                "message": "Docker daemon is accessible",
                "details": {
                    "docker_version": version.get("Version"),
                    "api_version": version.get("ApiVersion"),
                    "containers": info.get("Containers", 0),
                    "images": info.get("Images", 0)
                }
            }
        except docker.errors.DockerException as e:
            return {
                "healthy": False,
                "message": f"Cannot connect to Docker daemon: {str(e)}",
                "details": {
                    "suggestion": "Ensure Docker is running and accessible"
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            }
    
    def __del__(self):
        """Cleanup Docker client"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
