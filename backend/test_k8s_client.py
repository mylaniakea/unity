"""
Test script for KubernetesClient service.

This demonstrates the basic functionality of the k8s_client module.
Run with: python test_k8s_client.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.k8s_client import (
    KubernetesClient,
    create_k8s_client,
    KubernetesClientError,
    KUBERNETES_AVAILABLE
)


async def test_client_initialization():
    """Test that we can initialize the client"""
    print("=" * 60)
    print("Test 1: Client Initialization")
    print("=" * 60)

    if not KUBERNETES_AVAILABLE:
        print("❌ Kubernetes library not available")
        print("   Install with: pip install kubernetes pyyaml")
        return False

    print("✓ Kubernetes library is available")

    try:
        # Test with default kubeconfig
        client = create_k8s_client()
        print("✓ Client created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return False


async def test_connection():
    """Test connection to cluster (if available)"""
    print("\n" + "=" * 60)
    print("Test 2: Connection Test")
    print("=" * 60)

    try:
        client = create_k8s_client()
        result = await client.test_connection()

        if result["success"]:
            print(f"✓ Connected to Kubernetes cluster")
            print(f"  Cluster version: {result.get('cluster_version', 'unknown')}")

            # Print API versions
            if "api_versions" in result:
                api_info = result["api_versions"]
                print(f"  Platform: {api_info.get('platform', 'unknown')}")
                print(f"  Go version: {api_info.get('go_version', 'unknown')}")

            return True
        else:
            print(f"❌ Connection failed: {result.get('message', 'unknown error')}")
            if "error" in result:
                print(f"   Error: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Connection test failed with exception: {e}")
        return False


async def test_list_namespaces():
    """Test listing namespaces"""
    print("\n" + "=" * 60)
    print("Test 3: List Namespaces")
    print("=" * 60)

    try:
        client = create_k8s_client()

        # First test connection
        conn_result = await client.test_connection()
        if not conn_result["success"]:
            print("⚠️  Skipping: Not connected to cluster")
            return False

        # List namespaces
        namespaces = await client.list_namespaces()
        print(f"✓ Found {len(namespaces)} namespaces:")

        for ns in namespaces[:5]:  # Show first 5
            print(f"  - {ns['name']} (status: {ns['status']})")

        if len(namespaces) > 5:
            print(f"  ... and {len(namespaces) - 5} more")

        return True

    except KubernetesClientError as e:
        print(f"❌ Failed to list namespaces: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_get_api_versions():
    """Test getting API versions"""
    print("\n" + "=" * 60)
    print("Test 4: Get API Versions")
    print("=" * 60)

    try:
        client = create_k8s_client()

        # First test connection
        conn_result = await client.test_connection()
        if not conn_result["success"]:
            print("⚠️  Skipping: Not connected to cluster")
            return False

        # Get API versions
        version_info = await client.get_api_versions()
        print(f"✓ Retrieved API version information:")
        print(f"  Git Version: {version_info.get('git_version', 'unknown')}")
        print(f"  Major: {version_info.get('major', 'unknown')}")
        print(f"  Minor: {version_info.get('minor', 'unknown')}")
        print(f"  Build Date: {version_info.get('build_date', 'unknown')}")

        return True

    except KubernetesClientError as e:
        print(f"❌ Failed to get API versions: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_context_manager():
    """Test async context manager"""
    print("\n" + "=" * 60)
    print("Test 5: Async Context Manager")
    print("=" * 60)

    try:
        async with create_k8s_client() as client:
            print("✓ Client created with async context manager")

            # Try a simple operation
            conn_result = await client.test_connection()
            if conn_result["success"]:
                print("✓ Can perform operations within context")

        print("✓ Context manager cleanup completed")
        return True

    except Exception as e:
        print(f"❌ Context manager test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Kubernetes Client Service Test Suite")
    print("=" * 60 + "\n")

    results = []

    # Test 1: Initialization
    results.append(("Initialization", await test_client_initialization()))

    # Test 2: Connection (requires cluster)
    results.append(("Connection", await test_connection()))

    # Test 3: List namespaces (requires cluster)
    results.append(("List Namespaces", await test_list_namespaces()))

    # Test 4: Get API versions (requires cluster)
    results.append(("Get API Versions", await test_get_api_versions()))

    # Test 5: Context manager
    results.append(("Context Manager", await test_context_manager()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        print("\nNote: Some tests require a Kubernetes cluster to be available.")
        print("If you don't have a cluster, the client will still initialize correctly.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
