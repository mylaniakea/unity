#!/usr/bin/env python3
"""
Plugin Validator Tool

Validates Unity plugin structure, configuration, and code quality.
"""

import argparse
import ast
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json


class ValidationResult:
    """Validation result container"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str):
        self.errors.append(f"❌ ERROR: {message}")
    
    def add_warning(self, message: str):
        self.warnings.append(f"⚠️  WARNING: {message}")
    
    def add_info(self, message: str):
        self.info.append(f"ℹ️  INFO: {message}")
    
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def print_results(self):
        if self.errors:
            print("\n🔴 Validation Failed\n")
            for error in self.errors:
                print(error)
        
        if self.warnings:
            print("\n⚠️  Warnings\n")
            for warning in self.warnings:
                print(warning)
        
        if self.info:
            print("\nℹ️  Information\n")
            for info in self.info:
                print(info)
        
        if self.is_valid() and not self.warnings:
            print("\n✅ Plugin validation passed! No issues found.\n")


class PluginValidator:
    """Validates Unity plugins"""
    
    def __init__(self, plugin_path: Path):
        self.plugin_path = plugin_path
        self.result = ValidationResult()
    
    def validate(self) -> ValidationResult:
        """Run all validation checks"""
        
        # Check file exists
        if not self.plugin_path.exists():
            self.result.add_error(f"Plugin file not found: {self.plugin_path}")
            return self.result
        
        # Check file extension
        if self.plugin_path.suffix != ".py":
            self.result.add_error(f"Plugin must be a Python file (.py): {self.plugin_path}")
            return self.result
        
        # Parse AST
        try:
            with open(self.plugin_path, 'r') as f:
                source = f.read()
            tree = ast.parse(source, filename=str(self.plugin_path))
        except SyntaxError as e:
            self.result.add_error(f"Syntax error in plugin: {e}")
            return self.result
        
        # Run validation checks
        self._check_imports(tree)
        self._check_plugin_class(tree)
        self._check_required_methods(tree)
        self._check_docstrings(tree)
        self._check_code_quality(tree)
        
        # Try to import and validate runtime
        self._validate_runtime()
        
        return self.result
    
    def _check_imports(self, tree: ast.AST):
        """Check required imports"""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        
        required_imports = [
            "app.plugins.base",
            "typing"
        ]
        
        for req_import in required_imports:
            found = any(req_import in imp for imp in imports)
            if not found:
                self.result.add_warning(f"Missing recommended import: {req_import}")
    
    def _check_plugin_class(self, tree: ast.AST):
        """Check for plugin class definition"""
        plugin_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if inherits from PluginBase
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "PluginBase":
                        plugin_classes.append(node)
                    elif isinstance(base, ast.Attribute) and base.attr == "PluginBase":
                        plugin_classes.append(node)
        
        if not plugin_classes:
            self.result.add_error("No class inheriting from PluginBase found")
            return
        
        if len(plugin_classes) > 1:
            self.result.add_warning(f"Multiple plugin classes found: {[c.name for c in plugin_classes]}")
        
        # Check first plugin class
        plugin_class = plugin_classes[0]
        self.result.add_info(f"Found plugin class: {plugin_class.name}")
        
        # Store for later checks
        self.plugin_class = plugin_class
    
    def _check_required_methods(self, tree: ast.AST):
        """Check required methods exist"""
        if not hasattr(self, 'plugin_class'):
            return
        
        # Collect both sync and async methods from class body
        methods = {}
        for node in self.plugin_class.body:
            if isinstance(node, ast.FunctionDef):
                methods[node.name] = ('sync', node)
            elif isinstance(node, ast.AsyncFunctionDef):
                methods[node.name] = ('async', node)
        
        required_methods = {
            "get_metadata": "Returns plugin metadata",
            "collect_data": "Collects plugin data"
        }
        
        for method_name, description in required_methods.items():
            if method_name not in methods:
                self.result.add_error(f"Missing required method: {method_name} ({description})")
            else:
                method_type, method_node = methods[method_name]
                # Check if collect_data is async
                if method_name == "collect_data" and method_type != "async":
                    self.result.add_error(f"Method '{method_name}' must be async (use 'async def')")
                elif method_name == "get_metadata" and method_type == "async":
                    self.result.add_warning(f"Method '{method_name}' is async but typically should be sync")
        
        # Check optional but recommended methods
        recommended_methods = {
            "health_check": "Health check implementation",
            "validate_config": "Configuration validation",
            "on_enable": "Enable lifecycle hook",
            "on_disable": "Disable lifecycle hook"
        }
        
        for method_name, description in recommended_methods.items():
            if method_name not in methods:
                self.result.add_info(f"Optional method not implemented: {method_name} ({description})")
            else:
                method_type, method_node = methods[method_name]
                # Health check should typically be async
                if method_name == "health_check" and method_type != "async":
                    self.result.add_info(f"Method '{method_name}' is sync - consider making it async for consistency")
    
    def _check_docstrings(self, tree: ast.AST):
        """Check for docstrings"""
        if not hasattr(self, 'plugin_class'):
            return
        
        # Check class docstring
        if not ast.get_docstring(self.plugin_class):
            self.result.add_warning(f"Class '{self.plugin_class.name}' missing docstring")
        
        # Check method docstrings
        for node in self.plugin_class.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    self.result.add_warning(f"Method '{node.name}' missing docstring")
    
    def _check_code_quality(self, tree: ast.AST):
        """Check code quality issues"""
        
        # Check for bare except clauses
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.result.add_warning("Bare 'except:' clause found - catch specific exceptions")
        
        # Check for TODO comments
        try:
            with open(self.plugin_path, 'r') as f:
                for i, line in enumerate(f, 1):
                    if "TODO" in line and not line.strip().startswith("#"):
                        self.result.add_info(f"TODO found at line {i}: {line.strip()}")
        except:
            pass
    
    def _validate_runtime(self):
        """Validate plugin at runtime"""
        try:
            # Load module
            spec = importlib.util.spec_from_file_location("plugin_module", self.plugin_path)
            if not spec or not spec.loader:
                self.result.add_error("Could not load plugin module")
                return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    hasattr(obj, '__bases__') and 
                    any('PluginBase' in str(base) for base in obj.__bases__)):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                self.result.add_error("Could not find PluginBase subclass in module")
                return
            
            # Try to instantiate
            try:
                plugin = plugin_class()
                self.result.add_info("Plugin instantiated successfully")
            except Exception as e:
                self.result.add_error(f"Failed to instantiate plugin: {e}")
                return
            
            # Validate metadata
            try:
                metadata = plugin.get_metadata()
                self._validate_metadata(metadata)
            except Exception as e:
                self.result.add_error(f"Failed to get metadata: {e}")
                return
            
        except ImportError as e:
            self.result.add_error(f"Import error: {e}")
        except Exception as e:
            self.result.add_error(f"Runtime validation error: {e}")
    
    def _validate_metadata(self, metadata):
        """Validate plugin metadata"""
        
        # Check required fields
        required_fields = ["id", "name", "version", "description", "author", "category"]
        for field in required_fields:
            if not hasattr(metadata, field) or not getattr(metadata, field):
                self.result.add_error(f"Metadata missing required field: {field}")
        
        # Validate ID format (kebab-case)
        if hasattr(metadata, "id"):
            plugin_id = metadata.id
            if not all(c.isalnum() or c == "-" for c in plugin_id):
                self.result.add_error(f"Plugin ID must be kebab-case: {plugin_id}")
            if plugin_id != plugin_id.lower():
                self.result.add_error(f"Plugin ID must be lowercase: {plugin_id}")
        
        # Validate version format (semver)
        if hasattr(metadata, "version"):
            version = metadata.version
            parts = version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                self.result.add_warning(f"Version should follow semver (X.Y.Z): {version}")
        
        # Check dependencies
        if hasattr(metadata, "dependencies") and metadata.dependencies:
            self.result.add_info(f"Plugin dependencies: {', '.join(metadata.dependencies)}")
        
        # Validate config schema if present
        if hasattr(metadata, "config_schema") and metadata.config_schema:
            try:
                # Basic JSON schema validation
                if not isinstance(metadata.config_schema, dict):
                    self.result.add_error("config_schema must be a dictionary")
                elif "type" not in metadata.config_schema:
                    self.result.add_warning("config_schema should have 'type' field")
                else:
                    self.result.add_info("Plugin has configuration schema")
            except Exception as e:
                self.result.add_error(f"Invalid config_schema: {e}")


def validate_plugin(plugin_path: Path, verbose: bool = False) -> bool:
    """
    Validate a plugin file.
    
    Args:
        plugin_path: Path to plugin file
        verbose: Print detailed output
        
    Returns:
        True if validation passed, False otherwise
    """
    print(f"\n🔍 Validating plugin: {plugin_path}\n")
    
    validator = PluginValidator(plugin_path)
    result = validator.validate()
    
    if verbose or not result.is_valid():
        result.print_results()
    
    return result.is_valid()


def main():
    parser = argparse.ArgumentParser(
        description="Validate Unity plugin structure and code quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single plugin
  %(prog)s backend/app/plugins/builtin/my_plugin.py
  
  # Validate all builtin plugins
  %(prog)s backend/app/plugins/builtin/*.py
  
  # Validate with verbose output
  %(prog)s --verbose backend/app/plugins/builtin/my_plugin.py
        """
    )
    
    parser.add_argument(
        "plugins",
        nargs="+",
        help="Plugin file(s) to validate"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed validation output"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    
    args = parser.parse_args()
    
    # Validate all specified plugins
    all_valid = True
    for plugin_file in args.plugins:
        plugin_path = Path(plugin_file)
        is_valid = validate_plugin(plugin_path, args.verbose)
        
        if not is_valid:
            all_valid = False
    
    # Exit with appropriate code
    if all_valid:
        print("\n✅ All plugins validated successfully!\n")
        return 0
    else:
        print("\n❌ Some plugins failed validation\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
