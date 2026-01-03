"""
Manifest Generator - Creates Kubernetes manifests from blueprints and parameters.
"""
import logging
import json
import yaml
from typing import Dict, List, Any, Optional
from jinja2 import Template, TemplateError
import secrets
import string

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """Generates Kubernetes manifests from templates."""
    
    def __init__(self):
        """Initialize manifest generator."""
        self.generated_manifests = []
    
    def generate_from_blueprint(
        self,
        blueprint: Dict[str, Any],
        namespace: str = "homelab",
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete Kubernetes manifests from a blueprint.
        
        Args:
            blueprint: Blueprint definition with app config
            namespace: Target namespace
            overrides: Parameter overrides
        
        Returns:
            Dict with generated manifests and metadata
        """
        overrides = overrides or {}
        manifests = []
        
        # Generate secrets first (if needed)
        if blueprint.get("secrets"):
            secret_manifest = self._generate_secret(
                blueprint["name"],
                blueprint.get("secrets", {}),
                namespace
            )
            manifests.append(secret_manifest)
        
        # Generate ConfigMap if needed
        if blueprint.get("config"):
            config_manifest = self._generate_configmap(
                blueprint["name"],
                blueprint.get("config", {}),
                namespace
            )
            manifests.append(config_manifest)
        
        # Generate PVC if storage needed
        if blueprint.get("storage"):
            pvc_manifest = self._generate_pvc(
                blueprint["name"],
                blueprint.get("storage", {}),
                namespace
            )
            manifests.append(pvc_manifest)
        
        # Generate Deployment or StatefulSet
        if blueprint.get("type") == "statefulset":
            app_manifest = self._generate_statefulset(blueprint, namespace, overrides)
        else:
            app_manifest = self._generate_deployment(blueprint, namespace, overrides)
        manifests.append(app_manifest)
        
        # Generate Service
        service_manifest = self._generate_service(blueprint, namespace)
        manifests.append(service_manifest)
        
        # Generate Ingress if specified
        if blueprint.get("ingress"):
            ingress_manifest = self._generate_ingress(blueprint, namespace)
            manifests.append(ingress_manifest)
        
        self.generated_manifests = manifests
        
        return {
            "app": blueprint["name"],
            "manifests": manifests,
            "count": len(manifests),
            "namespace": namespace,
            "valid": True
        }
    
    def _generate_secret(
        self,
        app_name: str,
        secrets_config: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """Generate Kubernetes Secret."""
        data = {}
        
        for key, value in secrets_config.items():
            if value == "auto-generate":
                # Generate secure random password
                data[key] = self._generate_password()
            else:
                data[key] = value
        
        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": f"{app_name}-secrets",
                "namespace": namespace
            },
            "type": "Opaque",
            "stringData": data
        }
    
    def _generate_configmap(
        self,
        app_name: str,
        config: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """Generate Kubernetes ConfigMap."""
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{app_name}-config",
                "namespace": namespace
            },
            "data": config
        }
    
    def _generate_pvc(
        self,
        app_name: str,
        storage_config: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """Generate Kubernetes PersistentVolumeClaim."""
        size = storage_config.get("size", "20Gi")
        storage_class = storage_config.get("storage_class", "local-path")
        
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{app_name}-pvc",
                "namespace": namespace
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": storage_class,
                "resources": {
                    "requests": {
                        "storage": size
                    }
                }
            }
        }
    
    def _generate_deployment(
        self,
        blueprint: Dict[str, Any],
        namespace: str,
        overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Kubernetes Deployment."""
        app_name = blueprint["name"]
        image = blueprint.get("image", f"{app_name}:latest")
        
        # Build environment variables
        env = []
        for key, value in blueprint.get("env", {}).items():
            if isinstance(value, str) and value.startswith("secret:"):
                # Reference from secret
                secret_key = value.replace("secret:", "")
                env.append({
                    "name": key,
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": f"{app_name}-secrets",
                            "key": secret_key
                        }
                    }
                })
            elif isinstance(value, str) and value.startswith("configmap:"):
                # Reference from configmap
                config_key = value.replace("configmap:", "")
                env.append({
                    "name": key,
                    "valueFrom": {
                        "configMapKeyRef": {
                            "name": f"{app_name}-config",
                            "key": config_key
                        }
                    }
                })
            else:
                env.append({
                    "name": key,
                    "value": str(value)
                })
        
        # Build volume mounts
        volume_mounts = []
        volumes = []
        
        if blueprint.get("storage"):
            volume_mounts.append({
                "name": "data",
                "mountPath": blueprint.get("storage", {}).get("mount_path", "/data")
            })
            volumes.append({
                "name": "data",
                "persistentVolumeClaim": {
                    "claimName": f"{app_name}-pvc"
                }
            })
        
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": app_name,
                "namespace": namespace,
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "replicas": blueprint.get("replicas", 1),
                "selector": {
                    "matchLabels": {
                        "app": app_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": app_name
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": app_name,
                                "image": image,
                                "imagePullPolicy": blueprint.get("imagePullPolicy", "IfNotPresent"),
                                "ports": [
                                    {
                                        "containerPort": blueprint.get("port", 8000),
                                        "name": "http"
                                    }
                                ],
                                "env": env,
                                "volumeMounts": volume_mounts,
                                "resources": {
                                    "requests": {
                                        "cpu": blueprint.get("resources", {}).get("cpu", "100m"),
                                        "memory": blueprint.get("resources", {}).get("memory", "128Mi")
                                    }
                                },
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": "http"
                                    },
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10
                                } if blueprint.get("health_check") else None,
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": "http"
                                    },
                                    "initialDelaySeconds": 10,
                                    "periodSeconds": 5
                                } if blueprint.get("health_check") else None
                            }
                        ],
                        "volumes": volumes
                    }
                }
            }
        }
    
    def _generate_statefulset(
        self,
        blueprint: Dict[str, Any],
        namespace: str,
        overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Kubernetes StatefulSet."""
        deployment = self._generate_deployment(blueprint, namespace, overrides)
        deployment["kind"] = "StatefulSet"
        deployment["spec"]["serviceName"] = f"{blueprint['name']}-service"
        return deployment
    
    def _generate_service(
        self,
        blueprint: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """Generate Kubernetes Service."""
        app_name = blueprint["name"]
        service_type = blueprint.get("service_type", "ClusterIP")
        port = blueprint.get("port", 8000)
        
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{app_name}-service",
                "namespace": namespace,
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "type": service_type,
                "selector": {
                    "app": app_name
                },
                "ports": [
                    {
                        "port": port,
                        "targetPort": "http",
                        "protocol": "TCP",
                        "name": "http"
                    }
                ]
            }
        }
    
    def _generate_ingress(
        self,
        blueprint: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """Generate Kubernetes Ingress."""
        app_name = blueprint["name"]
        ingress_config = blueprint.get("ingress", {})
        host = ingress_config.get("host", f"{app_name}.local")
        
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{app_name}-ingress",
                "namespace": namespace,
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "rules": [
                    {
                        "host": host,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": f"{app_name}-service",
                                            "port": {
                                                "number": blueprint.get("port", 8000)
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
    
    def validate_manifests(self) -> Dict[str, Any]:
        """Validate generated manifests."""
        errors = []
        
        for manifest in self.generated_manifests:
            if not manifest.get("apiVersion"):
                errors.append(f"Missing apiVersion in {manifest.get('kind', 'Unknown')}")
            if not manifest.get("kind"):
                errors.append("Missing kind")
            if not manifest.get("metadata", {}).get("name"):
                errors.append(f"Missing metadata.name in {manifest.get('kind', 'Unknown')}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "manifest_count": len(self.generated_manifests)
        }
    
    def to_yaml(self) -> str:
        """Export manifests as YAML."""
        return "---\n".join([
            yaml.dump(manifest, default_flow_style=False)
            for manifest in self.generated_manifests
        ])
    
    @staticmethod
    def _generate_password(length: int = 32) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
