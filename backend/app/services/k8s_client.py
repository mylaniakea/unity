"""
Kubernetes Client Service

A thin wrapper around the official Kubernetes Python client library that provides:
- Support for both kubeconfig file and in-cluster authentication
- Async-compatible methods where possible
- Proper error handling and connection testing
- Logging for debugging and monitoring

This service is designed to be used by other services that need to interact
with Kubernetes clusters (e.g., orchestration, deployment management).
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from contextlib import asynccontextmanager
import asyncio

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    # Create dummy types for type hints when kubernetes not installed
    if TYPE_CHECKING:
        from kubernetes import client
    else:
        client = None

logger = logging.getLogger(__name__)


class KubernetesClientError(Exception):
    """Base exception for Kubernetes client errors"""
    pass


class KubernetesConnectionError(KubernetesClientError):
    """Raised when connection to Kubernetes cluster fails"""
    pass


class KubernetesAuthenticationError(KubernetesClientError):
    """Raised when authentication to Kubernetes cluster fails"""
    pass


class KubernetesClient:
    """
    Thin wrapper around kubernetes.client that handles authentication,
    connection management, and provides common operations.

    Usage:
        # Using kubeconfig file
        k8s_client = KubernetesClient(kubeconfig_path="/path/to/kubeconfig")

        # Using in-cluster authentication (when running inside K8s)
        k8s_client = KubernetesClient(in_cluster=True)

        # Test connection
        if await k8s_client.test_connection():
            namespaces = await k8s_client.list_namespaces()
    """

    def __init__(
        self,
        kubeconfig_path: Optional[str] = None,
        context: Optional[str] = None,
        in_cluster: bool = False
    ):
        """
        Initialize Kubernetes client.

        Args:
            kubeconfig_path: Path to kubeconfig file. If None, uses default locations.
            context: Specific context to use from kubeconfig. If None, uses current context.
            in_cluster: If True, use in-cluster authentication (ignores kubeconfig_path).

        Raises:
            KubernetesClientError: If kubernetes library is not available
        """
        if not KUBERNETES_AVAILABLE:
            raise KubernetesClientError(
                "kubernetes library not available. Install with: pip install kubernetes"
            )

        self.kubeconfig_path = kubeconfig_path
        self.context = context
        self.in_cluster = in_cluster
        self._api_client: Optional[client.ApiClient] = None
        self._loaded = False

        logger.info(
            f"Initializing KubernetesClient (in_cluster={in_cluster}, "
            f"kubeconfig={kubeconfig_path}, context={context})"
        )

    def _load_config(self) -> None:
        """
        Load Kubernetes configuration.

        Raises:
            KubernetesAuthenticationError: If authentication fails
            KubernetesConnectionError: If connection fails
        """
        if self._loaded:
            return

        try:
            if self.in_cluster:
                logger.info("Loading in-cluster Kubernetes configuration")
                config.load_incluster_config()
            else:
                logger.info(f"Loading kubeconfig from: {self.kubeconfig_path or 'default locations'}")
                config.load_kube_config(
                    config_file=self.kubeconfig_path,
                    context=self.context
                )

            self._loaded = True
            logger.info("Kubernetes configuration loaded successfully")

        except config.ConfigException as e:
            logger.error(f"Failed to load Kubernetes configuration: {e}")
            raise KubernetesAuthenticationError(
                f"Failed to load Kubernetes configuration: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error loading Kubernetes configuration: {e}")
            raise KubernetesConnectionError(
                f"Failed to connect to Kubernetes cluster: {e}"
            ) from e

    def get_client(self) -> "client.ApiClient":
        """
        Get the underlying Kubernetes API client.

        Returns:
            kubernetes.client.ApiClient instance

        Raises:
            KubernetesAuthenticationError: If authentication fails
        """
        if not self._loaded:
            self._load_config()

        if self._api_client is None:
            self._api_client = client.ApiClient()

        return self._api_client

    def get_core_v1_api(self) -> "client.CoreV1Api":
        """
        Get CoreV1Api client for core Kubernetes resources.

        Returns:
            kubernetes.client.CoreV1Api instance
        """
        self.get_client()
        return client.CoreV1Api()

    def get_apps_v1_api(self) -> "client.AppsV1Api":
        """
        Get AppsV1Api client for apps (Deployments, StatefulSets, etc.).

        Returns:
            kubernetes.client.AppsV1Api instance
        """
        self.get_client()
        return client.AppsV1Api()

    def get_batch_v1_api(self) -> "client.BatchV1Api":
        """
        Get BatchV1Api client for Jobs and CronJobs.

        Returns:
            kubernetes.client.BatchV1Api instance
        """
        self.get_client()
        return client.BatchV1Api()

    def get_networking_v1_api(self) -> "client.NetworkingV1Api":
        """
        Get NetworkingV1Api client for Ingresses and NetworkPolicies.

        Returns:
            kubernetes.client.NetworkingV1Api instance
        """
        self.get_client()
        return client.NetworkingV1Api()

    def get_rbac_authorization_v1_api(self) -> "client.RbacAuthorizationV1Api":
        """
        Get RbacAuthorizationV1Api client for RBAC resources.

        Returns:
            kubernetes.client.RbacAuthorizationV1Api instance
        """
        self.get_client()
        return client.RbacAuthorizationV1Api()

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Kubernetes cluster.

        Returns:
            Dict with connection test results:
            {
                "success": bool,
                "message": str,
                "cluster_version": str (if successful),
                "error": str (if failed)
            }
        """
        try:
            # Load config
            self._load_config()

            # Try to get cluster version as a connection test
            version_info = await self.get_api_versions()

            return {
                "success": True,
                "message": "Successfully connected to Kubernetes cluster",
                "cluster_version": version_info.get("git_version", "unknown"),
                "api_versions": version_info
            }

        except KubernetesAuthenticationError as e:
            logger.error(f"Kubernetes authentication failed: {e}")
            return {
                "success": False,
                "message": "Authentication failed",
                "error": str(e)
            }

        except KubernetesConnectionError as e:
            logger.error(f"Kubernetes connection failed: {e}")
            return {
                "success": False,
                "message": "Connection failed",
                "error": str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error testing Kubernetes connection: {e}")
            return {
                "success": False,
                "message": "Unexpected error",
                "error": str(e)
            }

    async def list_namespaces(self, label_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all namespaces in the cluster.

        Args:
            label_selector: Optional label selector to filter namespaces (e.g., "env=prod")

        Returns:
            List of namespace dictionaries with name, labels, creation time, status

        Raises:
            KubernetesClientError: If request fails
        """
        try:
            api = self.get_core_v1_api()

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            namespaces = await loop.run_in_executor(
                None,
                lambda: api.list_namespace(label_selector=label_selector)
            )

            result = []
            for ns in namespaces.items:
                result.append({
                    "name": ns.metadata.name,
                    "labels": ns.metadata.labels or {},
                    "annotations": ns.metadata.annotations or {},
                    "created_at": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None,
                    "status": ns.status.phase if ns.status else "Unknown",
                    "uid": ns.metadata.uid
                })

            logger.info(f"Listed {len(result)} namespaces")
            return result

        except ApiException as e:
            logger.error(f"Kubernetes API error listing namespaces: {e}")
            raise KubernetesClientError(
                f"Failed to list namespaces: {e.reason} (status={e.status})"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error listing namespaces: {e}")
            raise KubernetesClientError(f"Failed to list namespaces: {e}") from e

    async def get_api_versions(self) -> Dict[str, Any]:
        """
        Get Kubernetes API server version information.

        Returns:
            Dict with version information including:
            - major: Major version number
            - minor: Minor version number
            - git_version: Full version string (e.g., "v1.28.0")
            - platform: Platform information
            - build_date: Build timestamp

        Raises:
            KubernetesClientError: If request fails
        """
        try:
            version_api = client.VersionApi()

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            version_info = await loop.run_in_executor(
                None,
                version_api.get_code
            )

            result = {
                "major": version_info.major,
                "minor": version_info.minor,
                "git_version": version_info.git_version,
                "git_commit": version_info.git_commit,
                "build_date": version_info.build_date,
                "platform": version_info.platform,
                "compiler": version_info.compiler,
                "go_version": version_info.go_version
            }

            logger.info(f"Kubernetes cluster version: {version_info.git_version}")
            return result

        except ApiException as e:
            logger.error(f"Kubernetes API error getting version: {e}")
            raise KubernetesClientError(
                f"Failed to get API versions: {e.reason} (status={e.status})"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error getting API versions: {e}")
            raise KubernetesClientError(f"Failed to get API versions: {e}") from e

    async def get_namespace(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific namespace.

        Args:
            name: Namespace name

        Returns:
            Namespace dictionary or None if not found

        Raises:
            KubernetesClientError: If request fails (except 404)
        """
        try:
            api = self.get_core_v1_api()

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            ns = await loop.run_in_executor(
                None,
                lambda: api.read_namespace(name=name)
            )

            return {
                "name": ns.metadata.name,
                "labels": ns.metadata.labels or {},
                "annotations": ns.metadata.annotations or {},
                "created_at": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None,
                "status": ns.status.phase if ns.status else "Unknown",
                "uid": ns.metadata.uid
            }

        except ApiException as e:
            if e.status == 404:
                logger.debug(f"Namespace not found: {name}")
                return None
            logger.error(f"Kubernetes API error getting namespace {name}: {e}")
            raise KubernetesClientError(
                f"Failed to get namespace {name}: {e.reason} (status={e.status})"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error getting namespace {name}: {e}")
            raise KubernetesClientError(f"Failed to get namespace {name}: {e}") from e

    async def list_pods(
        self,
        namespace: str = "default",
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List pods in a namespace.

        Args:
            namespace: Namespace to query (default: "default")
            label_selector: Label selector to filter pods (e.g., "app=nginx")
            field_selector: Field selector to filter pods (e.g., "status.phase=Running")

        Returns:
            List of pod dictionaries with name, status, containers, etc.

        Raises:
            KubernetesClientError: If request fails
        """
        try:
            api = self.get_core_v1_api()

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            pods = await loop.run_in_executor(
                None,
                lambda: api.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector
                )
            )

            result = []
            for pod in pods.items:
                # Extract container statuses
                container_statuses = []
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        container_statuses.append({
                            "name": cs.name,
                            "ready": cs.ready,
                            "restart_count": cs.restart_count,
                            "image": cs.image,
                            "state": self._get_container_state(cs.state)
                        })

                result.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "labels": pod.metadata.labels or {},
                    "annotations": pod.metadata.annotations or {},
                    "created_at": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                    "status": {
                        "phase": pod.status.phase,
                        "conditions": [
                            {"type": c.type, "status": c.status, "reason": c.reason}
                            for c in (pod.status.conditions or [])
                        ],
                        "container_statuses": container_statuses,
                        "host_ip": pod.status.host_ip,
                        "pod_ip": pod.status.pod_ip
                    },
                    "uid": pod.metadata.uid
                })

            logger.info(f"Listed {len(result)} pods in namespace {namespace}")
            return result

        except ApiException as e:
            logger.error(f"Kubernetes API error listing pods in {namespace}: {e}")
            raise KubernetesClientError(
                f"Failed to list pods in {namespace}: {e.reason} (status={e.status})"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error listing pods in {namespace}: {e}")
            raise KubernetesClientError(f"Failed to list pods in {namespace}: {e}") from e

    def _get_container_state(self, state) -> str:
        """Extract container state as string"""
        if state.running:
            return "running"
        elif state.waiting:
            return f"waiting ({state.waiting.reason})"
        elif state.terminated:
            return f"terminated ({state.terminated.reason})"
        return "unknown"

    async def close(self) -> None:
        """
        Close the API client and clean up resources.
        """
        if self._api_client:
            try:
                # The Python kubernetes client doesn't have an explicit close method
                # but we can clean up our reference
                self._api_client = None
                self._loaded = False
                logger.info("Kubernetes client closed")
            except Exception as e:
                logger.error(f"Error closing Kubernetes client: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - note: this is sync, use async context manager for proper cleanup"""
        # Synchronous cleanup - limited
        self._api_client = None
        self._loaded = False
        return False

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        return False


# Convenience function for quick client creation
def create_k8s_client(
    kubeconfig_path: Optional[str] = None,
    context: Optional[str] = None,
    in_cluster: bool = False
) -> KubernetesClient:
    """
    Factory function to create a KubernetesClient instance.

    Args:
        kubeconfig_path: Path to kubeconfig file. If None, uses default locations.
        context: Specific context to use from kubeconfig. If None, uses current context.
        in_cluster: If True, use in-cluster authentication.

    Returns:
        Configured KubernetesClient instance

    Example:
        client = create_k8s_client(kubeconfig_path="~/.kube/config")
        if await client.test_connection():
            namespaces = await client.list_namespaces()
    """
    return KubernetesClient(
        kubeconfig_path=kubeconfig_path,
        context=context,
        in_cluster=in_cluster
    )
