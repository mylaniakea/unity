"""Plugin Registry API

Provides plugin discovery, metadata, and management endpoints.
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import importlib
import os
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()


class PluginInfo(BaseModel):
    """Plugin information model."""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    tags: List[str]
    requires_sudo: bool
    supported_os: List[str]
    dependencies: List[str]
    installed: bool = True
    enabled: bool = False
    config_schema: Dict[str, Any] = {}


class PluginCategory(BaseModel):
    """Plugin category information."""
    name: str
    count: int
    plugins: List[str]


class PluginSearchResult(BaseModel):
    """Search result model."""
    total: int
    plugins: List[PluginInfo]


def _discover_plugins() -> List[PluginInfo]:
    """Discover all available builtin plugins."""
    plugins = []
    builtin_dir = Path(__file__).parent.parent.parent / "plugins" / "builtin"
    
    if not builtin_dir.exists():
        logger.warning(f"Builtin plugins directory not found: {builtin_dir}")
        return plugins
    
    for file in builtin_dir.glob("*.py"):
        if file.name.startswith("_") or file.name == "README.md":
            continue
        
        try:
            # Import the plugin module
            module_name = f"app.plugins.builtin.{file.stem}"
            module = importlib.import_module(module_name)
            
            # Find the plugin class
            for attr_name in dir(module):
                if attr_name.endswith("Plugin") and not attr_name.startswith("_"):
                    plugin_class = getattr(module, attr_name)
                    
                    # Instantiate and get metadata
                    try:
                        plugin_instance = plugin_class(config={})
                        metadata = plugin_instance.get_metadata()
                        
                        plugins.append(PluginInfo(
                            id=metadata.id,
                            name=metadata.name,
                            version=metadata.version,
                            description=metadata.description,
                            author=metadata.author,
                            category=metadata.category.value if hasattr(metadata.category, 'value') else str(metadata.category),
                            tags=metadata.tags,
                            requires_sudo=metadata.requires_sudo,
                            supported_os=metadata.supported_os,
                            dependencies=metadata.dependencies,
                            installed=True,
                            enabled=False,  # TODO: Check actual enabled status
                            config_schema=metadata.config_schema
                        ))
                        break  # Found the plugin class, move to next file
                    except Exception as e:
                        logger.warning(f"Failed to instantiate plugin {attr_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load plugin from {file.name}: {e}")
    
    return plugins


@router.get("/", response_model=PluginSearchResult)
async def list_plugins(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    skip: int = Query(0, ge=0, description="Number of plugins to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of plugins to return")
):
    """
    List all available plugins with optional filtering.
    
    Returns plugin metadata including ID, name, version, category, and installation status.
    """
    plugins = _discover_plugins()
    
    # Apply filters
    if category:
        plugins = [p for p in plugins if p.category.lower() == category.lower()]
    
    if tag:
        plugins = [p for p in plugins if tag.lower() in [t.lower() for t in p.tags]]
    
    if enabled is not None:
        plugins = [p for p in plugins if p.enabled == enabled]
    
    # Pagination
    total = len(plugins)
    plugins = plugins[skip:skip + limit]
    
    return PluginSearchResult(total=total, plugins=plugins)


@router.get("/categories", response_model=List[PluginCategory])
async def list_categories():
    """
    List all plugin categories with plugin counts.
    
    Returns a list of categories and the number of plugins in each.
    """
    plugins = _discover_plugins()
    
    # Group by category
    categories: Dict[str, List[str]] = {}
    for plugin in plugins:
        cat = plugin.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(plugin.id)
    
    # Convert to response format
    result = [
        PluginCategory(name=cat, count=len(plugin_ids), plugins=plugin_ids)
        for cat, plugin_ids in sorted(categories.items())
    ]
    
    return result


@router.get("/search", response_model=PluginSearchResult)
async def search_plugins(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results")
):
    """
    Search plugins by name, description, or tags.
    
    Performs case-insensitive search across plugin metadata.
    """
    plugins = _discover_plugins()
    query = q.lower()
    
    # Search in name, description, and tags
    matches = []
    for plugin in plugins:
        if (query in plugin.name.lower() or
            query in plugin.description.lower() or
            query in plugin.id.lower() or
            any(query in tag.lower() for tag in plugin.tags)):
            matches.append(plugin)
    
    total = len(matches)
    matches = matches[:limit]
    
    return PluginSearchResult(total=total, plugins=matches)


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str):
    """
    Get detailed information about a specific plugin.
    
    Returns complete plugin metadata including configuration schema.
    """
    plugins = _discover_plugins()
    
    for plugin in plugins:
        if plugin.id == plugin_id:
            return plugin
    
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")


@router.post("/{plugin_id}/install")
async def install_plugin(plugin_id: str):
    """
    Install a plugin (placeholder for future marketplace).
    
    Currently all builtin plugins are pre-installed.
    Returns installation status.
    """
    plugins = _discover_plugins()
    
    for plugin in plugins:
        if plugin.id == plugin_id:
            if plugin.installed:
                return {
                    "success": True,
                    "plugin_id": plugin_id,
                    "message": "Plugin is already installed",
                    "installed": True
                }
            else:
                # TODO: Implement actual installation logic
                return {
                    "success": True,
                    "plugin_id": plugin_id,
                    "message": "Plugin installation initiated",
                    "installed": True
                }
    
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found in registry")


@router.delete("/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str):
    """
    Uninstall a plugin (placeholder for future marketplace).
    
    Builtin plugins cannot be uninstalled, only disabled.
    Returns uninstallation status.
    """
    plugins = _discover_plugins()
    
    for plugin in plugins:
        if plugin.id == plugin_id:
            # Builtin plugins can't be uninstalled
            raise HTTPException(
                status_code=400,
                detail="Builtin plugins cannot be uninstalled. Use the disable endpoint instead."
            )
    
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")


@router.get("/{plugin_id}/dependencies")
async def get_plugin_dependencies(plugin_id: str):
    """
    Get plugin dependencies and their installation status.
    
    Checks if required Python packages are available.
    """
    plugins = _discover_plugins()
    
    for plugin in plugins:
        if plugin.id == plugin_id:
            dependencies = []
            
            for dep in plugin.dependencies:
                try:
                    importlib.import_module(dep)
                    installed = True
                except ImportError:
                    installed = False
                
                dependencies.append({
                    "name": dep,
                    "required": True,
                    "installed": installed
                })
            
            return {
                "plugin_id": plugin_id,
                "dependencies": dependencies,
                "all_satisfied": all(d["installed"] for d in dependencies)
            }
    
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")


@router.get("/{plugin_id}/compatibility")
async def check_plugin_compatibility(plugin_id: str):
    """
    Check if plugin is compatible with current system.
    
    Verifies OS compatibility and dependency availability.
    """
    import platform
    
    plugins = _discover_plugins()
    
    for plugin in plugins:
        if plugin.id == plugin_id:
            current_os = platform.system().lower()
            
            # Map platform.system() to plugin OS names
            os_map = {
                "linux": "linux",
                "darwin": "darwin",
                "windows": "windows"
            }
            
            system_os = os_map.get(current_os, current_os)
            os_compatible = system_os in plugin.supported_os if plugin.supported_os else True
            
            # Check dependencies
            missing_deps = []
            for dep in plugin.dependencies:
                try:
                    importlib.import_module(dep)
                except ImportError:
                    missing_deps.append(dep)
            
            deps_satisfied = len(missing_deps) == 0
            
            return {
                "plugin_id": plugin_id,
                "compatible": os_compatible and deps_satisfied,
                "os_compatible": os_compatible,
                "current_os": system_os,
                "supported_os": plugin.supported_os,
                "dependencies_satisfied": deps_satisfied,
                "missing_dependencies": missing_deps,
                "requires_sudo": plugin.requires_sudo
            }
    
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
