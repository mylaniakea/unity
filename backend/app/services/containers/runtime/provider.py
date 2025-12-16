"""Abstract base class for container runtime providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session


class ContainerRuntimeProvider(ABC):
    """Abstract base class for container runtime providers (Docker, Podman, Kubernetes)."""
    
    def __init__(self, db: Session):
        """Initialize the provider with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    @abstractmethod
    async def connect(self, host_id: int) -> Any:
        """Establish connection to the container runtime.
        
        Args:
            host_id: Database ID of the container host
            
        Returns:
            Runtime-specific client object
            
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def get_host_info(self, host_id: int) -> Dict[str, Any]:
        """Get information about the container runtime host.
        
        Args:
            host_id: Database ID of the container host
            
        Returns:
            Dict containing host information (version, architecture, resources, etc.)
        """
        pass
    
    @abstractmethod
    async def list_containers(self, host_id: int, all_containers: bool = True) -> List[Dict[str, Any]]:
        """List all containers/workloads on the host.
        
        Args:
            host_id: Database ID of the container host
            all_containers: Include stopped containers (ignored for K8s)
            
        Returns:
            List of container/workload information dicts
        """
        pass
    
    @abstractmethod
    async def get_container_details(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific container/workload.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container/workload identifier
            
        Returns:
            Dict with detailed container information
        """
        pass
    
    @abstractmethod
    async def pull_image(self, host_id: int, image: str, tag: str = "latest") -> bool:
        """Pull a container image.
        
        Args:
            host_id: Database ID of the container host
            image: Image name
            tag: Image tag
            
        Returns:
            True if successful
            
        Raises:
            RuntimeError: If pull fails
        """
        pass
    
    @abstractmethod
    async def create_container(
        self,
        host_id: int,
        image: str,
        name: str,
        config: Dict[str, Any]
    ) -> str:
        """Create a new container/workload.
        
        Args:
            host_id: Database ID of the container host
            image: Image name with tag
            name: Container/workload name
            config: Runtime-specific configuration
            
        Returns:
            Container/workload ID
            
        Raises:
            RuntimeError: If creation fails
        """
        pass
    
    @abstractmethod
    async def start_container(self, host_id: int, container_id: str) -> bool:
        """Start a container/workload.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container/workload identifier
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def stop_container(self, host_id: int, container_id: str, timeout: int = 10) -> bool:
        """Stop a container/workload.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container/workload identifier
            timeout: Timeout in seconds
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def remove_container(self, host_id: int, container_id: str, force: bool = False) -> bool:
        """Remove a container/workload.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container/workload identifier
            force: Force removal even if running
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def rename_container(self, host_id: int, container_id: str, new_name: str) -> bool:
        """Rename a container.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container identifier
            new_name: New container name
            
        Returns:
            True if successful
            
        Note:
            Not supported for Kubernetes workloads
        """
        pass
    
    @abstractmethod
    async def get_logs(
        self,
        host_id: int,
        container_id: str,
        tail: Optional[int] = None,
        since: Optional[str] = None
    ) -> str:
        """Get container/pod logs.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container/pod identifier
            tail: Number of lines from end
            since: Timestamp to get logs from
            
        Returns:
            Log output as string
        """
        pass
    
    @abstractmethod
    async def get_stats(self, host_id: int, container_id: str) -> Dict[str, Any]:
        """Get container/pod resource usage statistics.
        
        Args:
            host_id: Database ID of the container host
            container_id: Container/pod identifier
            
        Returns:
            Dict with CPU, memory, network stats
        """
        pass
    
    @abstractmethod
    def close_all(self):
        """Close all active connections and clean up resources."""
        pass


class RuntimeProviderFactory:
    """Factory for creating runtime provider instances."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register_provider(cls, runtime_type: str, provider_class: type):
        """Register a runtime provider class.
        
        Args:
            runtime_type: Runtime type identifier (docker, podman, kubernetes)
            provider_class: Provider class implementing ContainerRuntimeProvider
        """
        cls._providers[runtime_type] = provider_class
    
    @classmethod
    def create_provider(cls, runtime_type: str, db: Session) -> ContainerRuntimeProvider:
        """Create a runtime provider instance.
        
        Args:
            runtime_type: Runtime type identifier
            db: Database session
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If runtime type is not registered
        """
        if runtime_type not in cls._providers:
            raise ValueError(
                f"Unknown runtime type: {runtime_type}. "
                f"Available types: {', '.join(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[runtime_type]
        return provider_class(db)
    
    @classmethod
    def get_supported_runtimes(cls) -> List[str]:
        """Get list of supported runtime types.
        
        Returns:
            List of runtime type identifiers
        """
        return list(cls._providers.keys())
