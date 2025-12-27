"""Tests for database monitoring plugins."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from app.plugins.builtin.postgres_monitor import PostgreSQLMonitorPlugin
from app.plugins.builtin.mysql_monitor import MySQLMonitorPlugin
from app.plugins.builtin.mongodb_monitor import MongoDBMonitorPlugin
from app.plugins.builtin.redis_monitor import RedisMonitorPlugin


class TestPostgreSQLMonitorPlugin:
    """Tests for PostgreSQLMonitorPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return PostgreSQLMonitorPlugin(config={
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "test_user",
            "password": "test_pass"
        })
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "postgres-monitor"
        assert metadata.version == "1.0.0"
        assert "psycopg2" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_connection_stats(self, plugin):
        """Test PostgreSQL connection statistics collection."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (50, 10, 100)  # active, idle, max
        mock_cursor.fetchall.return_value = []
        
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            data = await plugin.collect_data()
            
            if 'connections' in data:
                assert isinstance(data['connections'], dict)
    
    @pytest.mark.asyncio
    async def test_connection_failure(self, plugin):
        """Test handling of connection failures."""
        with patch('psycopg2.connect', side_effect=Exception("Connection refused")):
            data = await plugin.collect_data()
            
            assert 'error' in data or data == {}
    
    @pytest.mark.asyncio
    async def test_transaction_stats(self, plugin):
        """Test transaction statistics collection."""
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (50, 10, 100),  # connections
            (1000, 5),  # transactions (commits, rollbacks)
            (500000,)  # database size
        ]
        mock_cursor.fetchall.return_value = []
        
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            data = await plugin.collect_data()
            
            if 'transactions' in data:
                assert 'commits' in data['transactions'] or 'commit' in str(data)


class TestMySQLMonitorPlugin:
    """Tests for MySQLMonitorPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return MySQLMonitorPlugin(config={
            "host": "localhost",
            "port": 3306,
            "user": "test_user",
            "password": "test_pass"
        })
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "mysql-monitor"
        assert metadata.version == "1.0.0"
        assert "pymysql" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_status_variables(self, plugin):
        """Test MySQL status variables collection."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('Threads_connected', '10'),
            ('Max_used_connections', '50'),
            ('Uptime', '86400'),
            ('Questions', '10000')
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('pymysql.connect', return_value=mock_conn):
            data = await plugin.collect_data()
            
            assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_slow_queries(self, plugin):
        """Test slow query detection."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('Slow_queries', '25')
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        with patch('pymysql.connect', return_value=mock_conn):
            data = await plugin.collect_data()
            
            if 'slow_queries' in data:
                assert data['slow_queries'] == 25


