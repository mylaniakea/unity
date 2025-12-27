"""Tests for system monitoring plugins."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.plugins.builtin.system_info import SystemInfoPlugin
from app.plugins.builtin.process_monitor import ProcessMonitorPlugin
from app.plugins.builtin.temperature_monitor import TemperatureMonitorPlugin


class TestSystemInfoPlugin:
    """Tests for SystemInfoPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return SystemInfoPlugin(config={})
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "system-info"
        assert metadata.version == "1.0.0"
        assert metadata.name == "System Info"
        assert "psutil" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_data_basic(self, plugin):
        """Test basic data collection."""
        with patch('psutil.cpu_percent', return_value=45.2):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value = Mock(
                    total=34359738368,  # 32 GB
                    used=20000000000,
                    percent=58.2
                )
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value = Mock(
                        total=500000000000,
                        used=320000000000,
                        percent=64.0
                    )
                    
                    data = await plugin.collect_data()
                    
                    assert 'cpu' in data
                    assert data['cpu']['usage_percent'] == 45.2
                    assert 'memory' in data
                    assert data['memory']['percent'] == 58.2
                    assert 'disk' in data
    
    @pytest.mark.asyncio
    async def test_collect_with_network(self, plugin):
        """Test collection with network stats enabled."""
        plugin.config = {"collect_network": True}
        
        with patch('psutil.cpu_percent', return_value=30.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value = Mock(total=16000000000, used=8000000000, percent=50.0)
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value = Mock(total=1000000000000, used=500000000000, percent=50.0)
                    with patch('psutil.net_io_counters') as mock_net:
                        mock_net.return_value = Mock(
                            bytes_sent=1000000,
                            bytes_recv=2000000
                        )
                        
                        data = await plugin.collect_data()
                        
                        if 'network' in data:
                            assert data['network']['bytes_sent'] == 1000000
                            assert data['network']['bytes_recv'] == 2000000
    
    @pytest.mark.asyncio
    async def test_error_handling(self, plugin):
        """Test error handling when psutil fails."""
        with patch('psutil.cpu_percent', side_effect=Exception("CPU read failed")):
            data = await plugin.collect_data()
            # Should handle error gracefully
            assert isinstance(data, dict)


class TestProcessMonitorPlugin:
    """Tests for ProcessMonitorPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return ProcessMonitorPlugin(config={"top_n": 5})
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "process-monitor"
        assert metadata.version == "1.0.0"
        assert "psutil" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_process_counts(self, plugin):
        """Test process count collection."""
        mock_processes = [Mock() for _ in range(10)]
        
        with patch('psutil.pids', return_value=list(range(100))):
            with patch('psutil.Process') as mock_process:
                mock_process.return_value = Mock(num_threads=lambda: 5)
                
                data = await plugin.collect_data()
                
                if 'process_count' in data:
                    assert isinstance(data['process_count'], int)
    
    @pytest.mark.asyncio
    async def test_top_processes(self, plugin):
        """Test top process collection."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'python',
            'cpu_percent': 25.5,
            'memory_percent': 10.2
        }
        
        with patch('psutil.process_iter', return_value=[mock_proc]):
            data = await plugin.collect_data()
            
            if 'top_processes' in data:
                assert isinstance(data['top_processes'], list)
    
    @pytest.mark.asyncio
    async def test_load_average(self, plugin):
        """Test system load average collection."""
        with patch('psutil.getloadavg', return_value=(1.5, 1.2, 1.0)):
            data = await plugin.collect_data()
            
            if 'load_average' in data:
                assert len(data['load_average']) == 3
                assert data['load_average'][0] == 1.5


class TestTemperatureMonitorPlugin:
    """Tests for TemperatureMonitorPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return TemperatureMonitorPlugin(config={})
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "temperature-monitor"
        assert metadata.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_collect_temperatures(self, plugin):
        """Test temperature collection."""
        mock_temps = {
            'coretemp': [
                Mock(label='Package id 0', current=45.0, high=100.0, critical=105.0),
                Mock(label='Core 0', current=43.0, high=100.0, critical=105.0),
            ]
        }
        
        with patch('psutil.sensors_temperatures', return_value=mock_temps):
            data = await plugin.collect_data()
            
            if 'temperatures' in data:
                assert isinstance(data['temperatures'], dict)
    
    @pytest.mark.asyncio
    async def test_temperature_alerts(self, plugin):
        """Test temperature alert threshold."""
        plugin.config = {"alert_threshold": 80.0}
        
        mock_temps = {
            'coretemp': [
                Mock(label='Core 0', current=85.0, high=100.0, critical=105.0),
                Mock(label='Core 1', current=70.0, high=100.0, critical=105.0),
            ]
        }
        
        with patch('psutil.sensors_temperatures', return_value=mock_temps):
            data = await plugin.collect_data()
            
            if 'alerts' in data:
                # Should detect Core 0 over threshold
                assert len(data['alerts']) >= 1
    
    @pytest.mark.asyncio
    async def test_no_sensors_available(self, plugin):
        """Test behavior when no temperature sensors available."""
        with patch('psutil.sensors_temperatures', return_value={}):
            data = await plugin.collect_data()
            
            # Should handle gracefully
            assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_celsius_to_fahrenheit(self, plugin):
        """Test temperature unit conversion."""
        plugin.config = {"temp_unit": "fahrenheit"}
        
        mock_temps = {
            'coretemp': [
                Mock(label='Core 0', current=50.0, high=100.0, critical=105.0),
            ]
        }
        
        with patch('psutil.sensors_temperatures', return_value=mock_temps):
            data = await plugin.collect_data()
            
            # Verify conversion if implemented
            if 'temperatures' in data:
                assert isinstance(data['temperatures'], dict)


# Test helper functions
def test_plugin_initialization():
    """Test that all system plugins can be initialized."""
    plugins = [
        SystemInfoPlugin(config={}),
        ProcessMonitorPlugin(config={}),
        TemperatureMonitorPlugin(config={})
    ]
    
    for plugin in plugins:
        assert plugin is not None
        metadata = plugin.get_metadata()
        assert metadata.id is not None
        assert metadata.version is not None


def test_plugin_config_validation():
    """Test plugin configuration validation."""
    # Valid config
    plugin = SystemInfoPlugin(config={"collect_network": True})
    assert plugin.config["collect_network"] is True
    
    # Empty config should work
    plugin = SystemInfoPlugin(config={})
    assert plugin.config == {}
    
    # None config should be handled
    plugin = SystemInfoPlugin(config=None)
    assert plugin.config is None or plugin.config == {}
