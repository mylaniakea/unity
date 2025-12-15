"""
Unity Plugin System

This package provides the plugin architecture for Unity - Homelab Intelligence Hub.
Plugins can be built-in or external, and all inherit from PluginBase.
"""

from .base import PluginBase, PluginMetadata, PluginCategory
from .loader import PluginLoader
from .hub_client import HubClient

__all__ = [
    "PluginBase",
    "PluginMetadata", 
    "PluginCategory",
    "PluginLoader",
    "HubClient"
]
