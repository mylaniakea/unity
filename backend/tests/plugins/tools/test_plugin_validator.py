"""
Unit tests for plugin_validator.py

Tests the PluginValidator tool which validates plugin code structure,
required methods, async detection, and metadata.
"""

import pytest
import tempfile
from pathlib import Path
from app.plugins.tools.plugin_validator import PluginValidator, ValidationResult


# Sample valid plugin code
VALID_PLUGIN = '''
from app.plugins.base import PluginBase
from typing import Dict, Any

class TestPlugin(PluginBase):
    """Test plugin."""
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "category": "SYSTEM"
        }
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect data."""
        return {"test": "data"}
'''

# Plugin with sync collect_data (should fail)
SYNC_COLLECT_DATA_PLUGIN = '''
from app.plugins.base import PluginBase
from typing import Dict, Any

class TestPlugin(PluginBase):
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "category": "SYSTEM"
        }
    
    def collect_data(self) -> Dict[str, Any]:
        """Sync method - should fail validation."""
        return {"test": "data"}
'''

# Plugin missing required methods
MISSING_METHODS_PLUGIN = '''
from app.plugins.base import PluginBase
from typing import Dict, Any

class TestPlugin(PluginBase):
    """Plugin missing collect_data method."""
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "category": "SYSTEM"
        }
'''

# Plugin with no PluginBase inheritance
NO_INHERITANCE_PLUGIN = '''
from typing import Dict, Any

class TestPlugin:
    """Not inheriting from PluginBase."""
    
    def get_metadata(self) -> Dict[str, Any]:
        return {}
    
    async def collect_data(self) -> Dict[str, Any]:
        return {}
'''


class TestPluginValidator:
    """Tests for PluginValidator."""
    
    def test_valid_plugin(self):
        """Test validation of a valid plugin."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(VALID_PLUGIN)
            plugin_path = f.name
        
        try:
            validator = PluginValidator(plugin_path)
            result = validator.validate()
            
            # Should pass validation (warnings/info are ok)
            assert not result.errors, f"Expected no errors, got: {result.errors}"
            assert result.is_valid()
        finally:
            Path(plugin_path).unlink()
    
    def test_sync_collect_data_fails(self):
        """Test that synchronous collect_data method fails validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(SYNC_COLLECT_DATA_PLUGIN)
            plugin_path = f.name
        
        try:
            validator = PluginValidator(plugin_path)
            result = validator.validate()
            
            # Should have error about collect_data not being async
            assert not result.is_valid()
            assert any("must be async" in err for err in result.errors)
        finally:
            Path(plugin_path).unlink()
    
    def test_missing_methods(self):
        """Test that missing required methods fails validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(MISSING_METHODS_PLUGIN)
            plugin_path = f.name
        
        try:
            validator = PluginValidator(plugin_path)
            result = validator.validate()
            
            # Should have error about missing collect_data
            assert not result.is_valid()
            assert any("collect_data" in err for err in result.errors)
        finally:
            Path(plugin_path).unlink()
    
    def test_no_plugin_base_inheritance(self):
        """Test that plugins not inheriting from PluginBase fail validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(NO_INHERITANCE_PLUGIN)
            plugin_path = f.name
        
        try:
            validator = PluginValidator(plugin_path)
            result = validator.validate()
            
            # Should have error about no PluginBase class
            assert not result.is_valid()
            assert any("PluginBase" in err for err in result.errors)
        finally:
            Path(plugin_path).unlink()
    
    def test_validation_result_is_valid(self):
        """Test ValidationResult.is_valid() method."""
        # No errors = valid
        result = ValidationResult("test.py")
        assert result.is_valid()
        
        # With errors = invalid
        result.add_error("Test error")
        assert not result.is_valid()
        
        # Warnings don't affect validity
        result2 = ValidationResult("test.py")
        result2.add_warning("Test warning")
        assert result2.is_valid()
    
    def test_validation_result_add_messages(self):
        """Test adding different message types to ValidationResult."""
        result = ValidationResult("test.py")
        
        result.add_error("Error message")
        result.add_warning("Warning message")
        result.add_info("Info message")
        
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.info) == 1
        
        assert result.errors[0] == "Error message"
        assert result.warnings[0] == "Warning message"
        assert result.info[0] == "Info message"
    
    def test_invalid_file_path(self):
        """Test validator with non-existent file."""
        with pytest.raises(FileNotFoundError):
            validator = PluginValidator("/nonexistent/file.py")
            validator.validate()
    
    def test_async_function_detection(self):
        """Test that both FunctionDef and AsyncFunctionDef are detected."""
        plugin_with_both = '''
from app.plugins.base import PluginBase
from typing import Dict, Any

class TestPlugin(PluginBase):
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "id": "test",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "category": "SYSTEM"
        }
    
    async def collect_data(self) -> Dict[str, Any]:
        return {}
    
    def health_check(self) -> bool:
        """Sync optional method."""
        return True
    
    async def on_enable(self):
        """Async optional method."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(plugin_with_both)
            plugin_path = f.name
        
        try:
            validator = PluginValidator(plugin_path)
            result = validator.validate()
            
            # Should detect both sync and async methods
            # Should not complain about missing methods
            method_errors = [e for e in result.errors if "Missing required method" in e]
            assert len(method_errors) == 0
        finally:
            Path(plugin_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
