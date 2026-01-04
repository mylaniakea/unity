"""
Example usage of KubernetesClient service.

This file demonstrates how to use the k8s_client module in other Unity services.
"""

import asyncio
from typing import List, Dict, Any
from app.services.k8s_client import (
    KubernetesClient,
    create_k8s_client,
    KubernetesClientError
)


class KubernetesMonitoringService:
    """
    Example service that uses KubernetesClient to monitor cluster health.

    This demonstrates best practices for:
    - Using the k8s_client in a service class
    - Error handling
    - Async/await patterns
    - Logging
    """

    def __init__(self, kubeconfig_path: str = None, in_cluster: bool = False):
        """Initialize with optional kubeconfig or in-cluster auth"""
        self.client = create_k8s_client(
            kubeconfig_path=kubeconfig_path,
            in_cluster=in_cluster
        )

    async def get_cluster_health(self) -> Dict[str, Any]:
        """
        Get overall cluster health status.

        Returns:
            Dict with cluster health information
        """
        try:
            # Test connection
            conn_result = await self.client.test_connection()
            if not conn_result["success"]:
                return {
                    "healthy": False,
                    "error": conn_result.get("message", "Connection failed")
                }

            # Get namespaces
            namespaces = await self.client.list_namespaces()

            # Get version info
            version = await self.client.get_api_versions()

            return {
                "healthy": True,
                "cluster_version": version.get("git_version"),
                "namespace_count": len(namespaces),
                "namespaces": [ns["name"] for ns in namespaces]
            }

        except KubernetesClientError as e:
            return {
                "healthy": False,
                "error": str(e)
            }

    async def get_namespace_pod_count(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Get pod count for a namespace.

        Args:
            namespace: Namespace to query

        Returns:
            Dict with pod counts by status
        """
        try:
            pods = await self.client.list_pods(namespace=namespace)

            # Count by phase
            counts = {}
            for pod in pods:
                phase = pod["status"]["phase"]
                counts[phase] = counts.get(phase, 0) + 1

            return {
                "namespace": namespace,
                "total_pods": len(pods),
                "by_status": counts
            }

        except KubernetesClientError as e:
            return {
                "namespace": namespace,
                "error": str(e)
            }

    async def list_unhealthy_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Find pods that are not in Running state.

        Args:
            namespace: Namespace to query

        Returns:
            List of unhealthy pod details
        """
        try:
            pods = await self.client.list_pods(namespace=namespace)

            unhealthy = []
            for pod in pods:
                if pod["status"]["phase"] != "Running":
                    unhealthy.append({
                        "name": pod["name"],
                        "namespace": pod["namespace"],
                        "phase": pod["status"]["phase"],
                        "created_at": pod["created_at"]
                    })

            return unhealthy

        except KubernetesClientError as e:
            # Log error but return empty list
            print(f"Error listing pods: {e}")
            return []

    async def close(self):
        """Clean up resources"""
        await self.client.close()


async def example_basic_usage():
    """Example 1: Basic usage with default kubeconfig"""
    print("Example 1: Basic Usage")
    print("-" * 40)

    # Create client with default kubeconfig
    client = create_k8s_client()

    # Test connection
    result = await client.test_connection()
    if result["success"]:
        print(f"Connected! Cluster version: {result.get('cluster_version')}")

        # List namespaces
        namespaces = await client.list_namespaces()
        print(f"Found {len(namespaces)} namespaces")
    else:
        print(f"Connection failed: {result.get('error')}")

    # Clean up
    await client.close()


async def example_with_context_manager():
    """Example 2: Using async context manager"""
    print("\nExample 2: Async Context Manager")
    print("-" * 40)

    async with create_k8s_client() as client:
        # Client automatically cleaned up when exiting context
        result = await client.test_connection()
        print(f"Connection: {'✓' if result['success'] else '✗'}")


async def example_in_cluster():
    """Example 3: Using in-cluster authentication"""
    print("\nExample 3: In-Cluster Authentication")
    print("-" * 40)

    try:
        # When running inside a Kubernetes pod
        client = create_k8s_client(in_cluster=True)
        result = await client.test_connection()

        if result["success"]:
            print("Connected using in-cluster authentication")
        else:
            print("In-cluster auth not available (not running in K8s)")

        await client.close()

    except Exception as e:
        print(f"Not running in cluster: {e}")


async def example_custom_service():
    """Example 4: Using client in a custom service"""
    print("\nExample 4: Custom Service")
    print("-" * 40)

    service = KubernetesMonitoringService()

    # Get cluster health
    health = await service.get_cluster_health()
    print(f"Cluster healthy: {health.get('healthy')}")

    if health.get("healthy"):
        # Get pod counts
        pod_counts = await service.get_namespace_pod_count("default")
        print(f"Pods in default namespace: {pod_counts.get('total_pods')}")

        # Find unhealthy pods
        unhealthy = await service.list_unhealthy_pods("default")
        if unhealthy:
            print(f"Found {len(unhealthy)} unhealthy pods")
        else:
            print("All pods are healthy")

    await service.close()


async def example_error_handling():
    """Example 5: Proper error handling"""
    print("\nExample 5: Error Handling")
    print("-" * 40)

    client = create_k8s_client()

    try:
        # Try to get a namespace that might not exist
        ns = await client.get_namespace("non-existent-namespace")
        if ns:
            print(f"Found namespace: {ns['name']}")
        else:
            print("Namespace not found (returns None, not an error)")

    except KubernetesClientError as e:
        # Handle specific Kubernetes errors
        print(f"Kubernetes error: {e}")

    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error: {e}")

    finally:
        # Always clean up
        await client.close()


async def main():
    """Run all examples"""
    print("=" * 60)
    print("KubernetesClient Usage Examples")
    print("=" * 60)

    # Run examples
    await example_basic_usage()
    await example_with_context_manager()
    await example_in_cluster()
    await example_custom_service()
    await example_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
