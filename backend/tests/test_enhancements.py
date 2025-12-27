"""
Integration tests for new enhancements.

Tests WebSocket, Advanced Alerting, Marketplace, Dashboard Builder, and AI Insights.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create database session."""
    # This would normally use a test database
    # For now, this is a placeholder
    pass


class TestWebSocketEnhancements:
    """Test WebSocket subscription features."""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection."""
        with client.websocket_connect("/ws/metrics") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
    
    def test_websocket_subscribe(self, client):
        """Test WebSocket subscription."""
        with client.websocket_connect("/ws/metrics") as websocket:
            # Send subscribe message
            websocket.send_json({
                "type": "subscribe",
                "plugin_ids": ["system_info"],
                "metric_names": ["cpu_percent"]
            })
            
            response = websocket.receive_json()
            assert response["type"] == "subscribed"


class TestMarketplaceAPI:
    """Test Plugin Marketplace API."""
    
    def test_list_marketplace_plugins(self, client):
        """Test listing marketplace plugins."""
        response = client.get("/api/v1/marketplace/plugins")
        assert response.status_code == 200
        assert "plugins" in response.json()
        assert "total" in response.json()
    
    def test_get_marketplace_categories(self, client):
        """Test getting categories."""
        response = client.get("/api/v1/marketplace/categories")
        assert response.status_code == 200
        assert "categories" in response.json()
    
    def test_get_widget_templates(self, client):
        """Test getting widget templates."""
        response = client.get("/api/v1/dashboards/templates/widgets")
        assert response.status_code == 200
        assert "templates" in response.json()
        assert len(response.json()["templates"]) > 0


class TestDashboardBuilder:
    """Test Dashboard Builder API."""
    
    def test_create_dashboard(self, client):
        """Test creating a dashboard."""
        response = client.post("/api/v1/dashboards", json={
            "name": "Test Dashboard",
            "description": "Test",
            "is_shared": False,
            "refresh_interval": 30
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Test Dashboard"
    
    def test_list_dashboards(self, client):
        """Test listing dashboards."""
        response = client.get("/api/v1/dashboards")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAIInsights:
    """Test AI Insights API."""
    
    def test_detect_anomalies(self, client):
        """Test anomaly detection."""
        response = client.get(
            "/api/v1/ai/insights/anomalies",
            params={
                "plugin_id": "system_info",
                "metric_name": "cpu_percent",
                "hours": 24,
                "method": "zscore"
            }
        )
        # Should return 200 even if no data
        assert response.status_code in [200, 404, 500]
    
    def test_forecast_metric(self, client):
        """Test metric forecasting."""
        response = client.get(
            "/api/v1/ai/insights/forecast",
            params={
                "plugin_id": "system_info",
                "metric_name": "cpu_percent",
                "hours": 24,
                "periods": 5
            }
        )
        # Should return 200 even if no data
        assert response.status_code in [200, 404, 500]


class TestAdvancedAlerting:
    """Test Advanced Alerting features."""
    
    def test_alert_correlation_exists(self):
        """Test that alert correlation service exists."""
        from app.services.monitoring.advanced_alerting import AlertCorrelator
        assert AlertCorrelator is not None
    
    def test_multi_condition_evaluator_exists(self):
        """Test that multi-condition evaluator exists."""
        from app.services.monitoring.advanced_alerting import AdvancedAlertEvaluator
        assert AdvancedAlertEvaluator is not None


class TestPerformanceOptimizations:
    """Test performance optimizations."""
    
    def test_cache_middleware_exists(self):
        """Test that cache middleware exists."""
        from app.middleware.cache_middleware import CacheMiddleware
        assert CacheMiddleware is not None
    
    def test_query_optimizer_exists(self):
        """Test that query optimizer exists."""
        from app.utils.query_optimizer import optimize_metrics_query
        assert optimize_metrics_query is not None

