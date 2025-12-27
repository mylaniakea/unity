"""
Tests for dashboard API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.alert_rules import AlertSeverity, AlertStatus
from app.models.monitoring import Alert


client = TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


class TestDashboardOverview:
    """Tests for /api/v1/monitoring/dashboard/overview endpoint."""
    
    @patch('app.routers.monitoring.dashboard.metrics_service')
    @pytest.mark.asyncio
    async def test_get_dashboard_overview_success(self, mock_service, mock_db):
        """Test successful dashboard overview retrieval."""
        # Mock service responses
        mock_service.get_dashboard_metrics = AsyncMock(return_value={
            'cpu': {'value': 45.2, 'timestamp': datetime.utcnow().isoformat()},
            'memory': {'value': 62.5, 'timestamp': datetime.utcnow().isoformat()},
            'disk': None,
            'network': None
        })
        
        mock_service.get_alert_summary = AsyncMock(return_value={
            'total': 10,
            'unresolved': 3,
            'by_severity': {'critical': 1, 'warning': 2, 'info': 0},
            'recent_alerts': []
        })
        
        mock_service.get_infrastructure_health = AsyncMock(return_value={
            'servers': {'total': 5, 'healthy': 4, 'unhealthy': 1},
            'storage': {'total': 10, 'devices': 10, 'pools': 0},
            'databases': {'total': 3, 'online': 3, 'offline': 0}
        })
        
        mock_service.get_plugin_metrics_summary = AsyncMock(return_value=[
            {'plugin_id': 'system_info', 'name': 'System Info', 'enabled': True, 'status': 'success', 'is_stale': False},
            {'plugin_id': 'disk_monitor', 'name': 'Disk Monitor', 'enabled': True, 'status': 'success', 'is_stale': False}
        ])
        
        response = client.get('/api/v1/monitoring/dashboard/overview')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'timestamp' in data
        assert 'metrics' in data
        assert 'alerts' in data
        assert 'infrastructure' in data
        assert 'plugins' in data
        
        # Check metrics
        assert data['metrics']['cpu']['value'] == 45.2
        assert data['metrics']['memory']['value'] == 62.5
        
        # Check alerts
        assert data['alerts']['total'] == 10
        assert data['alerts']['unresolved'] == 3
        
        # Check infrastructure
        assert data['infrastructure']['servers']['total'] == 5
        
        # Check plugins
        assert data['plugins']['total'] == 2
        assert data['plugins']['enabled'] == 2
        assert data['plugins']['healthy'] == 2


class TestMetricsHistory:
    """Tests for /api/v1/monitoring/dashboard/metrics/history endpoint."""
    
    @patch('app.routers.monitoring.dashboard.metrics_service')
    @pytest.mark.asyncio
    async def test_get_metrics_history_default_range(self, mock_service, mock_db):
        """Test metrics history with default time range."""
        mock_service.get_multi_metric_history = AsyncMock(return_value={
            'system_info.cpu_percent': [
                {'timestamp': datetime.utcnow().isoformat(), 'value': 45.0}
            ]
        })
        
        response = client.get('/api/v1/monitoring/dashboard/metrics/history')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['time_range'] == '1h'
        assert 'metrics' in data
        assert 'fetched_at' in data
    
    @patch('app.routers.monitoring.dashboard.metrics_service')
    @pytest.mark.asyncio
    async def test_get_metrics_history_custom_range(self, mock_service, mock_db):
        """Test metrics history with custom time range."""
        mock_service.get_multi_metric_history = AsyncMock(return_value={})
        
        response = client.get('/api/v1/monitoring/dashboard/metrics/history?time_range=24h')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['time_range'] == '24h'
    
    def test_get_metrics_history_invalid_range(self):
        """Test metrics history with invalid time range."""
        response = client.get('/api/v1/monitoring/dashboard/metrics/history?time_range=invalid')
        
        assert response.status_code == 422  # Validation error


class TestPluginHealth:
    """Tests for /api/v1/monitoring/dashboard/plugins/health endpoint."""
    
    @patch('app.routers.monitoring.dashboard.metrics_service')
    @pytest.mark.asyncio
    async def test_get_plugins_health_all(self, mock_service, mock_db):
        """Test getting health for all plugins."""
        mock_service.get_plugin_metrics_summary = AsyncMock(return_value=[
            {'plugin_id': 'p1', 'name': 'Plugin 1', 'category': 'system', 'status': 'success', 'is_stale': False},
            {'plugin_id': 'p2', 'name': 'Plugin 2', 'category': 'network', 'status': 'error', 'is_stale': False},
            {'plugin_id': 'p3', 'name': 'Plugin 3', 'category': 'system', 'status': 'success', 'is_stale': True}
        ])
        
        response = client.get('/api/v1/monitoring/dashboard/plugins/health')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['total'] == 3
        assert data['summary']['healthy'] == 1
        assert data['summary']['stale'] == 1
        assert data['summary']['failed'] == 1
    
    @patch('app.routers.monitoring.dashboard.metrics_service')
    @pytest.mark.asyncio
    async def test_get_plugins_health_filtered(self, mock_service, mock_db):
        """Test getting health filtered by category."""
        mock_service.get_plugin_metrics_summary = AsyncMock(return_value=[
            {'plugin_id': 'p1', 'name': 'Plugin 1', 'category': 'system', 'status': 'success', 'is_stale': False},
            {'plugin_id': 'p2', 'name': 'Plugin 2', 'category': 'network', 'status': 'success', 'is_stale': False},
            {'plugin_id': 'p3', 'name': 'Plugin 3', 'category': 'system', 'status': 'success', 'is_stale': False}
        ])
        
        response = client.get('/api/v1/monitoring/dashboard/plugins/health?category=system')
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only return system plugins
        assert data['total'] == 2
        assert all(p['category'] == 'system' for p in data['plugins'])


class TestSingleMetricHistory:
    """Tests for single metric history endpoint."""
    
    @patch('app.routers.monitoring.dashboard.metrics_service')
    @pytest.mark.asyncio
    async def test_get_single_metric_history(self, mock_service, mock_db):
        """Test getting history for a single metric."""
        mock_service.get_metric_history = AsyncMock(return_value=[
            {'timestamp': datetime.utcnow().isoformat(), 'value': 50.0}
        ])
        
        response = client.get('/api/v1/monitoring/dashboard/metrics/system_info/cpu_percent/history')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['plugin_id'] == 'system_info'
        assert data['metric_name'] == 'cpu_percent'
        assert data['time_range'] == '1h'
        assert len(data['data']) == 1
        assert data['count'] == 1
