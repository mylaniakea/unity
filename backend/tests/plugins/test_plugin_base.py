"""Tests for plugin base classes and infrastructure."""
import pytest
from unittest.mock import Mock
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory


class MockPlugin(PluginBase):
    """Mock plugin for testing."""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="mock-plugin",
            name="Mock Plugin",
            version="1.0.0",
            description="A mock plugin for testing",
            author="Test",
            category=PluginCategory.SYSTEM,
            tags=["test", "mock"],
            requires_sudo=False,
            supported_os=["linux"],
            dependencies=[],
            config_schema={}
        )
    
    async def collect_data(self):
        return {"test": "data"}


class TestPluginBase:
    """Tests for PluginBase class."""
    
    def test_plugin_initialization(self):
        """Test plugin can be initialized."""
        plugin = MockPlugin(config={})
        assert plugin is not None
        assert plugin.config == {}
    
    def test_plugin_with_config(self):
        """Test plugin initialization with config."""
        config = {"option1": "value1", "option2": 42}
        plugin = MockPlugin(config=config)
        assert plugin.config == config
    
    def test_plugin_metadata(self):
        """Test plugin metadata structure."""
        plugin = MockPlugin(config={})
        metadata = plugin.get_metadata()
        
        assert metadata.id == "mock-plugin"
        assert metadata.name == "Mock Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.description is not None
        assert metadata.author is not None
        assert isinstance(metadata.category, PluginCategory)
        assert isinstance(metadata.tags, list)
        assert isinstance(metadata.requires_sudo, bool)
        assert isinstance(metadata.supported_os, list)
        assert isinstance(metadata.dependencies, list)
    
    @pytest.mark.asyncio
    async def test_plugin_collect_data(self):
        """Test plugin data collection."""
        plugin = MockPlugin(config={})
        data = await plugin.collect_data()
        
        assert isinstance(data, dict)
        assert "test" in data
        assert data["test"] == "data"
    
    def test_plugin_config_none(self):
        """Test plugin handles None config."""
        plugin = MockPlugin(config=None)
        assert plugin.config is None or plugin.config == {}
    
    def test_plugin_categories(self):
        """Test all plugin categories are defined."""
        categories = [
            PluginCategory.SYSTEM,
            PluginCategory.NETWORK,
            PluginCategory.DATABASE,
            PluginCategory.CONTAINER,
            PluginCategory.APPLICATION,
            PluginCategory.STORAGE,
            PluginCategory.SECURITY,
            PluginCategory.HARDWARE,
            PluginCategory.IOT,
            PluginCategory.MEDIA
        ]
        
        for category in categories:
            assert category is not None
            assert isinstance(category.value, str)


class TestPluginMetadata:
    """Tests for PluginMetadata class."""
    
    def test_metadata_creation(self):
        """Test metadata object creation."""
        metadata = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            version="2.0.0",
            description="Test description",
            author="Test Author",
            category=PluginCategory.APPLICATION,
            tags=["tag1", "tag2"],
            requires_sudo=True,
            supported_os=["linux", "darwin"],
            dependencies=["requests", "psutil"],
            config_schema={"type": "object"}
        )
        
        assert metadata.id == "test-plugin"
        assert metadata.name == "Test Plugin"
        assert metadata.version == "2.0.0"
        assert len(metadata.tags) == 2
        assert metadata.requires_sudo is True
        assert len(metadata.supported_os) == 2
        assert len(metadata.dependencies) == 2
    
    def test_metadata_minimal(self):
        """Test metadata with minimal fields."""
        metadata = PluginMetadata(
            id="minimal",
            name="Minimal",
            version="1.0.0",
            description="Minimal plugin",
            author="Test",
            category=PluginCategory.SYSTEM,
            tags=[],
            requires_sudo=False,
            supported_os=["linux"],
            dependencies=[],
            config_schema={}
        )
        
        assert metadata.id == "minimal"
        assert len(metadata.tags) == 0
        assert len(metadata.dependencies) == 0


def test_plugin_inheritance():
    """Test that plugins inherit correctly from PluginBase."""
    plugin = MockPlugin(config={})
    assert isinstance(plugin, PluginBase)
    assert hasattr(plugin, 'get_metadata')
    assert hasattr(plugin, 'collect_data')
    assert hasattr(plugin, 'config')
