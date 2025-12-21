"""
Performance tests for Unity API (Run 5).

Tests response times, load handling, and throughput.
"""
import pytest
import time
import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"


@pytest.mark.slow
def test_api_response_time_health():
    """Test health endpoint response time."""
    times = []
    for _ in range(10):
        start = time.time()
        response = httpx.get(f"{BASE_URL}/health")
        elapsed = (time.time() - start) * 1000  # Convert to ms
        times.append(elapsed)
        assert response.status_code == 200
    
    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]
    
    print(f"\n  Average: {avg_time:.2f}ms")
    print(f"  P95: {p95_time:.2f}ms")
    
    # Performance targets
    assert avg_time < 100, f"Average response time {avg_time}ms exceeds 100ms"
    assert p95_time < 200, f"P95 response time {p95_time}ms exceeds 200ms"


@pytest.mark.slow
def test_api_response_time_plugins_list():
    """Test plugins list endpoint response time."""
    times = []
    for _ in range(10):
        start = time.time()
        response = httpx.get(f"{BASE_URL}/api/plugins")
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        assert response.status_code == 200
    
    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]
    
    print(f"\n  Average: {avg_time:.2f}ms")
    print(f"  P95: {p95_time:.2f}ms")
    
    assert avg_time < 150, f"Average response time {avg_time}ms exceeds 150ms"
    assert p95_time < 300, f"P95 response time {p95_time}ms exceeds 300ms"


@pytest.mark.slow
def test_concurrent_requests():
    """Test handling multiple concurrent requests."""
    def make_request():
        response = httpx.get(f"{BASE_URL}/api/plugins")
        return response.status_code == 200
    
    # Make 50 concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        start = time.time()
        results = list(executor.map(lambda _: make_request(), range(50)))
        elapsed = time.time() - start
    
    success_count = sum(results)
    throughput = len(results) / elapsed
    
    print(f"\n  Total requests: {len(results)}")
    print(f"  Successful: {success_count}")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Throughput: {throughput:.2f} req/s")
    
    assert success_count == 50, f"Only {success_count}/50 requests succeeded"
    assert throughput > 10, f"Throughput {throughput:.2f} req/s too low"


@pytest.mark.slow
@pytest.mark.integration
def test_metrics_query_performance():
    """Test metrics retrieval performance."""
    # Get list of plugins first
    response = httpx.get(f"{BASE_URL}/api/plugins")
    assert response.status_code == 200
    plugins = response.json()
    
    if not plugins:
        pytest.skip("No plugins available for testing")
    
    plugin_id = plugins[0]["plugin_id"]
    
    # Test metrics retrieval time
    times = []
    for _ in range(5):
        start = time.time()
        response = httpx.get(f"{BASE_URL}/api/plugins/{plugin_id}/metrics?limit=100")
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        assert response.status_code == 200
    
    avg_time = sum(times) / len(times)
    print(f"\n  Average metrics query time: {avg_time:.2f}ms")
    
    assert avg_time < 200, f"Metrics query too slow: {avg_time}ms"


@pytest.mark.slow
def test_api_under_sustained_load():
    """Test API behavior under sustained load."""
    duration = 10  # seconds
    request_interval = 0.1  # 10 req/s
    
    start_time = time.time()
    request_times = []
    errors = 0
    
    while time.time() - start_time < duration:
        try:
            req_start = time.time()
            response = httpx.get(f"{BASE_URL}/health", timeout=2.0)
            req_time = (time.time() - req_start) * 1000
            request_times.append(req_time)
            
            if response.status_code != 200:
                errors += 1
        except Exception:
            errors += 1
        
        time.sleep(request_interval)
    
    total_requests = len(request_times)
    avg_time = sum(request_times) / len(request_times) if request_times else 0
    error_rate = (errors / total_requests * 100) if total_requests > 0 else 0
    
    print(f"\n  Duration: {duration}s")
    print(f"  Total requests: {total_requests}")
    print(f"  Average response: {avg_time:.2f}ms")
    print(f"  Errors: {errors} ({error_rate:.1f}%)")
    
    assert error_rate < 5, f"Error rate {error_rate}% too high"
    assert avg_time < 150, f"Average response time degraded to {avg_time}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
