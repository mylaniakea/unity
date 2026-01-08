"""
Plugin Development Tools

This module provides tools for Unity plugin development:
- plugin_generator: Generate plugin boilerplate from templates
- plugin_validator: Validate plugin structure and code quality
- plugin_tester: Test plugins in isolation

Usage:
    python -m app.plugins.tools.plugin_generator --id my-plugin --name "My Plugin"
    python -m app.plugins.tools.plugin_validator backend/app/plugins/builtin/my_plugin.py
    python -m app.plugins.tools.plugin_tester backend/app/plugins/builtin/my_plugin.py
"""

__version__ = "1.0.0"
__all__ = ["plugin_generator", "plugin_validator", "plugin_tester"]
