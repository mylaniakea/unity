"""
Manifest Generator

Generates platform-specific deployment manifests from blueprints.
Handles auto-wiring of dependencies and configuration.
"""

import logging
import yaml
import copy
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """
    Generates Kubernetes manifests or Docker Compose files from blueprints.

    Handles:
    - Variable substitution
    - Auto-wiring dependencies
    - Platform-specific transformations
    """

    def __init__(self):
        self.logger = logger

    def generate(
        self,
        blueprint: Dict[str, Any],
        config: Dict[str, Any],
        platform: str = "kubernetes"
    ) -> List[Dict[str, Any]]:
        """
        Generate deployment manifests from blueprint.

        Args:
            blueprint: Application blueprint
            config: Configuration parameters
            platform: Target platform (kubernetes or docker)

        Returns:
            List of manifest dictionaries
        """
        try:
            # Merge defaults with config
            full_config = {**blueprint.get("defaults", {}), **config}

            # Get template
            template = blueprint.get("template", {})

            if platform == "kubernetes":
                return self._generate_k8s_manifests(blueprint, template, full_config)
            elif platform == "docker":
                return self._generate_docker_manifests(blueprint, template, full_config)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

        except Exception as e:
            self.logger.error(f"Failed to generate manifests: {e}")
            raise

    def _generate_k8s_manifests(
        self,
        blueprint: Dict[str, Any],
        template: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate Kubernetes manifests."""
        manifests = []

        # Apply variable substitution
        manifest = self._substitute_variables(copy.deepcopy(template), config)

        # If template is a list, expand it
        if isinstance(manifest, list):
            manifests.extend(manifest)
        else:
            manifests.append(manifest)

        # Generate additional resources based on config
        app_name = blueprint.get("name")

        # Add Service if not present and ports are defined
        if config.get("service_enabled", True) and blueprint.get("ports"):
            if not any(m.get("kind") == "Service" for m in manifests):
                service = self._generate_k8s_service(app_name, blueprint, config)
                manifests.append(service)

        # Add Ingress if enabled
        if config.get("ingress_enabled", False):
            ingress = self._generate_k8s_ingress(app_name, config)
            manifests.append(ingress)

        # Add PersistentVolumeClaim if volumes defined
        if blueprint.get("volumes"):
            for volume in blueprint.get("volumes", []):
                pvc = self._generate_k8s_pvc(app_name, volume, config)
                manifests.append(pvc)

        return manifests

    def _generate_docker_manifests(
        self,
        blueprint: Dict[str, Any],
        template: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate Docker Compose manifests."""
        # For Docker, we generate a single compose service definition
        service = self._substitute_variables(copy.deepcopy(template), config)

        return [service]

    def _substitute_variables(self, obj: Any, config: Dict[str, Any]) -> Any:
        """
        Recursively substitute variables in object.

        Variables format: ${VAR_NAME} or {{VAR_NAME}}
        """
        if isinstance(obj, dict):
            return {k: self._substitute_variables(v, config) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_variables(item, config) for item in obj]
        elif isinstance(obj, str):
            # Replace ${VAR} and {{VAR}} patterns
            import re
            
            def replacer(match):
                var_name = match.group(1)
                return str(config.get(var_name, match.group(0)))
            
            result = re.sub(r'\$\{([^}]+)\}', replacer, obj)
            result = re.sub(r'\{\{([^}]+)\}\}', replacer, result)
            return result
        else:
            return obj

    def _generate_k8s_service(
        self,
        app_name: str,
        blueprint: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Kubernetes Service manifest."""
        ports = []
        for port_def in blueprint.get("ports", []):
            ports.append({
                "name": port_def.get("name", f"port-{port_def['port']}"),
                "port": port_def.get("port"),
                "targetPort": port_def.get("targetPort", port_def.get("port")),
                "protocol": port_def.get("protocol", "TCP")
            })

        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": app_name,
                "namespace": config.get("namespace", "default")
            },
            "spec": {
                "selector": {
                    "app": app_name
                },
                "ports": ports,
                "type": config.get("service_type", "ClusterIP")
            }
        }

    def _generate_k8s_ingress(
        self,
        app_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Kubernetes Ingress manifest."""
        domain = config.get("domain", f"{app_name}.local")
        
        ingress = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{app_name}-ingress",
                "namespace": config.get("namespace", "default"),
                "annotations": {}
            },
            "spec": {
                "rules": [
                    {
                        "host": domain,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": app_name,
                                            "port": {
                                                "number": config.get("port", 80)
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

        # Add TLS if enabled
        if config.get("tls_enabled", False):
            ingress["spec"]["tls"] = [
                {
                    "hosts": [domain],
                    "secretName": f"{app_name}-tls"
                }
            ]
            ingress["metadata"]["annotations"]["cert-manager.io/cluster-issuer"] = config.get(
                "cert_issuer", "letsencrypt-prod"
            )

        return ingress

    def _generate_k8s_pvc(
        self,
        app_name: str,
        volume: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Kubernetes PersistentVolumeClaim manifest."""
        volume_name = volume.get("name", "data")
        size = config.get("storage_size", volume.get("size", "10Gi"))

        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{app_name}-{volume_name}",
                "namespace": config.get("namespace", "default")
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": size
                    }
                },
                "storageClassName": config.get("storage_class", "standard")
            }
        }

    def convert_to_compose(self, manifests: List[Dict[str, Any]]) -> str:
        """
        Convert Kubernetes manifests to Docker Compose format.

        Args:
            manifests: List of Kubernetes manifest dictionaries

        Returns:
            Docker Compose YAML string
        """
        compose = {
            "version": "3.8",
            "services": {},
            "volumes": {},
            "networks": {
                "default": {
                    "driver": "bridge"
                }
            }
        }

        for manifest in manifests:
            kind = manifest.get("kind")
            
            if kind == "Deployment":
                service_name = manifest["metadata"]["name"]
                spec = manifest["spec"]["template"]["spec"]
                
                # Extract container info
                container = spec["containers"][0]
                
                compose["services"][service_name] = {
                    "image": container["image"],
                    "container_name": service_name,
                    "restart": "unless-stopped"
                }

                # Add ports
                if "ports" in container:
                    compose["services"][service_name]["ports"] = [
                        f"{p['containerPort']}:{p['containerPort']}"
                        for p in container["ports"]
                    ]

                # Add environment
                if "env" in container:
                    compose["services"][service_name]["environment"] = {
                        e["name"]: e["value"]
                        for e in container["env"]
                        if "value" in e
                    }

                # Add volumes
                if "volumeMounts" in container:
                    volumes = []
                    for vm in container["volumeMounts"]:
                        volume_name = vm["name"]
                        compose["volumes"][volume_name] = {}
                        volumes.append(f"{volume_name}:{vm['mountPath']}")
                    compose["services"][service_name]["volumes"] = volumes

        return yaml.dump(compose, default_flow_style=False)
