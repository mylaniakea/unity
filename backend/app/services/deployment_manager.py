"""
Deployment Manager Service

Manages Docker Compose stacks using Docker Python SDK.
Provides file-system based stack management similar to Dockge.
"""
import os
import yaml
import shutil
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime
import docker
from docker.errors import DockerException, NotFound, APIError

logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manages Docker Compose stacks with file-system integration."""
    
    def __init__(self, stacks_dir: str = "/app/stacks"):
        """
        Initialize DeploymentManager.
        
        Args:
            stacks_dir: Directory where stacks are stored
        """
        self.stacks_dir = Path(stacks_dir)
        self.stacks_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            self.docker_client = docker.from_env()
            logger.info(f"✓ Connected to Docker daemon")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
    
    def list_stacks(self) -> List[Dict]:
        """
        List all stacks in the stacks directory.
        
        Returns:
            List of stack metadata dictionaries
        """
        stacks = []
        
        for stack_dir in self.stacks_dir.iterdir():
            if not stack_dir.is_dir() or stack_dir.name.startswith('.'):
                continue
            
            compose_file = stack_dir / "compose.yaml"
            if not compose_file.exists():
                compose_file = stack_dir / "docker-compose.yml"
            
            if compose_file.exists():
                try:
                    # Read compose file
                    with open(compose_file, 'r') as f:
                        compose_data = yaml.safe_load(f)
                    
                    # Get container status
                    containers = self._get_stack_containers(stack_dir.name)
                    
                    running_count = sum(1 for c in containers if c['state'] == 'running')
                    total_count = len(containers)
                    
                    status = 'running' if running_count == total_count and total_count > 0 else \
                             'partial' if running_count > 0 else \
                             'stopped' if total_count > 0 else 'unknown'
                    
                    stacks.append({
                        'name': stack_dir.name,
                        'path': str(stack_dir),
                        'compose_file': str(compose_file),
                        'status': status,
                        'containers': total_count,
                        'running': running_count,
                        'created_at': datetime.fromtimestamp(compose_file.stat().st_ctime).isoformat(),
                        'updated_at': datetime.fromtimestamp(compose_file.stat().st_mtime).isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"Error reading stack {stack_dir.name}: {e}")
                    continue
        
        return sorted(stacks, key=lambda x: x['name'])
    
    def get_stack(self, name: str) -> Optional[Dict]:
        """
        Get detailed information about a stack.
        
        Args:
            name: Stack name
            
        Returns:
            Stack details including compose content and container info
        """
        stack_dir = self.stacks_dir / name
        if not stack_dir.exists():
            return None
        
        compose_file = stack_dir / "compose.yaml"
        if not compose_file.exists():
            compose_file = stack_dir / "docker-compose.yml"
        
        if not compose_file.exists():
            return None
        
        try:
            with open(compose_file, 'r') as f:
                compose_content = f.read()
                compose_data = yaml.safe_load(compose_content)
            
            containers = self._get_stack_containers(name)
            
            return {
                'name': name,
                'path': str(stack_dir),
                'compose_file': str(compose_file),
                'compose_content': compose_content,
                'compose_data': compose_data,
                'containers': containers,
                'created_at': datetime.fromtimestamp(compose_file.stat().st_ctime).isoformat(),
                'updated_at': datetime.fromtimestamp(compose_file.stat().st_mtime).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting stack {name}: {e}")
            return None
    
    async def create_stack(self, name: str, compose_content: str, deploy: bool = True) -> Dict:
        """
        Create a new stack.
        
        Args:
            name: Stack name
            compose_content: Docker Compose YAML content
            deploy: Whether to deploy immediately
            
        Returns:
            Stack information
        """
        # Validate stack name
        if not name or '/' in name or '\\' in name:
            raise ValueError("Invalid stack name")
        
        stack_dir = self.stacks_dir / name
        if stack_dir.exists():
            raise ValueError(f"Stack {name} already exists")
        
        # Validate YAML
        try:
            yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        # Create stack directory
        stack_dir.mkdir(parents=True)
        
        # Write compose file atomically
        compose_file = stack_dir / "compose.yaml"
        temp_file = stack_dir / ".compose.yaml.tmp"
        
        try:
            with open(temp_file, 'w') as f:
                f.write(compose_content)
            temp_file.rename(compose_file)
            
            logger.info(f"Created stack {name}")
            
            if deploy:
                await self._deploy_stack(name)
            
            return self.get_stack(name)
        except Exception as e:
            # Cleanup on error
            if stack_dir.exists():
                shutil.rmtree(stack_dir)
            raise Exception(f"Failed to create stack: {e}")
    
    async def update_stack(self, name: str, compose_content: str, redeploy: bool = True) -> Dict:
        """
        Update an existing stack.
        
        Args:
            name: Stack name
            compose_content: New Docker Compose YAML content
            redeploy: Whether to redeploy after update
            
        Returns:
            Updated stack information
        """
        stack_dir = self.stacks_dir / name
        if not stack_dir.exists():
            raise ValueError(f"Stack {name} does not exist")
        
        # Validate YAML
        try:
            yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        compose_file = stack_dir / "compose.yaml"
        if not compose_file.exists():
            compose_file = stack_dir / "docker-compose.yml"
        
        # Backup current file
        backup_file = stack_dir / f".compose.yaml.backup.{int(datetime.now().timestamp())}"
        if compose_file.exists():
            shutil.copy(compose_file, backup_file)
        
        # Write new content atomically
        temp_file = stack_dir / ".compose.yaml.tmp"
        
        try:
            with open(temp_file, 'w') as f:
                f.write(compose_content)
            temp_file.rename(compose_file)
            
            logger.info(f"Updated stack {name}")
            
            if redeploy:
                await self._deploy_stack(name)
            
            return self.get_stack(name)
        except Exception as e:
            # Restore backup on error
            if backup_file.exists():
                shutil.copy(backup_file, compose_file)
            raise Exception(f"Failed to update stack: {e}")
        finally:
            # Cleanup backup
            if backup_file.exists():
                backup_file.unlink()
    
    async def delete_stack(self, name: str, stop_containers: bool = True) -> bool:
        """
        Delete a stack.
        
        Args:
            name: Stack name
            stop_containers: Whether to stop containers first
            
        Returns:
            True if successful
        """
        stack_dir = self.stacks_dir / name
        if not stack_dir.exists():
            raise ValueError(f"Stack {name} does not exist")
        
        try:
            if stop_containers:
                await self.stop_stack(name)
            
            # Remove stack directory
            shutil.rmtree(stack_dir)
            logger.info(f"Deleted stack {name}")
            return True
        except Exception as e:
            raise Exception(f"Failed to delete stack: {e}")
    
    async def start_stack(self, name: str) -> Dict:
        """Start a stopped stack."""
        await self._deploy_stack(name)
        return self.get_stack(name)
    
    async def stop_stack(self, name: str) -> Dict:
        """Stop a running stack."""
        stack_dir = self.stacks_dir / name
        compose_file = stack_dir / "compose.yaml"
        if not compose_file.exists():
            compose_file = stack_dir / "docker-compose.yml"
        
        try:
            # Use docker compose down
            process = await asyncio.create_subprocess_exec(
                'docker', 'compose', '-f', str(compose_file), '-p', name, 'down',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.wait()
            
            logger.info(f"Stopped stack {name}")
            return self.get_stack(name)
        except Exception as e:
            raise Exception(f"Failed to stop stack: {e}")
    
    async def restart_stack(self, name: str) -> Dict:
        """Restart a stack."""
        await self.stop_stack(name)
        await asyncio.sleep(1)  # Give containers time to stop
        await self.start_stack(name)
        return self.get_stack(name)
    
    async def get_stack_logs(self, name: str, follow: bool = False, tail: int = 100) -> AsyncGenerator[str, None]:
        """
        Stream logs from all containers in a stack.
        
        Args:
            name: Stack name
            follow: Whether to follow logs
            tail: Number of lines to show from end
            
        Yields:
            Log lines
        """
        containers = self._get_stack_containers(name)
        
        for container_info in containers:
            try:
                container = self.docker_client.containers.get(container_info['id'])
                logs = container.logs(stream=follow, follow=follow, tail=tail, timestamps=True)
                
                if follow:
                    for line in logs:
                        yield f"[{container_info['name']}] {line.decode('utf-8', errors='ignore').strip()}"
                else:
                    for line in logs.decode('utf-8', errors='ignore').split('\n'):
                        if line.strip():
                            yield f"[{container_info['name']}] {line.strip()}"
            except Exception as e:
                logger.error(f"Error getting logs from {container_info['name']}: {e}")
                continue
    
    def get_stack_metrics(self, name: str) -> Dict:
        """
        Get resource metrics for a stack.
        
        Args:
            name: Stack name
            
        Returns:
            Metrics dictionary
        """
        containers = self._get_stack_containers(name)
        metrics = []
        
        for container_info in containers:
            try:
                container = self.docker_client.containers.get(container_info['id'])
                stats = container.stats(stream=False)
                
                # Calculate CPU percentage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
                
                # Calculate memory usage
                mem_usage = stats['memory_stats'].get('usage', 0)
                mem_limit = stats['memory_stats'].get('limit', 1)
                mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0
                
                metrics.append({
                    'container': container_info['name'],
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_usage': mem_usage,
                    'memory_limit': mem_limit,
                    'memory_percent': round(mem_percent, 2),
                })
            except Exception as e:
                logger.error(f"Error getting metrics from {container_info['name']}: {e}")
                continue
        
        return {'stack': name, 'containers': metrics}
    
    def _get_stack_containers(self, stack_name: str) -> List[Dict]:
        """Get containers belonging to a stack."""
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={'label': f'com.docker.compose.project={stack_name}'}
            )
            
            return [{
                'id': c.id,
                'name': c.name,
                'image': c.image.tags[0] if c.image.tags else c.image.id,
                'state': c.status,
                'created': c.attrs['Created'],
            } for c in containers]
        except Exception as e:
            logger.error(f"Error listing containers for stack {stack_name}: {e}")
            return []
    
    async def _deploy_stack(self, name: str):
        """Deploy a stack using docker compose up."""
        stack_dir = self.stacks_dir / name
        compose_file = stack_dir / "compose.yaml"
        if not compose_file.exists():
            compose_file = stack_dir / "docker-compose.yml"
        
        try:
            process = await asyncio.create_subprocess_exec(
                'docker', 'compose', '-f', str(compose_file), '-p', name, 'up', '-d',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.wait()
            
            if process.returncode != 0:
                raise Exception(f"Deploy failed: {stderr.decode()}")
            
            logger.info(f"Deployed stack {name}")
        except Exception as e:
            raise Exception(f"Failed to deploy stack: {e}")


# Global instance
deployment_manager = DeploymentManager(
    stacks_dir=os.getenv('STACKS_DIR', '/app/stacks')
)
