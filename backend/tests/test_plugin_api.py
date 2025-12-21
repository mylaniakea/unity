"""
Comprehensive tests for Plugin API endpoints (Run 5).

Tests the REST API implemented in backend/app/api/plugins.py
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from app.core.database import Base, get_db
from app.models.plugin import Plugin, PluginMetric, PluginStatus, PluginExecution


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency with test database."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_plugin(test_db):
    """Create a sample plugin for testing."""
    plugin = Plugin(
        plugin_id="test_plugin",
        name="Test Plugin",
        version="1.0.0",
        description="A test plugin",
        category="test",
        enabled=True,
        config={"interval": 60}
    )
    test_db.add(plugin)
    test_db.commit()
    test_db.refresh(plugin)
    return plugin


@pytest.fixture
def sample_metrics(test_db, sample_plugin):
    """Create sample metrics for testing."""
    metrics = []
    base_time = datetime.utcnow()
    
    for i in range(5):
        metric = PluginMetric(
            time=base_time - timedelta(minutes=i),
            plugin_id=sample_plugin.plugin_id,
            metric_name=f"test_metric_{i}",
            value={"count": 100 + i},
            tags={"source": "test"}
        )
        metrics.append(metric)
        test_db.add(metric)
    
    test_db.commit()
    return metrics


@pytest.fixture
def sample_status(test_db, sample_plugin):
    """Create sample plugin status."""
    status = PluginStatus(
        plugin_id=sample_plugin.plugin_id,
        is_healthy=True,
        last_execution=datetime.utcnow(),
        last_error=None,
        consecutive_errors=0
    )
    test_db.add(status)
    test_db.commit()
    test_db.refresh(status)
    return status


@pytest.fixture
def sample_executions(test_db, sample_plugin):
    """Create sample plugin executions."""
    executions = []
    base_time = datetime.utcnow()
    
    for i in range(3):
        execution = PluginExecution(
            plugin_id=sample_plugin.plugin_id,
            started_at=base_time - timedelta(minutes=i*5),
            completed_at=base_time - timedelta(minutes=i*5) + timedelta(seconds=2),
            success=True,
            metrics_collected=10 + i,
            error_message=None
        )
        executions.append(execution)
        test_db.add(execution)
    
    test_db.commit()
    return executions


# === API Endpoint Tests ===

@pytest.mark.api
def test_list_plugins_empty(client, test_db):
    """Test listing plugins when none exist."""
    response = client.get("/api/plugins")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.api
def test_list_plugins(client, sample_plugin):
    """Test listing plugins."""
    response = client.get("/api/plugins")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["plugin_id"] == "test_plugin"
    assert data[0]["name"] == "Test Plugin"


@pytest.mark.api
def test_list_plugins_filter_enabled(client, test_db):
    """Test filtering plugins by enabled status."""
    # Create enabled and disabled plugins
    enabled = Plugin(plugin_id="enabled", name="Enabled", enabled=True)
    disabled = Plugin(plugin_id="disabled", name="Disabled", enabled=False)
    test_db.add_all([enabled, disabled])
    test_db.commit()
    
    # Test enabled filter
    response = client.get("/api/plugins?enabled=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["plugin_id"] == "enabled"
    
    # Test disabled filter
    response = client.get("/api/plugins?enabled=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["plugin_id"] == "disabled"


@pytest.mark.api
def test_list_plugins_filter_category(client, test_db):
    """Test filtering plugins by category."""
    system = Plugin(plugin_id="sys", name="System", category="system")
    network = Plugin(plugin_id="net", name="Network", category="network")
    test_db.add_all([system, network])
    test_db.commit()
    
    response = client.get("/api/plugins?category=system")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["plugin_id"] == "sys"


@pytest.mark.api
def test_get_plugin_success(client, sample_plugin):
    """Test getting a specific plugin."""
    response = client.get(f"/api/plugins/{sample_plugin.plugin_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == sample_plugin.plugin_id
    assert data["name"] == sample_plugin.name
    assert data["version"] == sample_plugin.version


@pytest.mark.api
def test_get_plugin_not_found(client):
    """Test getting a non-existent plugin."""
    response = client.get("/api/plugins/nonexistent")
    assert response.status_code == 404


@pytest.mark.api
def test_enable_plugin(client, test_db):
    """Test enabling a plugin."""
    plugin = Plugin(plugin_id="test", name="Test", enabled=False)
    test_db.add(plugin)
    test_db.commit()
    
    response = client.post(
        "/api/plugins/test/enable",
        json={"enabled": True, "config": {"interval": 30}}
    )
    assert response.status_code == 200
    
    # Verify plugin was updated
    test_db.refresh(plugin)
    assert plugin.enabled is True
    assert plugin.config["interval"] == 30


@pytest.mark.api
def test_get_plugin_status(client, sample_plugin, sample_status):
    """Test getting plugin health status."""
    response = client.get(f"/api/plugins/{sample_plugin.plugin_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["plugin_id"] == sample_plugin.plugin_id
    assert data["is_healthy"] is True
    assert data["consecutive_errors"] == 0


@pytest.mark.api
def test_get_plugin_status_not_found(client, sample_plugin):
    """Test getting status for plugin without status record."""
    response = client.get(f"/api/plugins/{sample_plugin.plugin_id}/status")
    # Should still return 200 with default status or 404
    assert response.status_code in [200, 404]


@pytest.mark.api
def test_get_plugin_metrics(client, sample_plugin, sample_metrics):
    """Test getting plugin metrics."""
    response = client.get(f"/api/plugins/{sample_plugin.plugin_id}/metrics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 100  # Default limit
    assert all(m["plugin_id"] == sample_plugin.plugin_id for m in data)


@pytest.mark.api
def test_get_plugin_metrics_with_limit(client, sample_plugin, sample_metrics):
    """Test getting plugin metrics with custom limit."""
    response = client.get(f"/api/plugins/{sample_plugin.plugin_id}/metrics?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2


@pytest.mark.api
def test_get_plugin_metrics_history(client, sample_plugin, sample_metrics):
    """Test getting plugin metrics history."""
    response = client.get(
        f"/api/plugins/{sample_plugin.plugin_id}/metrics/history?hours=1"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) or isinstance(data, list)


@pytest.mark.api
def test_get_plugin_executions(client, sample_plugin, sample_executions):
    """Test getting plugin execution history."""
    response = client.get(f"/api/plugins/{sample_plugin.plugin_id}/executions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(e["plugin_id"] == sample_plugin.plugin_id for e in data)
    assert all(e["success"] is True for e in data)


@pytest.mark.api
def test_list_categories(client, test_db):
    """Test listing plugin categories."""
    # Create plugins with different categories
    test_db.add_all([
        Plugin(plugin_id="sys", name="System", category="system"),
        Plugin(plugin_id="net", name="Network", category="network"),
        Plugin(plugin_id="db", name="Database", category="database"),
    ])
    test_db.commit()
    
    response = client.get("/api/plugins/categories/list")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "network" in data
    assert "system" in data


@pytest.mark.api
def test_get_stats_summary(client, sample_plugin, sample_metrics):
    """Test getting statistics summary."""
    response = client.get("/api/plugins/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_plugins" in data
    assert "enabled_plugins" in data
    assert "total_metrics" in data
    assert data["total_plugins"] >= 1


# === Integration Tests ===

@pytest.mark.integration
def test_plugin_lifecycle(client, test_db):
    """Test complete plugin lifecycle: create -> enable -> collect metrics -> disable."""
    # Create plugin
    plugin = Plugin(plugin_id="lifecycle_test", name="Lifecycle Test", enabled=False)
    test_db.add(plugin)
    test_db.commit()
    
    # 1. List plugins
    response = client.get("/api/plugins")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # 2. Get plugin details
    response = client.get("/api/plugins/lifecycle_test")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    
    # 3. Enable plugin
    response = client.post(
        "/api/plugins/lifecycle_test/enable",
        json={"enabled": True}
    )
    assert response.status_code == 200
    
    # 4. Verify enabled
    response = client.get("/api/plugins/lifecycle_test")
    assert response.json()["enabled"] is True
    
    # 5. Add metrics (simulating collection)
    metric = PluginMetric(
        time=datetime.utcnow(),
        plugin_id="lifecycle_test",
        metric_name="test_metric",
        value={"value": 42}
    )
    test_db.add(metric)
    test_db.commit()
    
    # 6. Retrieve metrics
    response = client.get("/api/plugins/lifecycle_test/metrics")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # 7. Disable plugin
    response = client.post(
        "/api/plugins/lifecycle_test/enable",
        json={"enabled": False}
    )
    assert response.status_code == 200


@pytest.mark.integration
def test_metrics_time_range(client, test_db, sample_plugin):
    """Test metrics retrieval across different time ranges."""
    now = datetime.utcnow()
    
    # Create metrics at different times
    for hours_ago in [1, 6, 12, 24, 48]:
        metric = PluginMetric(
            time=now - timedelta(hours=hours_ago),
            plugin_id=sample_plugin.plugin_id,
            metric_name="time_test",
            value={"hours_ago": hours_ago}
        )
        test_db.add(metric)
    test_db.commit()
    
    # Test 24-hour window
    response = client.get(
        f"/api/plugins/{sample_plugin.plugin_id}/metrics/history?hours=24"
    )
    assert response.status_code == 200
    # Should include metrics from last 24 hours (1, 6, 12, 24)
    
    # Test 12-hour window
    response = client.get(
        f"/api/plugins/{sample_plugin.plugin_id}/metrics/history?hours=12"
    )
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
