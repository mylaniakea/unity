"""
Blueprint Loader - Loads and manages application blueprints.
"""
import logging
import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BlueprintLoader:
    """Manages application blueprints for deployment."""
    
    def __init__(self, blueprint_dir: Optional[str] = None):
        """Initialize blueprint loader."""
        if blueprint_dir:
            self.blueprint_dir = Path(blueprint_dir)
        else:
            self.blueprint_dir = Path(__file__).parent.parent.parent / "blueprints"
        
        self.blueprints = {}
        self._load_all_blueprints()
    
    def _load_all_blueprints(self):
        """Load all blueprints from directory."""
        if not self.blueprint_dir.exists():
            logger.warning(f"Blueprint directory not found: {self.blueprint_dir}")
            self._register_builtin_blueprints()
            return
        
        for yaml_file in self.blueprint_dir.glob("*.yaml"):
            self._load_blueprint(yaml_file)
        
        # Register built-in blueprints as fallback
        self._register_builtin_blueprints()
    
    def _load_blueprint(self, path: Path):
        """Load a single blueprint from file."""
        try:
            with open(path, 'r') as f:
                blueprint = yaml.safe_load(f)
                if blueprint and blueprint.get("name"):
                    self.blueprints[blueprint["name"]] = blueprint
                    logger.info(f"Loaded blueprint: {blueprint['name']}")
        except Exception as e:
            logger.error(f"Error loading blueprint {path}: {e}")
    
    def _register_builtin_blueprints(self):
        """Register built-in blueprints."""
        # PostgreSQL blueprint
        self.blueprints["postgresql"] = {
            "name": "postgresql",
            "description": "PostgreSQL Database",
            "type": "statefulset",
            "image": "postgres:15-alpine",
            "port": 5432,
            "replicas": 1,
            "storage": {
                "size": "20Gi",
                "storage_class": "local-path",
                "mount_path": "/var/lib/postgresql/data"
            },
            "secrets": {
                "POSTGRES_USER": "auto-generate",
                "POSTGRES_PASSWORD": "auto-generate"
            },
            "env": {
                "POSTGRES_DB": "app_db",
                "PGDATA": "/var/lib/postgresql/data/pgdata"
            },
            "resources": {
                "cpu": "500m",
                "memory": "512Mi"
            }
        }
        
        # Nginx blueprint
        self.blueprints["nginx"] = {
            "name": "nginx",
            "description": "Nginx Reverse Proxy",
            "type": "deployment",
            "image": "nginx:latest",
            "port": 80,
            "replicas": 1,
            "service_type": "ClusterIP",
            "ingress": {
                "host": "*.local"
            },
            "config": {
                "nginx.conf": """
                upstream backend {
                    server backend-service.homelab.svc.cluster.local:8000;
                }
                server {
                    listen 80;
                    location / {
                        proxy_pass http://backend;
                    }
                }
                """
            },
            "resources": {
                "cpu": "100m",
                "memory": "128Mi"
            },
            "health_check": True
        }
        
        # Generic app blueprint
        self.blueprints["generic"] = {
            "name": "generic",
            "description": "Generic Application Template",
            "type": "deployment",
            "image": "ubuntu:latest",
            "port": 8000,
            "replicas": 1,
            "service_type": "ClusterIP",
            "resources": {
                "cpu": "100m",
                "memory": "128Mi"
            },
            "health_check": False
        }
    
    def get_blueprint(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a blueprint by name."""
        return self.blueprints.get(name.lower())
    
    def list_blueprints(self) -> List[str]:
        """List all available blueprint names."""
        return list(self.blueprints.keys())
    
    def search_blueprints(self, keyword: str) -> List[Dict[str, Any]]:
        """Search blueprints by keyword in name or description."""
        keyword = keyword.lower()
        results = []
        
        for blueprint in self.blueprints.values():
            name = blueprint.get("name", "").lower()
            desc = blueprint.get("description", "").lower()
            
            if keyword in name or keyword in desc:
                results.append({
                    "name": blueprint["name"],
                    "description": blueprint.get("description", ""),
                    "type": blueprint.get("type", "deployment")
                })
        
        return results
    
    def create_custom_blueprint(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a custom blueprint."""
        blueprint = {
            "name": name,
            "description": config.get("description", f"{name} application"),
            "type": config.get("type", "deployment"),
            "image": config.get("image", f"{name}:latest"),
            "port": config.get("port", 8000),
            "replicas": config.get("replicas", 1),
            "service_type": config.get("service_type", "ClusterIP"),
            "env": config.get("env", {}),
            "secrets": config.get("secrets", {}),
            "storage": config.get("storage"),
            "resources": config.get("resources", {
                "cpu": "100m",
                "memory": "128Mi"
            }),
            "health_check": config.get("health_check", False)
        }
        
        self.blueprints[name.lower()] = blueprint
        return blueprint
    
    def merge_blueprints(self, *blueprint_names: str) -> Dict[str, Any]:
        """
        Merge multiple blueprints.
        Useful for combining app + database + proxy.
        """
        merged = {
            "components": [],
            "dependencies": [],
            "secrets": {},
            "env": {},
            "storage": None
        }
        
        for name in blueprint_names:
            blueprint = self.get_blueprint(name)
            if blueprint:
                merged["components"].append(blueprint)
                merged["dependencies"].append(name)
                
                # Merge secrets
                if blueprint.get("secrets"):
                    merged["secrets"].update(blueprint["secrets"])
                
                # Merge env
                if blueprint.get("env"):
                    merged["env"].update(blueprint["env"])
                
                # Take largest storage
                if blueprint.get("storage"):
                    if not merged["storage"]:
                        merged["storage"] = blueprint["storage"]
        
        return merged
