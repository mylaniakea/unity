"""Container runtime manager - stub implementation."""
from app.services.containers.docker_manager import DockerManager

# Re-export for compatibility
__all__ = ['DockerManager']
