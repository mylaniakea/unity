# Afternoon Session Plan - December 17, 2025

## Session Overview
**Goal**: Complete BUILTIN_PLUGINS.md documentation and fix plugin validator

**Estimated Time**: 1-2 hours

---

## Priority Tasks

### 1. Complete BUILTIN_PLUGINS.md Documentation (45 min)

**Status**: Partially complete - need to add detailed sections for remaining plugins

**Current State**:
- ✅ Quick reference table
- ✅ System Info detailed section
- ✅ Process Monitor detailed section
- ❌ Missing detailed sections for 13+ other plugins

**Tasks**:
1. Add detailed sections for remaining plugins:
   - Thermal Monitor
   - Network Monitor
   - Disk Monitor
   - Docker Monitor
   - PostgreSQL Monitor
   - MySQL Monitor
   - MongoDB Monitor
   - Redis Monitor
   - InfluxDB Monitor
   - SQLite Monitor
   - Web Service Monitor
   - Log Monitor
   - **Auth Monitor** (NEW)
   - **Firewall Monitor** (NEW)

**Template for each plugin**:
```markdown
### Plugin Name

**Plugin ID:** `plugin-id`  
**Version:** 1.0.0  
**Dependencies:** `dependency1, dependency2`

Brief description of what the plugin monitors.

#### Metrics

- **Metric Category 1**: Description
- **Metric Category 2**: Description
- **Metric Category 3**: Description

#### Configuration

```json
{
  "config_option_1": value,
  "config_option_2": value
}
```

Options:
- `option_1`: Description (default: value)
- `option_2`: Description (default: value)

#### Example Output

```json
{
  "example": "output"
}
```

#### Use Cases

- Use case 1
- Use case 2
- Use case 3
```

**How to gather info**:
```bash
# Read each plugin file to get metadata, config schema, and understand metrics
cat backend/app/plugins/builtin/PLUGIN_NAME.py

# Look for get_metadata() to get:
# - id, name, version, description
# - dependencies
# - config_schema

# Look at collect_data() to understand:
# - What metrics are collected
# - Output structure
```

---

### 2. Fix Plugin Validator AsyncFunctionDef Detection (15 min)

**Issue**: Validator doesn't properly detect async methods in plugin class body

**Current Bug**: 
- Line 115-117 in `plugin_validator.py` only checks `ast.FunctionDef`
- Should also check `ast.AsyncFunctionDef`

**Fix Location**: `backend/app/plugins/tools/plugin_validator.py`

**Solution**:
Replace lines ~110-130 in `_check_required_methods()`:

```python
def _check_required_methods(self, tree: ast.AST):
    """Check required methods exist"""
    if not hasattr(self, 'plugin_class'):
        return
    
    # Collect both sync and async methods
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
                self.result.add_error(f"Method '{method_name}' must be async")
    
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
```

**Test the fix**:
```bash
cd backend
source .venv_new/bin/activate
python -m app.plugins.tools.plugin_validator app/plugins/builtin/auth_monitor.py
python -m app.plugins.tools.plugin_validator app/plugins/builtin/firewall_monitor.py
python -m app.plugins.tools.plugin_validator app/plugins/builtin/system_info.py
```

---

### 3. Add Unit Tests for Plugin Tools (Optional, 30 min)

**If time permits**, add basic tests for the tools:

**Create**: `backend/tests/plugins/tools/test_plugin_generator.py`

```python
import pytest
import tempfile
from pathlib import Path
from app.plugins.tools import plugin_generator

def test_create_plugin():
    """Test plugin generation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        args = type('Args', (), {
            'id': 'test-plugin',
            'name': 'Test Plugin',
            'category': 'custom',
            'author': 'Test',
            'description': 'Test description',
            'tags': ['test'],
            'output': tmpdir,
            'no_tests': True,
            'force': False
        })()
        
        result = plugin_generator.create_plugin(args)
        assert result == 0
        
        plugin_file = Path(tmpdir) / "test_plugin.py"
        assert plugin_file.exists()
        
        # Verify content
        content = plugin_file.read_text()
        assert "class TestPluginPlugin(PluginBase):" in content
        assert "id=\"test-plugin\"" in content
```

