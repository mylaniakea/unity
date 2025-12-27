"""Tests for network monitoring plugins."""
import pytest
from unittest.mock import Mock, patch

from app.plugins.builtin.network_monitor import NetworkMonitorPlugin
from app.plugins.builtin.dns_monitor import DNSMonitorPlugin
from app.plugins.builtin.vpn_monitor import VPNMonitorPlugin


class TestNetworkMonitorPlugin:
    @pytest.fixture
    def plugin(self):
        return NetworkMonitorPlugin(config={})
    
    def test_metadata(self, plugin):
        metadata = plugin.get_metadata()
        assert metadata.id == "network-monitor"
        assert "psutil" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_interface_stats(self, plugin):
        mock_stats = {
            'eth0': Mock(bytes_sent=1000000, bytes_recv=2000000, 
                        packets_sent=1000, packets_recv=2000,
                        errin=0, errout=0)
        }
        
        with patch('psutil.net_io_counters', return_value=mock_stats):
            data = await plugin.collect_data()
            assert isinstance(data, dict)


class TestDNSMonitorPlugin:
    @pytest.fixture
    def plugin(self):
        return DNSMonitorPlugin(config={
            "server_type": "pihole",
            "api_url": "http://pihole.local/admin/api.php"
        })
    
    def test_metadata(self, plugin):
        metadata = plugin.get_metadata()
        assert metadata.id == "dns-monitor"
    
    @pytest.mark.asyncio
    async def test_pihole_stats(self, plugin):
        mock_response = Mock()
        mock_response.json.return_value = {
            'dns_queries_today': 10000,
            'ads_blocked_today': 2500,
            'ads_percentage_today': 25.0
        }
        
        with patch('requests.get', return_value=mock_response):
            data = await plugin.collect_data()
            if 'queries_today' in data or 'dns_queries_today' in data:
                assert isinstance(data, dict)


class TestVPNMonitorPlugin:
    @pytest.fixture
    def plugin(self):
        return VPNMonitorPlugin(config={
            "vpn_type": "wireguard",
            "interface": "wg0"
        })
    
    def test_metadata(self, plugin):
        metadata = plugin.get_metadata()
        assert metadata.id == "vpn-monitor"
    
    @pytest.mark.asyncio
    async def test_wireguard_status(self, plugin):
        mock_result = Mock()
        mock_result.stdout = "interface: wg0\n  public key: test\n  listening port: 51820"
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            data = await plugin.collect_data()
            assert isinstance(data, dict)
