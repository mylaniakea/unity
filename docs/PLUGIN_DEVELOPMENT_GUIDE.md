# Unity Plugin Development Guide

Complete guide to creating custom monitoring plugins for Unity homelab platform.

**Last Updated**: December 22, 2025  
**Target Audience**: Python developers, DevOps engineers, homelab enthusiasts

## Table of Contents

1. [Quick Start](#quick-start)
2. [Plugin Architecture](#plugin-architecture)
3. [Step-by-Step Tutorial](#step-by-step-tutorial)
4. [Best Practices](#best-practices)
5. [Common Patterns](#common-patterns)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

Create your first plugin in 5 minutes!

### 1. Create Plugin File

```bash
cd app/plugins/builtin
touch my_service_monitor.py
```

### 2. Basic Plugin Structure

```python
"""My Service Monitor Plugin"""
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory

class MyServiceMonitorPlugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my-service-monitor",
            name="My Service Monitor",
            version="1.0.0",
            description="Monitors my custom service",
            author="Your Name",
            category=PluginCategory.APPLICATION,
            tags=["service", "monitoring"],
            requires_sudo=False,
            supported_os=["linux"],
            dependencies=[],
            config_schema={}
        )
    
    async def collect_data(self):
        return {
            "status": "running",
            "uptime": 3600
        }
```

### 3. Test Your Plugin

```python
# Quick test
import asyncio
plugin = MyServiceMonitorPlugin(config={})
data = asyncio.run(plugin.collect_data())
print(data)  # {'status': 'running', 'uptime': 3600}
```

### 4. Enable in Unity

```bash
curl -X POST http://localhost:8000/api/plugins/v2/enable/my-service-monitor
```

Done! Your plugin is now collecting data every collection interval.

---

## Plugin Architecture

### Core Components

```
PluginBase (abstract)
  ├── get_metadata() -> PluginMetadata
  └── collect_data() -> Dict[str, Any]

PluginMetadata
  ├── id: str (unique identifier)
  ├── name: str (display name)
  ├── version: str (semver)
  ├── category: PluginCategory (enum)
  ├── dependencies: List[str] (pip packages)
  └── config_schema: Dict (JSON schema)
```

### Plugin Lifecycle

```
1. Discovery → Plugin file found in builtin/
2. Registration → Metadata extracted, registered in system
3. Configuration → User provides config via API
4. Execution → collect_data() called on schedule
5. Storage → Metrics saved to database
```

### Data Flow

```
Plugin.collect_data()
  ↓
{ metric_name: value, ... }
  ↓
PluginManager.process_result()
  ↓
Database (metrics storage)
  ↓
API /metrics/{plugin_id}
```

---

## Step-by-Step Tutorial

### Tutorial 1: HTTP Service Monitor

Monitor a web service via HTTP endpoint.

**Goal**: Check if service is up and measure response time.

```python
"""HTTP Service Monitor Plugin"""
import httpx
import time
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory

class HTTPServiceMonitorPlugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="http-service-monitor",
            name="HTTP Service Monitor",
            version="1.0.0",
            description="Monitors HTTP/HTTPS endpoints",
            author="Unity Team",
            category=PluginCategory.APPLICATION,
            tags=["http", "web", "api"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["httpx"],
            config_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to monitor"
                    },
                    "timeout": {
                        "type": "number",
                        "default": 5.0
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        )
    
    async def collect_data(self):
        config = self.config or {}
        url = config.get("url")
        
        if not url:
            return {"error": "URL not configured"}
        
        timeout = config.get("timeout", 5.0)
        verify_ssl = config.get("verify_ssl", True)
        
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(verify=verify_ssl) as client:
                response = await client.get(url, timeout=timeout)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "up",
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "is_success": 200 <= response.status_code < 300,
                "url": url
            }
        except Exception as e:
            return {
                "status": "down",
                "error": str(e),
                "url": url
            }
```

**Configuration Example**:
```json
{
  "url": "https://api.example.com/health",
  "timeout": 10.0,
  "verify_ssl": true
}
```

### Tutorial 2: Database Connection Monitor

Monitor database availability and connection metrics.

```python
"""Database Connection Monitor"""
import psycopg2
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory

class DatabaseConnectionMonitorPlugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="db-connection-monitor",
            name="Database Connection Monitor",
            version="1.0.0",
            description="Monitors database connectivity",
            author="Unity Team",
            category=PluginCategory.DATABASE,
            tags=["database", "postgresql", "mysql"],
            requires_sudo=False,
            supported_os=["linux", "darwin"],
            dependencies=["psycopg2"],
            config_schema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer", "default": 5432},
                    "database": {"type": "string"},
                    "user": {"type": "string"},
                    "password": {"type": "string"}
                },
                "required": ["host", "database", "user", "password"]
            }
        )
    
    async def collect_data(self):
        config = self.config or {}
        
        try:
            conn = psycopg2.connect(
                host=config.get("host"),
                port=config.get("port", 5432),
                database=config.get("database"),
                user=config.get("user"),
                password=config.get("password"),
                connect_timeout=5
            )
            
            with conn.cursor() as cursor:
                # Get database size
                cursor.execute(
                    "SELECT pg_database_size(%s)", 
                    (config.get("database"),)
                )
                db_size = cursor.fetchone()[0]
                
                # Get connection count
                cursor.execute(
                    "SELECT count(*) FROM pg_stat_activity"
                )
                connections = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "status": "connected",
                "database_size_bytes": db_size,
                "active_connections": connections,
                "responsive": True
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "responsive": False
            }
```

---

## Best Practices

### 1. Error Handling

**Always handle exceptions gracefully:**

```python
async def collect_data(self):
    try:
        # Your collection logic
        return {"metric": value}
    except SpecificException as e:
        logger.warning(f"Plugin failed: {e}")
        return {"error": str(e), "status": "failed"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {"error": "Internal error"}
```

### 2. Configuration Validation

**Validate config in collect_data():**

```python
async def collect_data(self):
    config = self.config or {}
    
    # Validate required fields
    required = ["host", "port"]
    missing = [f for f in required if f not in config]
    
    if missing:
        return {"error": f"Missing required config: {', '.join(missing)}"}
    
    # Proceed with collection
    ...
```

### 3. Timeouts

**Always use timeouts for external calls:**

```python
# HTTP requests
async with httpx.AsyncClient(timeout=5.0) as client:
    response = await client.get(url)

# Database connections
conn = psycopg2.connect(..., connect_timeout=5)

# Subprocess
result = subprocess.run(cmd, timeout=10)
```

### 4. Secure Credentials

**Never log or expose credentials:**

```python
# ❌ Bad
logger.info(f"Connecting with password: {config['password']}")

# ✅ Good
logger.info(f"Connecting to {config['host']}")
```

### 5. Meaningful Metrics

**Return clear, actionable metrics:**

```python
# ❌ Bad
return {"data": [1, 2, 3]}

# ✅ Good
return {
    "cpu_usage_percent": 45.2,
    "memory_used_gb": 8.5,
    "disk_free_gb": 120.0,
    "status": "healthy"
}
```

### 6. Metric Naming

**Use consistent naming conventions:**

```python
# Format: {resource}.{metric}_{unit}
"cpu.usage_percent"
"memory.used_gb"
"disk.io_read_bytes_per_sec"
"network.packets_recv_count"
```

---

## Common Patterns

### Pattern 1: Command Execution

```python
import subprocess

async def collect_data(self):
    try:
        result = subprocess.run(
            ["command", "arg1", "arg2"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            return {"output": output, "success": True}
        else:
            return {"error": result.stderr, "success": False}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
```

### Pattern 2: File Parsing

```python
async def collect_data(self):
    log_file = self.config.get("log_file", "/var/log/app.log")
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Parse last 100 lines
        recent = lines[-100:]
        errors = [l for l in recent if "ERROR" in l]
        
        return {
            "total_lines": len(lines),
            "recent_errors": len(errors),
            "last_error": errors[-1] if errors else None
        }
    except FileNotFoundError:
        return {"error": "Log file not found"}
```

### Pattern 3: API Polling

```python
async def collect_data(self):
    api_url = self.config.get("api_url")
    api_token = self.config.get("api_token")
    
    headers = {"Authorization": f"Bearer {api_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_url}/api/stats",
            headers=headers,
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "online",
                **data  # Spread API response
            }
        else:
            return {"status": "error", "code": response.status_code}
```

---

## Testing

### Unit Tests

```python
# tests/plugins/builtin/test_my_plugin.py
import pytest
from unittest.mock import Mock, patch
from app.plugins.builtin.my_plugin import MyPluginClass

class TestMyPlugin:
    @pytest.fixture
    def plugin(self):
        return MyPluginClass(config={"host": "localhost"})
    
    def test_metadata(self, plugin):
        metadata = plugin.get_metadata()
        assert metadata.id == "my-plugin"
        assert metadata.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_collect_success(self, plugin):
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            data = await plugin.collect_data()
            
            assert data["status"] == "up"
            assert data["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_collect_error(self, plugin):
        plugin.config = {}  # Missing required config
        
        data = await plugin.collect_data()
        
        assert "error" in data
```

### Integration Tests

```python
# tests/integration/test_my_plugin_integration.py
import pytest
from app.plugins.builtin.my_plugin import MyPluginClass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_service():
    """Test against actual running service."""
    plugin = MyPluginClass(config={
        "url": "http://localhost:8080/health"
    })
    
    data = await plugin.collect_data()
    
    assert data["status"] in ["up", "down"]
    assert "response_time_ms" in data or "error" in data
```

---

## Deployment

### 1. Add to Builtin Plugins

```bash
# Place your plugin file
cp my_plugin.py app/plugins/builtin/

# Restart Unity
systemctl restart unity
```

### 2. Register in Registry

The plugin will be automatically discovered by the registry API.

### 3. Enable via API

```bash
curl -X POST http://localhost:8000/api/plugins/v2/enable/my-plugin \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "host": "localhost",
      "port": 8080
    }
  }'
```

### 4. Configure Collection

```bash
# Set collection interval (seconds)
curl -X PUT http://localhost:8000/api/plugins/v2/my-plugin/schedule \
  -H "Content-Type: application/json" \
  -d '{"interval": 60}'
```

---

## Troubleshooting

### Plugin Not Discovered

**Check**:
1. File is in `app/plugins/builtin/`
2. Class name ends with `Plugin`
3. Inherits from `PluginBase`
4. Has `get_metadata()` and `collect_data()` methods

### Import Errors

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
# Or for specific dependency
pip install httpx
```

### No Data Collected

**Debug**:
```bash
# Check logs
tail -f logs/unity.log | grep my-plugin

# Test manually
curl -X POST http://localhost:8000/api/plugins/v2/my-plugin/execute
```

### Configuration Issues

**Validate schema**:
```python
# Ensure config_schema matches your requirements
config_schema={
    "type": "object",
    "properties": {
        "required_field": {"type": "string"}
    },
    "required": ["required_field"]
}
```

---

## Advanced Topics

### Async/Await

All `collect_data()` methods are async:

```python
async def collect_data(self):
    # Use await for async operations
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    
    # Regular sync code works too
    data = process_response(response)
    
    return data
```

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_lookup(key):
    # Cache results for 5 minutes
    return fetch_from_api(key)
```

### Background Tasks

For long-running operations:

```python
import asyncio

async def collect_data(self):
    # Quick check
    status = check_status()
    
    # Schedule background task
    asyncio.create_task(expensive_scan())
    
    return {"status": status}
```

---

## Resources

- [Plugin API Reference](PLUGIN_API_EXAMPLES.md)
- [Built-in Plugins Catalog](BUILTIN_PLUGINS.md)
- [Unity Architecture](ARCHITECTURE.md)
- [Testing Guide](TESTING-GUIDE.md)

## Community

- Submit plugins: [GitHub Discussions](https://github.com/unity/discussions)
- Report issues: [GitHub Issues](https://github.com/unity/issues)
- Plugin showcase: [Unity Wiki](https://github.com/unity/wiki)

---

**Happy plugin development!** 🚀
