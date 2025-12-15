"""
Plugin Loader for Unity

Discovers and loads plugins from:
- Built-in plugins (backend/app/plugins/builtin/)
- External plugins (via entry points)
"""

import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Type, Optional
import logging
from .base import PluginBase

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Discover and load plugins from various sources.
    
    Supports:
    - Built-in plugins from builtin/ directory
    - External plugins via Python entry points
    """
    
    def __init__(self):
        """Initialize plugin loader."""
        self.plugins: Dict[str, Type[PluginBase]] = {}
        self.builtin_path = Path(__file__).parent / "builtin"
        
    def discover_builtin_plugins(self) -> List[str]:
        """
        Discover built-in plugins in the builtin/ directory.
        
        Returns:
            List of plugin IDs discovered
        """
        discovered = []
        
        if not self.builtin_path.exists():
            logger.warning(f"Built-in plugins directory not found: {self.builtin_path}")
            return discovered
        
        # Look for Python files in builtin/
        for plugin_file in self.builtin_path.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
                
            plugin_id = plugin_file.stem
            
            try:
                # Import the plugin module
                spec = importlib.util.spec_from_file_location(
                    f"app.plugins.builtin.{plugin_id}",
                    plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find PluginBase subclass in module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, PluginBase) and 
                            attr is not PluginBase):
                            
                            self.plugins[plugin_id] = attr
                            discovered.append(plugin_id)
                            logger.info(f"Loaded built-in plugin: {plugin_id}")
                            break
                            
            except Exception as e:
                logger.error(f"Failed to load built-in plugin {plugin_id}: {e}")
                
        return discovered
    
    def discover_external_plugins(self) -> List[str]:
        """
        Discover external plugins via entry points.
        
        External plugins should register via setup.py/pyproject.toml:
        [project.entry-points."unity.plugins"]
        my_plugin = "my_package.plugin:MyPlugin"
        
        Returns:
            List of plugin IDs discovered
        """
        discovered = []
        
        try:
            # Try using importlib.metadata (Python 3.8+)
            try:
                from importlib.metadata import entry_points
            except ImportError:
                # Fallback for older Python versions
                from importlib_metadata import entry_points
            
            # Get entry points for unity plugins
            if hasattr(entry_points, 'select'):
                # Python 3.10+ API
                eps = entry_points.select(group="unity.plugins")
            else:
                # Python 3.8-3.9 API
                eps = entry_points().get("unity.plugins", [])
            
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    plugin_id = ep.name
                    
                    if issubclass(plugin_class, PluginBase):
                        self.plugins[plugin_id] = plugin_class
                        discovered.append(plugin_id)
                        logger.info(f"Loaded external plugin: {plugin_id}")
                    else:
                        logger.warning(f"Plugin {plugin_id} does not inherit from PluginBase")
                        
                except Exception as e:
                    logger.error(f"Failed to load external plugin {ep.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to discover external plugins: {e}")
            
        return discovered
    
    def discover_all(self) -> List[str]:
        """
        Discover all plugins (built-in and external).
        
        Returns:
            List of all plugin IDs discovered
        """
        builtin = self.discover_builtin_plugins()
        external = self.discover_external_plugins()
        
        logger.info(f"Discovered {len(builtin)} built-in and {len(external)} external plugins")
        
        return builtin + external
    
    def get_plugin_class(self, plugin_id: str) -> Optional[Type[PluginBase]]:
        """
        Get plugin class by ID.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin class or None if not found
        """
        return self.plugins.get(plugin_id)
    
    def instantiate_plugin(
        self, 
        plugin_id: str, 
        config: Optional[Dict] = None
    ) -> Optional[PluginBase]:
        """
        Create instance of plugin by ID.
        
        Args:
            plugin_id: Plugin identifier
            config: Plugin configuration
            
        Returns:
            Plugin instance or None if not found
        """
        plugin_class = self.get_plugin_class(plugin_id)
        
        if not plugin_class:
            logger.error(f"Plugin {plugin_id} not found")
            return None
        
        try:
            return plugin_class(config=config)
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {plugin_id}: {e}")
            return None
    
    def list_plugins(self) -> List[str]:
        """
        List all discovered plugin IDs.
        
        Returns:
            List of plugin IDs
        """
        return list(self.plugins.keys())
    
    def reload_plugins(self):
        """Reload all plugins (useful for development)."""
        self.plugins.clear()
        self.discover_all()
