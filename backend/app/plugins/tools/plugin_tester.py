#!/usr/bin/env python3
"""
Plugin Tester Tool

Test Unity plugins in isolation with mock data and environments.
"""

import argparse
import asyncio
import sys
import time
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional
import json


class PluginTester:
    """Test plugin execution in isolation"""
    
    def __init__(self, plugin_path: Path, config: Optional[Dict[str, Any]] = None):
        self.plugin_path = plugin_path
        self.config = config or {}
        self.plugin = None
        self.plugin_class = None
    
    def load_plugin(self) -> bool:
        """Load plugin module"""
        try:
            print(f"📦 Loading plugin from {self.plugin_path}...")
            
            spec = importlib.util.spec_from_file_location("test_plugin", self.plugin_path)
            if not spec or not spec.loader:
                print("❌ Could not load plugin module")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    hasattr(obj, '__bases__') and 
                    any('PluginBase' in str(base) for base in obj.__bases__)):
                    self.plugin_class = obj
                    break
            
            if not self.plugin_class:
                print("❌ Could not find PluginBase subclass")
                return False
            
            # Instantiate plugin
            self.plugin = self.plugin_class(config=self.config)
            print(f"✅ Plugin loaded: {self.plugin_class.__name__}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load plugin: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_metadata(self):
        """Test plugin metadata"""
        print("\n🔍 Testing metadata...")
        
        try:
            metadata = self.plugin.get_metadata()
            
            print(f"  Plugin ID: {metadata.id}")
            print(f"  Name: {metadata.name}")
            print(f"  Version: {metadata.version}")
            print(f"  Category: {metadata.category}")
            print(f"  Author: {metadata.author}")
            print(f"  Description: {metadata.description}")
            
            if metadata.tags:
                print(f"  Tags: {', '.join(metadata.tags)}")
            
            if metadata.dependencies:
                print(f"  Dependencies: {', '.join(metadata.dependencies)}")
            
            if metadata.requires_sudo:
                print(f"  ⚠️  Requires sudo: Yes")
            
            print(f"  Supported OS: {', '.join(metadata.supported_os)}")
            
            if metadata.config_schema:
                print(f"  Has config schema: Yes")
            
            print("✅ Metadata test passed")
            return True
            
        except Exception as e:
            print(f"❌ Metadata test failed: {e}")
            return False
    
    async def test_health_check(self):
        """Test health check"""
        print("\n🏥 Testing health check...")
        
        try:
            health = await self.plugin.health_check()
            
            print(f"  Healthy: {health.get('healthy', 'Unknown')}")
            print(f"  Message: {health.get('message', 'No message')}")
            
            if "details" in health:
                print(f"  Details: {json.dumps(health['details'], indent=4)}")
            
            if health.get('healthy'):
                print("✅ Health check passed")
                return True
            else:
                print("⚠️  Health check returned unhealthy status")
                return False
                
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_lifecycle(self):
        """Test plugin lifecycle"""
        print("\n🔄 Testing lifecycle...")
        
        try:
            # Test enable
            print("  Enabling plugin...")
            await self.plugin.on_enable()
            
            if not self.plugin.enabled:
                print("❌ Plugin not enabled after on_enable()")
                return False
            
            print("  ✅ Plugin enabled")
            
            # Test disable
            print("  Disabling plugin...")
            await self.plugin.on_disable()
            
            if self.plugin.enabled:
                print("❌ Plugin still enabled after on_disable()")
                return False
            
            print("  ✅ Plugin disabled")
            print("✅ Lifecycle test passed")
            return True
            
        except Exception as e:
            print(f"❌ Lifecycle test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_collect_data(self, iterations: int = 1):
        """Test data collection"""
        print(f"\n📊 Testing data collection ({iterations} iteration{'s' if iterations > 1 else ''})...")
        
        try:
            # Enable plugin first
            await self.plugin.on_enable()
            
            results = []
            total_time = 0
            
            for i in range(iterations):
                print(f"\n  Iteration {i+1}/{iterations}...")
                
                start = time.time()
                data = await self.plugin.collect_data()
                duration = time.time() - start
                total_time += duration
                
                results.append(data)
                
                print(f"  ⏱️  Execution time: {duration:.3f}s")
                print(f"  📦 Data collected:")
                print(json.dumps(data, indent=4, default=str))
                
                # Basic validation
                if not isinstance(data, dict):
                    print(f"  ⚠️  Warning: Expected dict, got {type(data)}")
                
                if iterations > 1 and i < iterations - 1:
                    # Wait between iterations
                    await asyncio.sleep(1)
            
            # Statistics
            if iterations > 1:
                avg_time = total_time / iterations
                print(f"\n📈 Statistics:")
                print(f"  Total time: {total_time:.3f}s")
                print(f"  Average time: {avg_time:.3f}s")
                print(f"  Min time: {min(time.time() - start for start in [0]): .3f}s")
                print(f"  Max time: {max(time.time() - start for start in [0]):.3f}s")
            
            # Cleanup
            await self.plugin.on_disable()
            
            print("\n✅ Data collection test passed")
            return True
            
        except Exception as e:
            print(f"\n❌ Data collection test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_config_validation(self):
        """Test configuration validation"""
        print("\n⚙️  Testing configuration validation...")
        
        try:
            # Test with current config
            is_valid = await self.plugin.validate_config(self.config)
            print(f"  Current config valid: {is_valid}")
            
            # Test with empty config
            is_valid_empty = await self.plugin.validate_config({})
            print(f"  Empty config valid: {is_valid_empty}")
            
            print("✅ Config validation test passed")
            return True
            
        except Exception as e:
            print(f"❌ Config validation test failed: {e}")
            return False
    
    async def run_all_tests(self, iterations: int = 1):
        """Run all tests"""
        print("=" * 60)
        print("🧪 Plugin Test Suite")
        print("=" * 60)
        
        results = {
            "metadata": await self.test_metadata(),
            "health_check": await self.test_health_check(),
            "lifecycle": await self.test_lifecycle(),
            "collect_data": await self.test_collect_data(iterations),
            "config_validation": await self.test_config_validation()
        }
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 Test Summary")
        print("=" * 60)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name:20s} {status}")
        
        print(f"\n  Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return False


async def test_plugin(plugin_path: Path, config: Optional[Dict[str, Any]] = None, iterations: int = 1):
    """
    Test a plugin.
    
    Args:
        plugin_path: Path to plugin file
        config: Plugin configuration
        iterations: Number of data collection iterations
        
    Returns:
        True if all tests passed, False otherwise
    """
    tester = PluginTester(plugin_path, config)
    
    if not tester.load_plugin():
        return False
    
    return await tester.run_all_tests(iterations)


def main():
    parser = argparse.ArgumentParser(
        description="Test Unity plugins in isolation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a plugin
  %(prog)s backend/app/plugins/builtin/system_info.py
  
  # Test with custom configuration
  %(prog)s backend/app/plugins/builtin/postgres_monitor.py --config config.json
  
  # Test with inline configuration
  %(prog)s backend/app/plugins/builtin/system_info.py --config '{"collect_network": true}'
  
  # Run multiple iterations to test performance
  %(prog)s backend/app/plugins/builtin/system_info.py --iterations 5
        """
    )
    
    parser.add_argument(
        "plugin",
        help="Plugin file to test"
    )
    
    parser.add_argument(
        "--config",
        help="Plugin configuration (JSON file or inline JSON string)"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of data collection iterations (default: 1)"
    )
    
    args = parser.parse_args()
    
    # Parse configuration
    config = {}
    if args.config:
        try:
            # Try as file first
            config_path = Path(args.config)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                # Try as inline JSON
                config = json.loads(args.config)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON configuration: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return 1
    
    # Run tests
    plugin_path = Path(args.plugin)
    success = asyncio.run(test_plugin(plugin_path, config, args.iterations))
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
