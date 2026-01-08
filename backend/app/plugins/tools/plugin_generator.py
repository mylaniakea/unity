#!/usr/bin/env python3
"""
Plugin Generator Tool

Generates boilerplate code for new Unity plugins from templates.
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict


PLUGIN_CATEGORIES = [
    "system", "network", "storage", "thermal", "container",
    "database", "application", "security", "ai_ml", "custom"
]


def get_plugin_template(plugin_info: Dict[str, str]) -> str:
    """Generate plugin code from template"""
    
    category_upper = plugin_info["category"].upper()
    class_name = "".join(word.capitalize() for word in plugin_info["id"].split("-"))
    
    template = f'''"""
{plugin_info["name"]} Plugin

{plugin_info["description"]}

Author: {plugin_info["author"]}
Created: {datetime.now().strftime("%Y-%m-%d")}
"""

from app.plugins.base import PluginBase, PluginMetadata, PluginCategory
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class {class_name}Plugin(PluginBase):
    """{plugin_info["name"]} monitoring plugin"""
    
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        # Initialize plugin-specific attributes here
        self.initialized = False
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            id="{plugin_info["id"]}",
            name="{plugin_info["name"]}",
            version="1.0.0",
            description="{plugin_info["description"]}",
            author="{plugin_info["author"]}",
            category=PluginCategory.{category_upper},
            tags={plugin_info["tags"]},
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=[],
            config_schema={{
                "type": "object",
                "properties": {{
                    # Add configuration properties here
                    # Example:
                    # "interval": {{
                    #     "type": "integer",
                    #     "default": 60,
                    #     "description": "Collection interval in seconds"
                    # }}
                }},
                "required": []
            }}
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """
        Collect plugin data.
        
        Returns:
            Dictionary containing collected metrics
            
        Raises:
            Exception: If data collection fails
        """
        try:
            logger.info(f"Collecting data for {plugin_info["id"]}")
            
            # TODO: Implement your data collection logic here
            data = {{
                "timestamp": datetime.utcnow().isoformat(),
                "status": "active",
                # Add your metrics here
            }}
            
            return data
            
        except Exception as e:
            logger.error(f"Data collection failed: {{str(e)}}", exc_info=True)
            self._last_error = str(e)
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if plugin is healthy and operational.
        
        Returns:
            Dictionary with health status
        """
        try:
            # TODO: Implement health check logic
            # Example: Test connections, check dependencies, etc.
            
            return {{
                "healthy": True,
                "message": "{plugin_info["name"]} is operational",
                "details": {{
                    "last_execution": self._last_execution.isoformat() if self._last_execution else None,
                    "execution_count": self._execution_count
                }}
            }}
        except Exception as e:
            return {{
                "healthy": False,
                "message": f"Health check failed: {{str(e)}}"
            }}
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        # TODO: Implement configuration validation
        # Example: Check required fields, validate values, etc.
        return True
    
    async def on_enable(self):
        """Called when plugin is enabled"""
        await super().on_enable()
        logger.info(f"{plugin_info["id"]} plugin enabled")
        
        # TODO: Initialize resources, connections, etc.
        self.initialized = True
    
    async def on_disable(self):
        """Called when plugin is disabled"""
        logger.info(f"{plugin_info["id"]} plugin disabled")
        
        # TODO: Cleanup resources, close connections, etc.
        self.initialized = False
        
        await super().on_disable()
'''
    
    return template


def get_test_template(plugin_info: Dict[str, str]) -> str:
    """Generate test file template"""
    
    class_name = "".join(word.capitalize() for word in plugin_info["id"].split("-"))
    module_name = plugin_info["id"].replace("-", "_")
    
    template = f'''"""
Tests for {plugin_info["name"]} Plugin
"""

import pytest
from app.plugins.builtin.{module_name} import {class_name}Plugin
from app.plugins.base import PluginCategory


@pytest.mark.asyncio
async def test_plugin_metadata():
    """Test plugin metadata"""
    plugin = {class_name}Plugin()
    metadata = plugin.get_metadata()
    
    assert metadata.id == "{plugin_info["id"]}"
    assert metadata.name == "{plugin_info["name"]}"
    assert metadata.version == "1.0.0"
    assert metadata.category == PluginCategory.{plugin_info["category"].upper()}
    assert metadata.author == "{plugin_info["author"]}"


@pytest.mark.asyncio
async def test_plugin_initialization():
    """Test plugin initialization"""
    plugin = {class_name}Plugin()
    
    assert plugin.enabled is False
    assert plugin._execution_count == 0
    assert plugin._last_error is None


