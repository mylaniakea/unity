"""
Unity label injection service for Docker Compose files.
"""
import yaml
from datetime import datetime
from typing import Dict, Any
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class LabelInjector:
    """
    Injects Unity monitoring labels into Docker Compose services.
    """
    
    @staticmethod
    def inject_labels(compose_content: str, stack_name: str, deployed_by: str = "unity") -> str:
        """
        Inject Unity monitoring labels into all services in a compose file.
        
        Args:
            compose_content: Original docker-compose YAML content
            stack_name: Name of the stack
            deployed_by: User or system deploying the stack
            
        Returns:
            Modified docker-compose YAML with Unity labels injected
        """
        try:
            compose_dict = yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse compose file for label injection: {e}")
            return compose_content
        
        services = compose_dict.get('services', {})
        deployed_at = datetime.utcnow().isoformat()
        
        for service_name, service_config in services.items():
            # Initialize labels if not present
            if 'labels' not in service_config:
                service_config['labels'] = {}
            elif isinstance(service_config['labels'], list):
                # Convert list format to dict
                label_dict = {}
                for label in service_config['labels']:
                    if '=' in label:
                        key, value = label.split('=', 1)
                        label_dict[key] = value
                service_config['labels'] = label_dict
            
            # Add Unity labels
            unity_labels = {
                'unity.monitor': 'true',
                'unity.stack': stack_name,
                'unity.service': service_name,
                'unity.managed': 'true',
                'unity.deployed_at': deployed_at,
                'unity.deployed_by': deployed_by
            }
            
            # Merge with existing labels (Unity labels take precedence)
            service_config['labels'].update(unity_labels)
        
        # Convert back to YAML
        return yaml.dump(compose_dict, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def get_unity_labels(stack_name: str, service_name: str, deployed_by: str = "unity") -> Dict[str, str]:
        """
        Get Unity labels as a dictionary.
        
        Args:
            stack_name: Name of the stack
            service_name: Name of the service
            deployed_by: User or system deploying the stack
            
        Returns:
            Dictionary of Unity labels
        """
        return {
            'unity.monitor': 'true',
            'unity.stack': stack_name,
            'unity.service': service_name,
            'unity.managed': 'true',
            'unity.deployed_at': datetime.utcnow().isoformat(),
            'unity.deployed_by': deployed_by
        }
