"""
Docker Compose file validation service.
"""
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple
import docker
from backend.app.schemas.stack import ValidationError, ValidationWarning, ValidationResult
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class ComposeValidator:
    """
    Validates Docker Compose files and provides helpful error messages.
    """
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
    
    def validate(self, compose_content: str, stack_name: str) -> ValidationResult:
        """
        Comprehensive validation of Docker Compose file.
        
        Args:
            compose_content: YAML content of docker-compose file
            stack_name: Name of the stack
            
        Returns:
            ValidationResult with errors, warnings, and required env vars
        """
        errors = []
        warnings = []
        required_env_vars = []
        env_files_needed = []
        
        # 1. YAML Syntax Validation
        try:
            compose_dict = yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            errors.append(ValidationError(
                type="yaml_syntax",
                message=f"YAML syntax error: {str(e)}",
                fix="Check YAML syntax using an online validator or ensure proper indentation"
            ))
            return ValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                required_env_vars=[],
                env_files_needed=[]
            )
        
        if not isinstance(compose_dict, dict):
            errors.append(ValidationError(
                type="invalid_format",
                message="Compose file must be a YAML dictionary",
                fix="Ensure the file starts with valid service definitions"
            ))
            return ValidationResult(valid=False, errors=errors)
        
        # 2. Check for services
        services = compose_dict.get('services', {})
        if not services:
            errors.append(ValidationError(
                type="no_services",
                message="No services defined in compose file",
                fix="Add at least one service under 'services:' key"
            ))
            return ValidationResult(valid=False, errors=errors)
        
        # 3. Validate each service
        for service_name, service_config in services.items():
            # Check for image or build
            if 'image' not in service_config and 'build' not in service_config:
                errors.append(ValidationError(
                    type="missing_image",
                    message=f"Service '{service_name}' has no 'image' or 'build' specified",
                    fix=f"Add 'image: <image_name>' or 'build: <path>' to service '{service_name}'",
                    service=service_name
                ))
            
            # Check port conflicts
            ports = service_config.get('ports', [])
            for port in ports:
                port_str = str(port)
                if ':' in port_str:
                    host_port = port_str.split(':')[0]
                    if self._is_port_in_use(host_port):
                        container_using = self._get_container_using_port(host_port)
                        errors.append(ValidationError(
                            type="port_conflict",
                            message=f"Port {host_port} is already in use" + (f" by container '{container_using}'" if container_using else ""),
                            fix=f"Change port mapping to use a different host port (e.g., '{int(host_port)+1000}:{port_str.split(':')[1]}')",
                            service=service_name
                        ))
            
            # Check volume paths
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                if isinstance(volume, str) and ':' in volume:
                    host_path = volume.split(':')[0]
                    # Only check if it's an absolute path (not named volume)
                    if host_path.startswith('/') or host_path.startswith('./'):
                        full_path = Path(host_path).expanduser().resolve()
                        if not full_path.exists():
                            warnings.append(ValidationWarning(
                                type="missing_volume_path",
                                message=f"Host path '{host_path}' does not exist",
                                fix=f"Create directory: mkdir -p {host_path}",
                                service=service_name
                            ))
            
            # Check env_file references
            env_file = service_config.get('env_file')
            if env_file:
                if isinstance(env_file, str):
                    env_files_needed.append(env_file)
                elif isinstance(env_file, list):
                    env_files_needed.extend(env_file)
        
        # 4. Extract required environment variables
        required_env_vars = self._extract_env_vars(compose_dict)
        
        # 5. Check for common issues
        self._check_common_issues(compose_dict, warnings)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            required_env_vars=required_env_vars,
            env_files_needed=env_files_needed
        )
    
    def _extract_env_vars(self, compose_dict: Dict[str, Any]) -> List[str]:
        """Extract environment variable references from compose file."""
        env_vars = set()
        
        def find_vars(obj):
            if isinstance(obj, str):
                # Find ${VAR} or $VAR patterns
                matches = re.findall(r'\$\{([^}]+)\}|\$(\w+)', obj)
                for match in matches:
                    var_name = match[0] or match[1]
                    # Remove default value if present (${VAR:-default})
                    var_name = var_name.split(':')[0]
                    env_vars.add(var_name)
            elif isinstance(obj, dict):
                for v in obj.values():
                    find_vars(v)
            elif isinstance(obj, list):
                for item in obj:
                    find_vars(item)
        
        find_vars(compose_dict)
        return sorted(list(env_vars))
    
    def _is_port_in_use(self, port: str) -> bool:
        """Check if a port is already in use by Docker containers."""
        if not self.docker_client:
            return False
        
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            if binding.get('HostPort') == str(port):
                                return True
        except Exception as e:
            logger.error(f"Error checking port usage: {e}")
        
        return False
    
    def _get_container_using_port(self, port: str) -> str:
        """Get the name of the container using a specific port."""
        if not self.docker_client:
            return ""
        
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            if binding.get('HostPort') == str(port):
                                return container.name
        except Exception as e:
            logger.error(f"Error finding container for port: {e}")
        
        return ""
    
    def _check_common_issues(self, compose_dict: Dict[str, Any], warnings: List[ValidationWarning]):
        """Check for common compose file issues."""
        services = compose_dict.get('services', {})
        
        for service_name, service_config in services.items():
            # Warn if no restart policy
            if 'restart' not in service_config:
                warnings.append(ValidationWarning(
                    type="no_restart_policy",
                    message=f"Service '{service_name}' has no restart policy",
                    fix=f"Consider adding 'restart: unless-stopped' or 'restart: always'",
                    service=service_name
                ))
            
            # Warn if using 'latest' tag
            image = service_config.get('image', '')
            if image and (':latest' in image or ':' not in image):
                warnings.append(ValidationWarning(
                    type="latest_tag",
                    message=f"Service '{service_name}' uses 'latest' tag",
                    fix="Consider using a specific version tag for reproducibility",
                    service=service_name
                ))
