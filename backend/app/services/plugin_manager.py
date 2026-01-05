"""
Plugin Manager Service

Manages the lifecycle of plugins, including:
- Discovery and registration
- Enabling/disabling
- Execution scheduling
- Health monitoring
- Metric collection and storage
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import Plugin, PluginMetric, PluginExecution
from app.plugins import PluginLoader, PluginBase
from app.plugins.base import PluginMetadata

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Central manager for all plugin operations.
    
    Responsibilities:
    - Plugin discovery and loading
    - Plugin lifecycle management (enable/disable)
    - Background execution scheduling
    - Health monitoring
    - Metrics storage
    """
    
    def __init__(self, db: Session):
        """
        Initialize plugin manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.loader = PluginLoader()
        self.plugin_instances: Dict[str, PluginBase] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    async def initialize(self):
        """
        Initialize plugin system.
        
        - Discovers all available plugins
        - Loads enabled plugins
        - Syncs database with discovered plugins
        """
        logger.info("Initializing plugin system...")
        
        # Discover all plugins
        discovered = self.loader.discover_all()
        logger.info(f"Discovered {len(discovered)} plugins")
        
        # Sync discovered plugins with database
        await self._sync_plugins_to_db()
        
        # Load enabled plugins
        await self._load_enabled_plugins()
        
        logger.info("Plugin system initialized")
    
    async def _sync_plugins_to_db(self):
        """Sync discovered plugins with database registry."""
        for plugin_id in self.loader.list_plugins():
            plugin_class = self.loader.get_plugin_class(plugin_id)
            if not plugin_class:
                continue
                
            try:
                # Create temporary instance to get metadata
                temp_instance = plugin_class()
                metadata = temp_instance.get_metadata()
                
                # Check if plugin exists in DB
                stmt = select(Plugin).where(Plugin.id == plugin_id)
                result = self.db.execute(stmt)
                db_plugin = result.scalar_one_or_none()
                
                if not db_plugin:
                    # Create new plugin entry
                    db_plugin = Plugin(
                        id=metadata.id,
                        name=metadata.name,
                        version=metadata.version,
                        category=metadata.category.value,
                        description=metadata.description,
                        author=metadata.author,
                        external=False,  # Built-in plugins
                        metadata=metadata.dict(),
                        enabled=False
                    )
                    self.db.add(db_plugin)
                    logger.info(f"Registered new plugin: {plugin_id}")
                else:
                    # Update existing plugin metadata
                    db_plugin.name = metadata.name
                    db_plugin.version = metadata.version
                    db_plugin.category = metadata.category.value
                    db_plugin.description = metadata.description
                    db_plugin.author = metadata.author
                    db_plugin.plugin_metadata = metadata.dict()
                    db_plugin.updated_at = datetime.utcnow()
                    logger.info(f"Updated plugin metadata: {plugin_id}")
                    
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Failed to sync plugin {plugin_id}: {e}")
                self.db.rollback()
    
    async def _load_enabled_plugins(self):
        """Load and instantiate all enabled plugins."""
        stmt = select(Plugin).where(Plugin.enabled == True)
        result = self.db.execute(stmt)
        enabled_plugins = result.scalars().all()
        
        for db_plugin in enabled_plugins:
            try:
                await self._load_plugin(db_plugin.id)
            except Exception as e:
                logger.error(f"Failed to load enabled plugin {db_plugin.id}: {e}")
    
    async def _load_plugin(self, plugin_id: str):
        """
        Load and instantiate a plugin.
        
        Args:
            plugin_id: Plugin identifier
        """
        if plugin_id in self.plugin_instances:
            logger.warning(f"Plugin {plugin_id} already loaded")
            return
        
        # Get plugin config from DB
        stmt = select(Plugin).where(Plugin.id == plugin_id)
        result = self.db.execute(stmt)
        db_plugin = result.scalar_one_or_none()
        
        if not db_plugin:
            raise ValueError(f"Plugin {plugin_id} not found in database")
        
        # Instantiate plugin
        config = db_plugin.config if db_plugin.config else {}
        plugin = self.loader.instantiate_plugin(plugin_id, config)
        
        if not plugin:
            raise ValueError(f"Failed to instantiate plugin {plugin_id}")
        
        # Enable plugin
        await plugin.on_enable()
        
        # Store instance
        self.plugin_instances[plugin_id] = plugin
        
        logger.info(f"Loaded plugin: {plugin_id}")
    
    async def enable_plugin(self, plugin_id: str, tenant_id: str = "default") -> bool:
        """
        Enable a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update database
            stmt = select(Plugin).where(Plugin.id == plugin_id)
            result = self.db.execute(stmt)
            db_plugin = result.scalar_one_or_none()
            
            if not db_plugin:
                logger.error(f"Plugin {plugin_id} not found")
                return False
            
            db_plugin.enabled = True
            self.db.commit()
            
            # Load plugin
            await self._load_plugin(plugin_id)
            
            logger.info(f"Enabled plugin: {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable plugin {plugin_id}: {e}")
            self.db.rollback()
            return False
    
    async def disable_plugin(self, plugin_id: str, tenant_id: str = "default") -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update database
            stmt = select(Plugin).where(Plugin.id == plugin_id)
            result = self.db.execute(stmt)
            db_plugin = result.scalar_one_or_none()
            
            if not db_plugin:
                logger.error(f"Plugin {plugin_id} not found")
                return False
            
            db_plugin.enabled = False
            self.db.commit()
            
            # Unload plugin
            if plugin_id in self.plugin_instances:
                plugin = self.plugin_instances[plugin_id]
                await plugin.on_disable()
                del self.plugin_instances[plugin_id]
            
            logger.info(f"Disabled plugin: {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable plugin {plugin_id}: {e}")
            self.db.rollback()
            return False
    
    async def execute_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Execute a plugin and store results.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Execution result
        """
        if plugin_id not in self.plugin_instances:
            return {
                "success": False,
                "error": f"Plugin {plugin_id} not loaded or not enabled"
            }
        
        plugin = self.plugin_instances[plugin_id]
        
        # Create execution record
        execution = PluginExecution(
            plugin_id=plugin_id,
            started_at=datetime.utcnow(),
            status="running"
        )
        self.db.add(execution)
        self.db.commit()
        
        try:
            # Execute plugin
            result = await plugin.execute()
            
            # Update execution record
            execution.completed_at = datetime.utcnow()
            execution.status = "success" if result.get("success") else "failed"
            execution.error_message = result.get("error")
            
            # Store metrics if successful
            if result.get("success") and result.get("data"):
                metric = PluginMetric(
                    plugin_id=plugin_id,
                    timestamp=datetime.utcnow(),
                    data=result["data"]
                )
                self.db.add(metric)
                execution.metrics_count = 1
            
            self.db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Plugin execution failed for {plugin_id}: {e}")
            
            execution.completed_at = datetime.utcnow()
            execution.status = "failed"
            execution.error_message = str(e)
            self.db.commit()
            
            return {
                "success": False,
                "error": str(e),
                "plugin_id": plugin_id
            }
    
    async def check_plugin_health(self, plugin_id: str) -> Dict[str, Any]:
        """
        Check plugin health and update database.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Health check result
        """
        if plugin_id not in self.plugin_instances:
            return {
                "healthy": False,
                "message": "Plugin not loaded"
            }
        
        plugin = self.plugin_instances[plugin_id]
        
        try:
            health = await plugin.health_check()
            
            # Update database
            stmt = select(Plugin).where(Plugin.id == plugin_id)
            result = self.db.execute(stmt)
            db_plugin = result.scalar_one_or_none()
            
            if db_plugin:
                db_plugin.last_health_check = datetime.utcnow()
                db_plugin.health_status = "healthy" if health.get("healthy") else "unhealthy"
                db_plugin.health_message = health.get("message")
                self.db.commit()
            
            return health
            
        except Exception as e:
            logger.error(f"Health check failed for {plugin_id}: {e}")
            return {
                "healthy": False,
                "message": f"Health check error: {str(e)}"
            }
    
    def list_plugins(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """
        List all registered plugins.
        
        Returns:
            List of plugin information dictionaries
        """
        stmt = select(Plugin)
        result = self.db.execute(stmt)
        plugins = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "category": p.category,
                "description": p.description,
                "enabled": p.enabled,
                "external": p.external,
                "health_status": p.health_status,
                "last_health_check": p.last_health_check.isoformat() if p.last_health_check else None
            }
            for p in plugins
        ]
    
    def get_plugin_info(self, plugin_id: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get detailed plugin information.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin information dictionary or None
        """
        stmt = select(Plugin).where(Plugin.id == plugin_id)
        result = self.db.execute(stmt)
        plugin = result.scalar_one_or_none()
        
        if not plugin:
            return None
        
        return {
            "id": plugin.id,
            "name": plugin.name,
            "version": plugin.version,
            "category": plugin.category,
            "description": plugin.description,
            "author": plugin.author,
            "enabled": plugin.enabled,
            "external": plugin.external,
            "metadata": plugin.plugin_metadata,
            "config": plugin.config,
            "health_status": plugin.health_status,
            "health_message": plugin.health_message,
            "last_health_check": plugin.last_health_check.isoformat() if plugin.last_health_check else None,
            "last_error": plugin.last_error,
            "installed_at": plugin.installed_at.isoformat() if plugin.installed_at else None,
            "updated_at": plugin.updated_at.isoformat() if plugin.updated_at else None
        }
    
    async def update_plugin_config(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """
        Update plugin configuration.
        
        Args:
            plugin_id: Plugin identifier
            config: New configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stmt = select(Plugin).where(Plugin.id == plugin_id)
            result = self.db.execute(stmt)
            db_plugin = result.scalar_one_or_none()
            
            if not db_plugin:
                return False
            
            # Validate config if plugin is loaded
            if plugin_id in self.plugin_instances:
                plugin = self.plugin_instances[plugin_id]
                if not await plugin.validate_config(config):
                    logger.error(f"Invalid config for plugin {plugin_id}")
                    return False
                
                # Notify plugin of config change
                await plugin.on_config_change(config)
            
            # Update database
            db_plugin.config = config
            db_plugin.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated config for plugin {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config for {plugin_id}: {e}")
            self.db.rollback()
            return False
    
    async def register_external_plugin(self, metadata: Dict[str, Any]) -> bool:
        """
        Register an external plugin.
        
        Args:
            metadata: Plugin metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            plugin_id = metadata.get("id")
            if not plugin_id:
                logger.error("Plugin metadata missing 'id' field")
                return False
            
            # Check if already exists
            stmt = select(Plugin).where(Plugin.id == plugin_id)
            result = self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.warning(f"External plugin {plugin_id} already registered")
                return False
            
            # Create plugin entry
            plugin = Plugin(
                id=plugin_id,
                name=metadata.get("name", plugin_id),
                version=metadata.get("version", "1.0.0"),
                category=metadata.get("category", "custom"),
                description=metadata.get("description", ""),
                author=metadata.get("author", "Unknown"),
                external=True,
                metadata=metadata,
                enabled=False
            )
            
            self.db.add(plugin)
            self.db.commit()
            
            logger.info(f"Registered external plugin: {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register external plugin: {e}")
            self.db.rollback()
            return False
    
    async def shutdown(self):
        """Shutdown plugin manager and cleanup."""
        logger.info("Shutting down plugin manager...")
        
        # Disable all loaded plugins
        for plugin_id in list(self.plugin_instances.keys()):
            try:
                plugin = self.plugin_instances[plugin_id]
                await plugin.on_disable()
            except Exception as e:
                logger.error(f"Error disabling plugin {plugin_id}: {e}")
        
        self.plugin_instances.clear()
        logger.info("Plugin manager shutdown complete")
