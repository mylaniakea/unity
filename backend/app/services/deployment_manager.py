"""
Deployment Manager Service

Unified deployment interface for both Kubernetes and Docker platforms.
Provides high-level deployment operations that abstract away platform differences.
"""

import logging
import asyncio
import subprocess
import json
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.services.k8s_client import KubernetesClient, KubernetesClientError

logger = logging.getLogger(__name__)


class DeploymentManagerError(Exception):
    """Base exception for deployment manager errors"""
    pass


class DeploymentManager:
    """
    Unified deployment manager for Kubernetes and Docker.

    Provides a consistent interface for deploying, updating, scaling, and removing
    applications across different platforms.
    """

    def __init__(self, db_session=None):
        """
        Initialize deployment manager.

        Args:
            db_session: SQLAlchemy database session for persistence
        """
        self.db = db_session
        self.logger = logger

    # ==================
    # Kubernetes Deployment Methods
    # ==================

    async def deploy_to_kubernetes(
        self,
        manifests: List[Dict[str, Any]],
        namespace: str = "default",
        cluster_id: Optional[int] = None,
        kubeconfig_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deploy resources to Kubernetes cluster.

        Args:
            manifests: List of Kubernetes manifest dictionaries
            namespace: Target namespace
            cluster_id: Database ID of cluster (used to lookup kubeconfig)
            kubeconfig_path: Path to kubeconfig file (overrides cluster_id)

        Returns:
            Dict with deployment result:
            {
                "success": bool,
                "deployed_resources": List[Dict],
                "errors": List[str],
                "namespace": str,
                "cluster": str
            }
        """
        self.logger.info(f"Deploying {len(manifests)} manifests to Kubernetes namespace '{namespace}'")

        try:
            # Get kubeconfig path from cluster if cluster_id provided
            if cluster_id and not kubeconfig_path and self.db:
                from app.models import KubernetesCluster
                cluster = self.db.query(KubernetesCluster).filter_by(id=cluster_id).first()
                if cluster and cluster.kubeconfig_data:
                    # Write kubeconfig to temp file
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                        f.write(cluster.kubeconfig_data)
                        kubeconfig_path = f.name

            # Initialize Kubernetes client
            k8s_client = KubernetesClient(kubeconfig_path=kubeconfig_path)
            await k8s_client.load_config()

            # Test connection
            if not await k8s_client.test_connection():
                raise DeploymentManagerError("Failed to connect to Kubernetes cluster")

            # Create namespace if it doesn't exist
            try:
                await k8s_client.create_namespace(namespace)
                self.logger.info(f"Created namespace: {namespace}")
            except Exception as e:
                # Namespace might already exist, that's ok
                self.logger.debug(f"Namespace creation note: {e}")

            deployed_resources = []
            errors = []

            # Apply each manifest
            for manifest in manifests:
                try:
                    result = await self._apply_k8s_manifest(k8s_client, manifest, namespace)
                    deployed_resources.append(result)
                    self.logger.info(
                        f"Applied {result['kind']}/{result['name']} to namespace {namespace}"
                    )
                except Exception as e:
                    error_msg = f"Failed to apply {manifest.get('kind', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            success = len(errors) == 0

            return {
                "success": success,
                "deployed_resources": deployed_resources,
                "errors": errors,
                "namespace": namespace,
                "cluster": kubeconfig_path or "default",
                "deployment_time": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Kubernetes deployment failed: {e}")
            return {
                "success": False,
                "deployed_resources": [],
                "errors": [str(e)],
                "namespace": namespace,
                "cluster": kubeconfig_path or "default"
            }

    async def _apply_k8s_manifest(
        self,
        k8s_client: KubernetesClient,
        manifest: Dict[str, Any],
        namespace: str
    ) -> Dict[str, Any]:
        """Apply a single Kubernetes manifest."""
        kind = manifest.get("kind", "Unknown")
        name = manifest.get("metadata", {}).get("name", "unknown")

        # Set namespace in metadata if not present
        if "metadata" not in manifest:
            manifest["metadata"] = {}
        if "namespace" not in manifest["metadata"]:
            manifest["metadata"]["namespace"] = namespace

        # Apply manifest using kubectl-style dynamic client
        result = await k8s_client.apply_manifest(manifest)

        return {
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "status": "created" if result.get("created") else "updated",
            "api_version": manifest.get("apiVersion", "unknown")
        }

    async def update_kubernetes_deployment(
        self,
        deployment_name: str,
        namespace: str,
        new_manifests: List[Dict[str, Any]],
        kubeconfig_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update existing Kubernetes deployment.

        This is essentially the same as deploy_to_kubernetes since kubectl apply
        handles both creation and updates.
        """
        return await self.deploy_to_kubernetes(
            manifests=new_manifests,
            namespace=namespace,
            kubeconfig_path=kubeconfig_path
        )

    async def scale_kubernetes_deployment(
        self,
        deployment_name: str,
        namespace: str,
        replicas: int,
        kubeconfig_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scale Kubernetes deployment.

        Args:
            deployment_name: Name of deployment to scale
            namespace: Namespace containing deployment
            replicas: Target replica count
            kubeconfig_path: Path to kubeconfig file

        Returns:
            Dict with scale result
        """
        self.logger.info(f"Scaling {deployment_name} in {namespace} to {replicas} replicas")

        try:
            k8s_client = KubernetesClient(kubeconfig_path=kubeconfig_path)
            await k8s_client.load_config()

            result = await k8s_client.scale_deployment(deployment_name, namespace, replicas)

            return {
                "success": True,
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas": replicas,
                "status": result
            }
        except Exception as e:
            self.logger.error(f"Failed to scale deployment: {e}")
            return {
                "success": False,
                "deployment": deployment_name,
                "namespace": namespace,
                "error": str(e)
            }

    async def remove_kubernetes_deployment(
        self,
        deployment_name: str,
        namespace: str,
        kubeconfig_path: Optional[str] = None,
        delete_namespace: bool = False
    ) -> Dict[str, Any]:
        """
        Remove Kubernetes deployment and associated resources.

        Args:
            deployment_name: Name of deployment to remove
            namespace: Namespace containing deployment
            kubeconfig_path: Path to kubeconfig file
            delete_namespace: If True, delete entire namespace

        Returns:
            Dict with removal result
        """
        self.logger.info(f"Removing deployment {deployment_name} from namespace {namespace}")

        try:
            k8s_client = KubernetesClient(kubeconfig_path=kubeconfig_path)
            await k8s_client.load_config()

            if delete_namespace:
                # Delete entire namespace
                result = await k8s_client.delete_namespace(namespace)
                return {
                    "success": True,
                    "action": "namespace_deleted",
                    "namespace": namespace,
                    "status": result
                }
            else:
                # Delete specific deployment
                result = await k8s_client.delete_deployment(deployment_name, namespace)
                return {
                    "success": True,
                    "action": "deployment_deleted",
                    "deployment": deployment_name,
                    "namespace": namespace,
                    "status": result
                }
        except Exception as e:
            self.logger.error(f"Failed to remove deployment: {e}")
            return {
                "success": False,
                "deployment": deployment_name,
                "namespace": namespace,
                "error": str(e)
            }

    async def get_kubernetes_deployment_status(
        self,
        deployment_name: str,
        namespace: str,
        kubeconfig_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get status of Kubernetes deployment.

        Returns:
            Dict with deployment status including replicas, conditions, etc.
        """
        try:
            k8s_client = KubernetesClient(kubeconfig_path=kubeconfig_path)
            await k8s_client.load_config()

            status = await k8s_client.get_deployment_status(deployment_name, namespace)

            return {
                "success": True,
                "deployment": deployment_name,
                "namespace": namespace,
                "status": status
            }
        except Exception as e:
            self.logger.error(f"Failed to get deployment status: {e}")
            return {
                "success": False,
                "deployment": deployment_name,
                "namespace": namespace,
                "error": str(e)
            }

    # ==================
    # Docker Deployment Methods
    # ==================

    async def deploy_to_docker(
        self,
        compose_content: str,
        project_name: str,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Deploy using Docker Compose.

        Args:
            compose_content: Docker Compose YAML content
            project_name: Docker Compose project name
            env_vars: Environment variables for compose

        Returns:
            Dict with deployment result
        """
        self.logger.info(f"Deploying Docker Compose project: {project_name}")

        try:
            # Write compose file to temp location
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(compose_content)
                compose_file = f.name

            # Build docker-compose command
            cmd = [
                "docker-compose",
                "-f", compose_file,
                "-p", project_name,
                "up", "-d"
            ]

            # Set environment variables
            env = env_vars.copy() if env_vars else {}

            # Execute docker-compose
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env}
            )

            stdout, stderr = await result.communicate()

            success = result.returncode == 0

            if success:
                # Get container status
                containers = await self._get_docker_containers(project_name)

                return {
                    "success": True,
                    "project": project_name,
                    "containers": containers,
                    "output": stdout.decode(),
                    "deployment_time": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "project": project_name,
                    "error": stderr.decode(),
                    "output": stdout.decode()
                }

        except Exception as e:
            self.logger.error(f"Docker deployment failed: {e}")
            return {
                "success": False,
                "project": project_name,
                "error": str(e)
            }

    async def update_docker_deployment(
        self,
        project_name: str,
        compose_content: str,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Update existing Docker Compose deployment.

        This recreates containers with new configuration.
        """
        return await self.deploy_to_docker(compose_content, project_name, env_vars)

    async def scale_docker_service(
        self,
        project_name: str,
        service_name: str,
        replicas: int
    ) -> Dict[str, Any]:
        """
        Scale Docker Compose service.

        Args:
            project_name: Docker Compose project name
            service_name: Service to scale
            replicas: Target replica count
        """
        self.logger.info(f"Scaling Docker service {service_name} to {replicas}")

        try:
            cmd = [
                "docker-compose",
                "-p", project_name,
                "up", "-d",
                "--scale", f"{service_name}={replicas}"
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            return {
                "success": result.returncode == 0,
                "project": project_name,
                "service": service_name,
                "replicas": replicas,
                "output": stdout.decode()
            }
        except Exception as e:
            self.logger.error(f"Failed to scale Docker service: {e}")
            return {
                "success": False,
                "project": project_name,
                "service": service_name,
                "error": str(e)
            }

    async def remove_docker_deployment(
        self,
        project_name: str,
        remove_volumes: bool = False
    ) -> Dict[str, Any]:
        """
        Remove Docker Compose deployment.

        Args:
            project_name: Docker Compose project name
            remove_volumes: If True, also remove volumes
        """
        self.logger.info(f"Removing Docker Compose project: {project_name}")

        try:
            cmd = ["docker-compose", "-p", project_name, "down"]
            if remove_volumes:
                cmd.append("-v")

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            return {
                "success": result.returncode == 0,
                "project": project_name,
                "action": "removed",
                "output": stdout.decode()
            }
        except Exception as e:
            self.logger.error(f"Failed to remove Docker deployment: {e}")
            return {
                "success": False,
                "project": project_name,
                "error": str(e)
            }

    async def get_docker_deployment_status(
        self,
        project_name: str
    ) -> Dict[str, Any]:
        """
        Get status of Docker Compose deployment.
        """
        try:
            containers = await self._get_docker_containers(project_name)

            return {
                "success": True,
                "project": project_name,
                "containers": containers,
                "running": sum(1 for c in containers if c["status"] == "running")
            }
        except Exception as e:
            self.logger.error(f"Failed to get Docker status: {e}")
            return {
                "success": False,
                "project": project_name,
                "error": str(e)
            }

    async def _get_docker_containers(self, project_name: str) -> List[Dict[str, Any]]:
        """Get list of containers for a Docker Compose project."""
        cmd = [
            "docker-compose",
            "-p", project_name,
            "ps", "--format", "json"
        ]

        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            return []

        # Parse JSON output
        try:
            containers = json.loads(stdout.decode())
            return containers if isinstance(containers, list) else [containers]
        except:
            return []

    # ==================
    # Platform-Agnostic Methods
    # ==================

    async def deploy(
        self,
        platform: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Platform-agnostic deployment method.

        Args:
            platform: "kubernetes" or "docker"
            config: Platform-specific configuration

        Returns:
            Dict with deployment result
        """
        if platform == "kubernetes":
            return await self.deploy_to_kubernetes(
                manifests=config.get("manifests", []),
                namespace=config.get("namespace", "default"),
                cluster_id=config.get("cluster_id"),
                kubeconfig_path=config.get("kubeconfig_path")
            )
        elif platform == "docker":
            return await self.deploy_to_docker(
                compose_content=config.get("compose_content", ""),
                project_name=config.get("project_name", ""),
                env_vars=config.get("env_vars", {})
            )
        else:
            raise DeploymentManagerError(f"Unsupported platform: {platform}")

    async def get_deployment_status(
        self,
        platform: str,
        deployment_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Platform-agnostic status check.

        Args:
            platform: "kubernetes" or "docker"
            deployment_id: Deployment identifier
            **kwargs: Platform-specific parameters
        """
        if platform == "kubernetes":
            return await self.get_kubernetes_deployment_status(
                deployment_name=deployment_id,
                namespace=kwargs.get("namespace", "default"),
                kubeconfig_path=kwargs.get("kubeconfig_path")
            )
        elif platform == "docker":
            return await self.get_docker_deployment_status(
                project_name=deployment_id
            )
        else:
            raise DeploymentManagerError(f"Unsupported platform: {platform}")


import os