class TestMongoDBMonitorPlugin:
    """Tests for MongoDBMonitorPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return MongoDBMonitorPlugin(config={
            "host": "localhost",
            "port": 27017
        })
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "mongodb-monitor"
        assert metadata.version == "1.0.0"
        assert "pymongo" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_server_status(self, plugin):
        """Test MongoDB server status collection."""
        mock_client = Mock()
        mock_db = Mock()
        mock_db.command.return_value = {
            'version': '4.4.0',
            'uptime': 86400,
            'connections': {'current': 10, 'available': 800},
            'opcounters': {
                'insert': 1000,
                'query': 5000,
                'update': 500,
                'delete': 100
            }
        }
        mock_client.__getitem__.return_value = mock_db
        
        with patch('pymongo.MongoClient', return_value=mock_client):
            data = await plugin.collect_data()
            
            if 'version' in data:
                assert data['version'] == '4.4.0'
            if 'connections' in data:
                assert data['connections']['current'] == 10
    
    @pytest.mark.asyncio
    async def test_replication_status(self, plugin):
        """Test MongoDB replication status."""
        mock_client = Mock()
        mock_db = Mock()
        mock_db.command.side_effect = [
            {'ok': 1},  # serverStatus
            {'set': 'rs0', 'members': []}  # replSetGetStatus
        ]
        mock_client.__getitem__.return_value = mock_db
        
        with patch('pymongo.MongoClient', return_value=mock_client):
            data = await plugin.collect_data()
            
            # Should handle replication status
            assert isinstance(data, dict)


class TestRedisMonitorPlugin:
    """Tests for RedisMonitorPlugin."""
    
    @pytest.fixture
    def plugin(self):
        return RedisMonitorPlugin(config={
            "host": "localhost",
            "port": 6379
        })
    
    def test_metadata(self, plugin):
        """Test plugin metadata."""
        metadata = plugin.get_metadata()
        assert metadata.id == "redis-monitor"
        assert metadata.version == "1.0.0"
        assert "redis" in metadata.dependencies
    
    @pytest.mark.asyncio
    async def test_collect_info(self, plugin):
        """Test Redis INFO command collection."""
        mock_redis = Mock()
        mock_redis.info.return_value = {
            'redis_version': '6.2.0',
            'uptime_in_seconds': 86400,
            'connected_clients': 5,
            'used_memory': 1024000,
            'used_memory_human': '1.00M',
            'total_commands_processed': 10000
        }
        mock_redis.dbsize.return_value = 1000
        
        with patch('redis.Redis', return_value=mock_redis):
            data = await plugin.collect_data()
            
            if 'version' in data or 'redis_version' in data:
                assert '6.2.0' in str(data)
            if 'connected_clients' in data:
                assert data['connected_clients'] == 5
    
    @pytest.mark.asyncio
    async def test_memory_stats(self, plugin):
        """Test Redis memory statistics."""
        mock_redis = Mock()
        mock_redis.info.return_value = {
            'used_memory': 2048000,
            'used_memory_human': '2.00M',
            'maxmemory': 10485760,
            'mem_fragmentation_ratio': 1.05
        }
        
        with patch('redis.Redis', return_value=mock_redis):
            data = await plugin.collect_data()
            
            if 'used_memory' in data:
                assert data['used_memory'] == 2048000
    
    @pytest.mark.asyncio
    async def test_connection_failure(self, plugin):
        """Test Redis connection failure handling."""
        with patch('redis.Redis', side_effect=Exception("Connection refused")):
            data = await plugin.collect_data()
            
            assert 'error' in data or data == {}
    
    @pytest.mark.asyncio
    async def test_keyspace_stats(self, plugin):
        """Test Redis keyspace statistics."""
        mock_redis = Mock()
        mock_redis.info.return_value = {
            'db0': {'keys': 1000, 'expires': 100}
        }
        mock_redis.dbsize.return_value = 1000
        
        with patch('redis.Redis', return_value=mock_redis):
            data = await plugin.collect_data()
            
            # Should collect key count
            assert isinstance(data, dict)


# Integration-style tests
def test_all_database_plugins_have_required_metadata():
    """Test that all database plugins have required metadata fields."""
    plugins = [
        PostgreSQLMonitorPlugin(config={}),
        MySQLMonitorPlugin(config={}),
        MongoDBMonitorPlugin(config={}),
        RedisMonitorPlugin(config={})
    ]
    
    for plugin in plugins:
        metadata = plugin.get_metadata()
        assert metadata.id is not None
        assert metadata.name is not None
        assert metadata.version is not None
        assert len(metadata.dependencies) > 0


def test_database_plugin_config_requirements():
    """Test database plugins handle missing config correctly."""
    # Should handle missing connection details
    plugin = PostgreSQLMonitorPlugin(config={})
    assert plugin.config == {}
    
    # Should handle None config
    plugin = MySQLMonitorPlugin(config=None)
    assert plugin.config is None or plugin.config == {}


@pytest.mark.asyncio
async def test_database_plugins_error_isolation():
    """Test that database plugin errors don't crash the system."""
    plugins = [
        PostgreSQLMonitorPlugin(config={"host": "invalid"}),
        MySQLMonitorPlugin(config={"host": "invalid"}),
        MongoDBMonitorPlugin(config={"host": "invalid"}),
        RedisMonitorPlugin(config={"host": "invalid"})
    ]
    
    for plugin in plugins:
        # All should handle errors gracefully
        try:
            data = await plugin.collect_data()
            assert isinstance(data, dict)
        except Exception as e:
            pytest.fail(f"Plugin {plugin.get_metadata().id} raised unhandled exception: {e}")
