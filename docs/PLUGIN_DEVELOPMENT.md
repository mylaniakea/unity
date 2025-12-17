# Plugin Development Guide

This guide covers everything you need to know to develop custom plugins for Unity.

## Table of Contents

- [Quick Start](#quick-start)
- [Plugin Architecture](#plugin-architecture)
- [Creating Your First Plugin](#creating-your-first-plugin)
- [Configuration Schema](#configuration-schema)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Best Practices](#best-practices)
- [Advanced Topics](#advanced-topics)

## Quick Start

### Prerequisites

- Python 3.9+
- Unity backend installed
- Basic understanding of async/await patterns

### Create a Simple Plugin in 5 Minutes

```python
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory
from typing import Dict, Any
from datetime import datetime

class MyPlugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my-plugin",
            name="My Custom Plugin",
            version="1.0.0",
            description="Does something awesome",
            author="Your Name",
            category=PluginCategory.CUSTOM,
            tags=["custom", "monitoring"],
            dependencies=[]
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active",
            "value": 42
        }
```

Save as `backend/app/plugins/builtin/my_plugin.py`, restart Unity, and your plugin is ready!

## Plugin Architecture

### Base Classes

All plugins inherit from `PluginBase` which provides:

- **Metadata Management**: Plugin information and requirements
- **Configuration**: Schema validation and config management
- **Lifecycle Hooks**: Enable, disable, cleanup
- **Health Monitoring**: Built-in health check framework
- **Hub Integration**: Communication with Unity Hub

### Plugin Lifecycle

```
┌──────────┐
│ Discover │ Plugin file found in plugins directory
└────┬─────┘
     │
┌────▼─────┐
│  Load    │ Import module, instantiate class
└────┬─────┘
     │
┌────▼────────┐
│  Configure  │ Apply configuration, validate
└────┬────────┘
     │
┌────▼────────┐
│   Enable    │ on_enable() called, plugin starts
└────┬────────┘
     │
┌────▼──────────┐
│ Execute/Poll  │ collect_data() called periodically
└────┬──────────┘
     │
┌────▼────────┐
│  Disable    │ on_disable() called, cleanup
└─────────────┘
```

## Creating Your First Plugin

### Step 1: Choose Plugin Type

Unity supports several plugin categories:

- **SYSTEM**: CPU, memory, processes
- **NETWORK**: Network interfaces, connections
- **STORAGE**: Disk usage, I/O statistics
- **DATABASE**: Database monitoring
- **APPLICATION**: Service monitoring
- **SECURITY**: Auth, firewall, intrusion detection
- **CUSTOM**: Everything else

### Step 2: Implement Required Methods

Every plugin MUST implement:

#### `get_metadata()` - Plugin Information

```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        id="unique-plugin-id",           # Unique identifier (kebab-case)
        name="Human Readable Name",       # Display name
        version="1.0.0",                  # Semantic version
        description="What it does",       # Brief description
        author="Your Name",               # Author name/org
        category=PluginCategory.SYSTEM,   # Plugin category
        tags=["tag1", "tag2"],           # Search tags
        requires_sudo=False,              # Needs root access?
        supported_os=["linux"],           # OS support
        dependencies=["psutil"],          # Python packages
        config_schema={}                  # JSON schema (optional)
    )
```

#### `collect_data()` - Main Collection Logic

```python
async def collect_data(self) -> Dict[str, Any]:
    """
    Collect and return plugin data.
    
    Returns:
        Dictionary with collected metrics/data
        
    Raises:
        Exception: On collection failure
    """
    # Your collection logic here
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            # Your metrics
        }
    }
    return data
```

### Step 3: Add Optional Methods

#### Health Check

```python
async def health_check(self) -> Dict[str, Any]:
    """Check if plugin can operate correctly"""
    try:
        # Test dependencies, connections, etc.
        test_connection()
        return {
            "healthy": True,
            "message": "All systems operational"
        }
    except Exception as e:
        return {
            "healthy": False,
            "message": f"Health check failed: {str(e)}"
        }
```

#### Configuration Validation

```python
async def validate_config(self, config: Dict[str, Any]) -> bool:
    """Validate plugin configuration"""
    required = ["host", "port"]
    return all(key in config for key in required)
```

#### Lifecycle Hooks

```python
async def on_enable(self):
    """Called when plugin is enabled"""
    await super().on_enable()
    # Initialize connections, resources, etc.
    self.connection = await self._connect()

async def on_disable(self):
    """Called when plugin is disabled"""
    # Cleanup resources
    if self.connection:
        await self.connection.close()
    await super().on_disable()
```

## Configuration Schema

Define configuration using JSON Schema:

```python
config_schema = {
    "type": "object",
    "properties": {
        "host": {
            "type": "string",
            "default": "localhost",
            "description": "Database host"
        },
        "port": {
            "type": "integer",
            "default": 5432,
            "minimum": 1,
            "maximum": 65535,
            "description": "Database port"
        },
        "username": {
            "type": "string",
            "description": "Database username"
        },
        "password": {
            "type": "string",
            "description": "Database password (use env vars!)"
        },
        "timeout": {
            "type": "integer",
            "default": 10,
            "description": "Connection timeout in seconds"
        },
        "ssl_enabled": {
            "type": "boolean",
            "default": False,
            "description": "Enable SSL connection"
        }
    },
    "required": ["host", "username", "password"]
}
```

### Accessing Configuration

```python
async def collect_data(self) -> Dict[str, Any]:
    host = self.config.get("host", "localhost")
    port = self.config.get("port", 5432)
    timeout = self.config.get("timeout", 10)
    
    # Use configuration values
    connection = await connect(host, port, timeout=timeout)
    # ...
```

## Error Handling

### Best Practices

1. **Catch Specific Exceptions**: Don't use bare `except`

```python
async def collect_data(self) -> Dict[str, Any]:
    try:
        data = await self._fetch_data()
        return data
    except ConnectionError as e:
        self._last_error = f"Connection failed: {str(e)}"
        raise
    except TimeoutError as e:
        self._last_error = f"Operation timed out: {str(e)}"
        raise
    except Exception as e:
        self._last_error = f"Unexpected error: {str(e)}"
        raise
```

2. **Provide Context**: Include useful error details

```python
except psycopg2.OperationalError as e:
    raise Exception(
        f"PostgreSQL connection failed to {self.config['host']}:"
        f"{self.config['port']}: {str(e)}"
    )
```

3. **Graceful Degradation**: Return partial data when possible

```python
async def collect_data(self) -> Dict[str, Any]:
    data = {"timestamp": datetime.utcnow().isoformat()}
    
    try:
        data["primary_metrics"] = await self._collect_primary()
    except Exception as e:
        data["primary_metrics_error"] = str(e)
    
    try:
        data["secondary_metrics"] = await self._collect_secondary()
    except Exception as e:
        data["secondary_metrics_error"] = str(e)
    
    return data
```

## Testing

### Unit Tests

```python
import pytest
from app.plugins.builtin.my_plugin import MyPlugin

@pytest.mark.asyncio
async def test_plugin_metadata():
    plugin = MyPlugin()
    metadata = plugin.get_metadata()
    
    assert metadata.id == "my-plugin"
    assert metadata.version == "1.0.0"
    assert metadata.category == PluginCategory.CUSTOM

@pytest.mark.asyncio
async def test_collect_data():
    plugin = MyPlugin(config={"host": "localhost"})
    data = await plugin.collect_data()
    
    assert "timestamp" in data
    assert "metrics" in data

@pytest.mark.asyncio
async def test_health_check():
    plugin = MyPlugin()
    health = await plugin.health_check()
    
    assert health["healthy"] is True
    assert "message" in health
```

### Integration Tests

Test with real services using Docker:

```python
import pytest
import docker

@pytest.fixture
async def postgres_container():
    client = docker.from_env()
    container = client.containers.run(
        "postgres:15",
        environment={"POSTGRES_PASSWORD": "test"},
        ports={"5432/tcp": 5433},
        detach=True
    )
    # Wait for container to be ready
    await asyncio.sleep(5)
    
    yield container
    
    container.stop()
    container.remove()

@pytest.mark.asyncio
async def test_postgres_plugin_real_connection(postgres_container):
    plugin = PostgreSQLMonitorPlugin(config={
        "host": "localhost",
        "port": 5433,
        "user": "postgres",
        "password": "test",
        "database": "postgres"
    })
    
    data = await plugin.collect_data()
    assert "server_version" in data
    assert "connections" in data
```

### Manual Testing

```bash
# Start Unity
uvicorn app.main:app --reload

# Check plugin discovered
curl http://localhost:8000/api/v1/plugins | jq '.[] | select(.id=="my-plugin")'

# Test health check
curl http://localhost:8000/api/v1/plugins/my-plugin/health

# Enable plugin
curl -X POST http://localhost:8000/api/v1/plugins/my-plugin/enable

# Execute and get data
curl -X POST http://localhost:8000/api/v1/plugins/my-plugin/execute

# Get metrics history
curl http://localhost:8000/api/v1/plugins/my-plugin/metrics
```

## Best Practices

### 1. Security

**Never hardcode credentials:**

```python
# ❌ BAD
config = {
    "password": "super_secret_password"
}

# ✅ GOOD - Use environment variables
import os
config = {
    "password": os.getenv("DB_PASSWORD")
}
```

**Validate and sanitize inputs:**

```python
async def validate_config(self, config: Dict[str, Any]) -> bool:
    # Check required fields
    if "host" not in config:
        return False
    
    # Sanitize inputs
    host = str(config["host"]).strip()
    if not host or ".." in host:
        return False
    
    return True
```

### 2. Performance

**Use connection pooling:**

```python
class DatabasePlugin(PluginBase):
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        self.pool = None
    
    async def on_enable(self):
        await super().on_enable()
        self.pool = await create_pool(
            host=self.config["host"],
            min_size=2,
            max_size=10
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            # Use connection
            pass
```

**Cache expensive operations:**

```python
from functools import lru_cache

class MyPlugin(PluginBase):
    @lru_cache(maxsize=1)
    def _get_system_info(self):
        # Expensive operation cached
        return platform.uname()
```

### 3. Reliability

**Implement timeouts:**

```python
import asyncio

async def collect_data(self) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(
            self._fetch_data(),
            timeout=self.config.get("timeout", 30)
        )
    except asyncio.TimeoutError:
        raise Exception("Data collection timed out")
```

**Handle resource cleanup:**

```python
def __del__(self):
    """Ensure resources are cleaned up"""
    if hasattr(self, 'connection') and self.connection:
        try:
            self.connection.close()
        except:
            pass
```

### 4. Observability

**Log important events:**

```python
import logging

logger = logging.getLogger(__name__)

async def collect_data(self) -> Dict[str, Any]:
    logger.info(f"Collecting data from {self.config['host']}")
    
    try:
        data = await self._fetch_data()
        logger.debug(f"Collected {len(data)} metrics")
        return data
    except Exception as e:
        logger.error(f"Collection failed: {str(e)}", exc_info=True)
        raise
```

**Include diagnostic information:**

```python
async def health_check(self) -> Dict[str, Any]:
    return {
        "healthy": True,
        "message": "Operational",
        "details": {
            "last_execution": self._last_execution.isoformat() if self._last_execution else None,
            "execution_count": self._execution_count,
            "last_error": self._last_error
        }
    }
```

## Advanced Topics

### External Plugin Support

Plugins can also be loaded from external directories:

```python
# ~/.unity/plugins/my_external_plugin.py
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory

class ExternalPlugin(PluginBase):
    # Same implementation as builtin plugins
    pass
```

Configure external plugin paths in `unity.yaml`:

```yaml
plugins:
  external_paths:
    - /home/user/.unity/plugins
    - /opt/unity/plugins
```

### Hub Communication

External plugins can communicate with Unity Hub:

```python
async def collect_data(self) -> Dict[str, Any]:
    # Send data to hub (if connected)
    if self.hub:
        await self.hub.send_metrics({
            "plugin_id": self.get_metadata().id,
            "data": collected_data
        })
    
    return collected_data
```

### Async Best Practices

**Use async/await properly:**

```python
# ✅ GOOD - Concurrent operations
async def collect_data(self) -> Dict[str, Any]:
    # Run multiple queries concurrently
    results = await asyncio.gather(
        self._query_stats(),
        self._query_connections(),
        self._query_databases()
    )
    return self._format_results(results)

# ❌ BAD - Sequential operations
async def collect_data(self) -> Dict[str, Any]:
    stats = await self._query_stats()
    connections = await self._query_connections()
    databases = await self._query_databases()
    return self._format_results([stats, connections, databases])
```

### Plugin Dependencies

If your plugin depends on another plugin:

```python
class DerivedPlugin(PluginBase):
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        self.base_plugin = None
    
    async def on_enable(self):
        await super().on_enable()
        # Load base plugin
        from app.plugins.loader import get_plugin
        self.base_plugin = get_plugin("base-plugin-id")
    
    async def collect_data(self) -> Dict[str, Any]:
        # Use base plugin data
        base_data = await self.base_plugin.collect_data()
        # Derive metrics from base data
        derived_data = self._process(base_data)
        return derived_data
```

## Next Steps

- Review [Built-in Plugins Catalog](BUILTIN_PLUGINS.md) for examples
- Use the Plugin Generator: `python -m app.plugins.tools.plugin_generator my-plugin`
- Check out the [example plugins](../backend/app/plugins/builtin/) in the repository
- Join the community Discord for plugin development discussions

## Need Help?

- 📖 [API Documentation](API.md)
- 🏗️ [Architecture Overview](../ARCHITECTURE.md)
- 💬 Community Discord
- 🐛 [GitHub Issues](https://github.com/yourusername/unity/issues)