@pytest.mark.asyncio
async def test_collect_data():
    """Test data collection"""
    plugin = {class_name}Plugin()
    await plugin.on_enable()
    
    data = await plugin.collect_data()
    
    assert "timestamp" in data
    assert "status" in data
    # Add more assertions for your specific metrics


@pytest.mark.asyncio
async def test_health_check():
    """Test health check"""
    plugin = {class_name}Plugin()
    
    health = await plugin.health_check()
    
    assert "healthy" in health
    assert "message" in health
    assert health["healthy"] is True


@pytest.mark.asyncio
async def test_config_validation():
    """Test configuration validation"""
    plugin = {class_name}Plugin()
    
    # Test valid config
    valid_config = {{}}
    assert await plugin.validate_config(valid_config) is True
    
    # TODO: Add tests for invalid configurations


@pytest.mark.asyncio
async def test_lifecycle():
    """Test plugin lifecycle"""
    plugin = {class_name}Plugin()
    
    # Test enable
    await plugin.on_enable()
    assert plugin.enabled is True
    
    # Test disable
    await plugin.on_disable()
    assert plugin.enabled is False
'''
    
    return template


def create_plugin(args):
    """Create a new plugin from template"""
    
    # Prepare plugin info
    plugin_info = {
        "id": args.id,
        "name": args.name,
        "description": args.description or f"Monitors {args.name.lower()}",
        "author": args.author,
        "category": args.category,
        "tags": args.tags or [args.category, "monitoring"]
    }
    
    # Determine output paths
    if args.output:
        output_dir = Path(args.output)
    else:
        # Default to builtin plugins directory
        script_dir = Path(__file__).parent.parent
        output_dir = script_dir / "builtin"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filenames
    module_name = args.id.replace("-", "_")
    plugin_file = output_dir / f"{module_name}.py"
    test_file = output_dir.parent.parent.parent / "tests" / "plugins" / f"test_{module_name}.py"
    
    # Check if files exist
    if plugin_file.exists() and not args.force:
        print(f"Error: Plugin file {plugin_file} already exists. Use --force to overwrite.")
        return 1
    
    # Generate plugin code
    plugin_code = get_plugin_template(plugin_info)
    
    # Write plugin file
    with open(plugin_file, 'w') as f:
        f.write(plugin_code)
    
    print(f"✅ Created plugin: {plugin_file}")
    
    # Generate and write test file if requested
    if not args.no_tests:
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_code = get_test_template(plugin_info)
        
        with open(test_file, 'w') as f:
            f.write(test_code)
        
        print(f"✅ Created tests: {test_file}")
    
    # Print next steps
    print(f"""
🎉 Plugin '{args.id}' created successfully!

Next steps:
1. Implement data collection logic in {plugin_file}
2. Add configuration schema if needed
3. {'Run tests: pytest ' + str(test_file) if not args.no_tests else 'Create tests for your plugin'}
4. Start Unity to test: uvicorn app.main:app --reload
5. Enable plugin: curl -X POST http://localhost:8000/api/v1/plugins/{args.id}/enable

Documentation:
- Plugin Development Guide: docs/PLUGIN_DEVELOPMENT.md
- Built-in Plugins Catalog: docs/BUILTIN_PLUGINS.md
""")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate a new Unity plugin from template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a simple custom plugin
  %(prog)s --id my-plugin --name "My Plugin" --category custom --author "Your Name"
  
  # Generate a database monitoring plugin
  %(prog)s --id postgres-monitor --name "PostgreSQL Monitor" --category database
  
  # Generate plugin in custom directory
  %(prog)s --id my-plugin --name "My Plugin" --output /path/to/plugins
        """
    )
    
    parser.add_argument(
        "--id",
        required=True,
        help="Plugin ID (kebab-case, e.g., 'my-plugin')"
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help="Human-readable plugin name (e.g., 'My Plugin')"
    )
    
    parser.add_argument(
        "--category",
        choices=PLUGIN_CATEGORIES,
        default="custom",
        help="Plugin category"
    )
    
    parser.add_argument(
        "--author",
        default="Unity Team",
        help="Plugin author name"
    )
    
    parser.add_argument(
        "--description",
        help="Plugin description (auto-generated if not provided)"
    )
    
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Plugin tags for search"
    )
    
    parser.add_argument(
        "--output",
        help="Output directory (defaults to builtin plugins directory)"
    )
    
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Don't generate test file"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files"
    )
    
    args = parser.parse_args()
    
    # Validate plugin ID format
    if not all(c.isalnum() or c == "-" for c in args.id):
        print("Error: Plugin ID must be kebab-case (lowercase with hyphens)")
        return 1
    
    return create_plugin(args)


if __name__ == "__main__":
    sys.exit(main())
