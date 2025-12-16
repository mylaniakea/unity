import logging
import time
import socket
from typing import Dict, Any, Optional
from docker.models.containers import Container as DockerContainer

logger = logging.getLogger(__name__)


class HealthValidator:
    """Service for validating container health after updates"""
    
    def __init__(self, docker_client):
        self.docker_client = docker_client
        self.health_check_timeout = 60  # seconds
        self.health_check_interval = 5  # seconds
    
    async def validate_container_health(
        self,
        container: DockerContainer,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate container health after update.
        
        Returns dict with:
        - healthy: bool
        - status: str
        - checks: dict of individual checks
        - errors: list of error messages
        """
        timeout = timeout or self.health_check_timeout
        start_time = time.time()
        
        result = {
            "healthy": False,
            "status": "unknown",
            "checks": {},
            "errors": [],
            "duration": 0.0
        }
        
        try:
            # Refresh container state
            container.reload()
            
            # Check 1: Container is running
            is_running = self._check_running(container)
            result["checks"]["running"] = is_running
            
            if not is_running:
                result["errors"].append("Container is not running")
                result["status"] = "not_running"
                result["duration"] = time.time() - start_time
                return result
            
            # Check 2: Wait for container to stabilize
            stabilized = await self._wait_for_stabilization(container, timeout)
            result["checks"]["stabilized"] = stabilized
            
            if not stabilized:
                result["errors"].append("Container failed to stabilize within timeout")
                result["status"] = "unstable"
                result["duration"] = time.time() - start_time
                return result
            
            # Check 3: Docker health check (if defined)
            health_status = self._check_docker_health(container)
            result["checks"]["docker_health"] = health_status
            
            if health_status == "unhealthy":
                result["errors"].append("Docker health check failed")
            
            # Check 4: Port accessibility
            ports_accessible = self._check_ports(container)
            result["checks"]["ports"] = ports_accessible
            
            if not ports_accessible["all_accessible"]:
                result["errors"].append(
                    f"Some ports not accessible: {ports_accessible['inaccessible']}"
                )
            
            # Check 5: Exit code (should be 0 or None for running containers)
            exit_code = container.attrs.get("State", {}).get("ExitCode")
            result["checks"]["exit_code"] = exit_code
            
            if exit_code and exit_code != 0:
                result["errors"].append(f"Non-zero exit code: {exit_code}")
            
            # Determine overall health
            result["healthy"] = (
                is_running and
                stabilized and
                health_status in ["healthy", "none"] and
                ports_accessible["all_accessible"] and
                (exit_code is None or exit_code == 0)
            )
            
            result["status"] = "healthy" if result["healthy"] else "unhealthy"
            
        except Exception as e:
            logger.error(f"Error validating container health: {e}")
            result["errors"].append(f"Health check exception: {str(e)}")
            result["status"] = "error"
        
        result["duration"] = time.time() - start_time
        return result
    
    def _check_running(self, container: DockerContainer) -> bool:
        """Check if container is in running state"""
        try:
            container.reload()
            return container.status == "running"
        except Exception as e:
            logger.error(f"Error checking container running status: {e}")
            return False
    
    async def _wait_for_stabilization(
        self,
        container: DockerContainer,
        timeout: int
    ) -> bool:
        """
        Wait for container to stabilize (not restarting continuously).
        A container is considered stable if it stays running for at least 10 seconds.
        """
        stabilization_period = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container.reload()
                
                if container.status != "running":
                    return False
                
                # Check how long container has been running
                started_at = container.attrs.get("State", {}).get("StartedAt")
                if started_at:
                    # Container has been running, wait for stabilization period
                    await self._async_sleep(stabilization_period)
                    
                    # Check again after stabilization period
                    container.reload()
                    if container.status == "running":
                        return True
                
                await self._async_sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error waiting for stabilization: {e}")
                return False
        
        return False
    
    def _check_docker_health(self, container: DockerContainer) -> str:
        """
        Check Docker's built-in health check status.
        Returns: "healthy", "unhealthy", "starting", or "none"
        """
        try:
            container.reload()
            health = container.attrs.get("State", {}).get("Health", {})
            
            if not health:
                # No health check defined
                return "none"
            
            status = health.get("Status", "none").lower()
            return status
            
        except Exception as e:
            logger.error(f"Error checking Docker health: {e}")
            return "error"
    
    def _check_ports(self, container: DockerContainer) -> Dict[str, Any]:
        """
        Check if exposed ports are accessible.
        Returns dict with accessibility info.
        """
        result = {
            "all_accessible": True,
            "accessible": [],
            "inaccessible": [],
            "ports_checked": 0
        }
        
        try:
            container.reload()
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            
            if not ports:
                # No ports exposed
                return result
            
            for container_port, host_bindings in ports.items():
                if not host_bindings:
                    continue
                
                for binding in host_bindings:
                    host_ip = binding.get("HostIp", "127.0.0.1")
                    host_port = binding.get("HostPort")
                    
                    if not host_port:
                        continue
                    
                    result["ports_checked"] += 1
                    
                    # Try to connect to the port
                    if self._check_port_accessible(host_ip, int(host_port)):
                        result["accessible"].append(f"{host_ip}:{host_port}")
                    else:
                        result["inaccessible"].append(f"{host_ip}:{host_port}")
                        result["all_accessible"] = False
            
        except Exception as e:
            logger.error(f"Error checking ports: {e}")
            result["all_accessible"] = False
        
        return result
    
    def _check_port_accessible(self, host: str, port: int, timeout: int = 2) -> bool:
        """Check if a specific port is accessible"""
        try:
            # Use 0.0.0.0 or :: as localhost for binding checks
            if host in ["0.0.0.0", "::"]:
                host = "127.0.0.1"
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return result == 0
            
        except Exception as e:
            logger.debug(f"Port {host}:{port} not accessible: {e}")
            return False
    
    async def _async_sleep(self, seconds: int):
        """Async sleep wrapper"""
        import asyncio
        await asyncio.sleep(seconds)