**Create**: `backend/tests/plugins/tools/test_plugin_validator.py`

```python
import pytest
from pathlib import Path
from app.plugins.tools.plugin_validator import PluginValidator

def test_validate_valid_plugin():
    """Test validator on valid plugin"""
    plugin_path = Path("app/plugins/builtin/system_info.py")
    validator = PluginValidator(plugin_path)
    result = validator.validate()
    
    assert result.is_valid()
    assert len(result.errors) == 0
```

---

## Quick Wins (If Extra Time)

### 4. Add README badges and stats (10 min)

Update `README.md` with:
- Plugin count badge
- Documentation links
- Quick stats

### 5. Update ROADMAP.md (5 min)

Mark completed items:
- ✅ Plugin documentation
- ✅ Plugin development tools
- ✅ Security monitoring plugins

---

## Testing Checklist

Before committing:

```bash
cd backend
source .venv_new/bin/activate

# Test validator fix
python -m app.plugins.tools.plugin_validator app/plugins/builtin/*.py

# Test generator
python -m app.plugins.tools.plugin_generator --id test2 --name "Test2" --output /tmp/test2 --no-tests

# Test tester
python -m app.plugins.tools.plugin_tester app/plugins/builtin/system_info.py

# Run any new tests
pytest tests/plugins/tools/ -v
```

---

## Commit Plan

### Commit 1: Complete BUILTIN_PLUGINS.md
```bash
git add docs/BUILTIN_PLUGINS.md
git commit -m "Complete BUILTIN_PLUGINS.md with all plugin details

- Add detailed sections for all 17 builtin plugins
- Include configuration examples and use cases
- Add security plugin documentation

Co-Authored-By: Warp <agent@warp.dev>"
git push origin main
```

### Commit 2: Fix plugin validator
```bash
git add backend/app/plugins/tools/plugin_validator.py
git commit -m "Fix plugin validator AsyncFunctionDef detection

- Properly detect async methods in plugin class
- Add separate tracking for sync vs async methods
- Fix false positives for async collect_data()

Co-Authored-By: Warp <agent@warp.dev>"
git push origin main
```

### Commit 3: Add tests (if completed)
```bash
git add backend/tests/plugins/tools/
git commit -m "Add unit tests for plugin development tools

- Test plugin generator functionality
- Test plugin validator on valid plugins
- Verify tool CLI interfaces

Co-Authored-By: Warp <agent@warp.dev>"
git push origin main
```

---

## Success Criteria

- [ ] BUILTIN_PLUGINS.md has detailed sections for all 17 plugins
- [ ] Plugin validator correctly validates all builtin plugins
- [ ] All tools pass validation tests
- [ ] Documentation is complete and accurate
- [ ] Changes committed and pushed to GitHub

---

## Future Enhancements (Post-Session Ideas)

1. **More Security Plugins**
   - SELinux/AppArmor monitor
   - fail2ban integration
   - Port scan detector
   - SSL certificate monitor

2. **Cloud Platform Plugins**
   - AWS CloudWatch integration
   - Azure Monitor integration
   - GCP Monitoring integration

3. **Advanced Features**
   - Plugin marketplace/registry
   - Plugin versioning and updates
   - Plugin dependency management
   - Plugin sandboxing

4. **Developer Experience**
   - Plugin hot-reload
   - Plugin debugging tools
   - Performance profiling
   - Integration test framework

---

## Resources

- Plugin Development Guide: `docs/PLUGIN_DEVELOPMENT.md`
- Current Catalog: `docs/BUILTIN_PLUGINS.md`
- Plugin Base: `backend/app/plugins/base.py`
- Example Plugins: `backend/app/plugins/builtin/`
- Session Summary: `SESSION_SUMMARY_2025-12-17.md`

---

**Happy Coding! 🚀**
