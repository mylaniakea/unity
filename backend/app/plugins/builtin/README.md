# Built-in Plugins

This directory contains all built-in monitoring plugins for Unity. These plugins are production-ready and cover common monitoring use cases.

## Available Plugins

### System Monitoring
- **system-info** - Comprehensive system information (CPU, memory, disk, network)
- **process-monitor** - Process tracking and resource consumption analysis
- **thermal-monitor** - Temperature monitoring for CPU/GPU and fan speeds

### Network Monitoring
- **network-monitor** - Network interface statistics, throughput, and connections

### Storage Monitoring
- **disk-monitor** - Disk usage, I/O statistics, and partition monitoring

### Container Orchestration
- **docker-monitor** - Docker container stats, health, and network monitoring

### Database Monitoring
- **postgres-monitor** - PostgreSQL metrics (connections, queries, cache hits)
- **mysql-monitor** - MySQL/MariaDB metrics (threads, queries, buffer pool)
- **mongodb-monitor** - MongoDB metrics (operations, connections, replica status)
- **redis-monitor** - Redis metrics (memory, commands, keyspace stats)
- **influxdb-monitor** - InfluxDB metrics (writes, queries, measurements)
- **sqlite-monitor** - SQLite database stats (size, queries, cache, integrity)

### Application Monitoring
- **web-service-monitor** - HTTP endpoint monitoring (response time, status, availability)
- **log-monitor** - Log file analysis (error counts, patterns, rates)

## Quick Start

### Enable a Plugin

```bash
# List available plugins
curl http://localhost:8000/api/v1/plugins

# Enable a plugin
curl -X POST http://localhost:8000/api/v1/plugins/system-info/enable

# Execute plugin and get data
curl -X POST http://localhost:8000/api/v1/plugins/system-info/execute
```

### Configure a Plugin

```bash
# Configure with custom settings
curl -X POST http://localhost:8000/api/v1/plugins/postgres-monitor/configure \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "${POSTGRES_PASSWORD}",
    "database": "mydb"
  }'
```

### Health Check

```bash
# Check plugin health
curl http://localhost:8000/api/v1/plugins/system-info/health
```

## Plugin Structure

All plugins inherit from `PluginBase` and implement:

```python
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory
from typing import Dict, Any

class MyPlugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            id="my-plugin",
            name="My Plugin",
            version="1.0.0",
            description="What it does",
            author="Your Name",
            category=PluginCategory.CUSTOM,
            tags=["monitoring"],
            dependencies=["psutil"]
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect and return metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                # Your metrics here
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if plugin is healthy"""
        return {
            "healthy": True,
            "message": "All systems operational"
        }
```

## Creating a New Built-in Plugin

### Option 1: Use the Plugin Generator (Recommended)

```bash
# Generate a new plugin from template
python -m app.plugins.tools.plugin_generator \
  --id my-plugin \
  --name "My Plugin" \
  --category system \
  --author "Your Name"
```

### Option 2: Manual Creation

1. **Create plugin file**: `backend/app/plugins/builtin/my_plugin.py`

2. **Implement required methods**:
   - `get_metadata()` - Plugin information
   - `collect_data()` - Data collection logic

3. **Add optional methods**:
   - `health_check()` - Health validation
   - `validate_config()` - Config validation
   - `on_enable()` / `on_disable()` - Lifecycle hooks

4. **Register plugin**: No explicit registration needed - plugins are auto-discovered

5. **Test plugin**:
```bash
# Validate plugin
python -m app.plugins.tools.plugin_validator my_plugin.py

# Test with mock data
python -m app.plugins.tools.plugin_tester my-plugin

# Start Unity and check logs
uvicorn app.main:app --reload
```

## Plugin Best Practices

### 1. Configuration

- **Use JSON Schema** for config validation
- **Never hardcode secrets** - use environment variables
- **Provide sensible defaults** for optional settings

### 2. Error Handling

- **Catch specific exceptions** - avoid bare `except`
- **Provide context** in error messages
- **Implement graceful degradation** when possible

### 3. Performance

- **Use connection pooling** for database/network plugins
- **Cache expensive operations** appropriately
- **Implement timeouts** for all I/O operations
- **Use async/await** for concurrent operations

### 4. Testing

- **Write unit tests** for core logic
- **Test error conditions** and edge cases
- **Use Docker** for integration tests with real services
- **Validate against the schema** before deployment

### 5. Documentation

- **Clear docstrings** for all methods
- **Document configuration options** with examples
- **Include use cases** and common scenarios
- **Provide troubleshooting tips** for common issues

## Plugin Categories

- `SYSTEM` - System resources (CPU, memory, processes)
- `NETWORK` - Network interfaces and connections
- `STORAGE` - Disk and filesystem monitoring
- `THERMAL` - Temperature and cooling
- `CONTAINER` - Docker, Kubernetes, etc.
- `DATABASE` - Database monitoring
- `APPLICATION` - Application/service monitoring
- `SECURITY` - Security and access monitoring
- `AI_ML` - AI/ML model and GPU monitoring
- `CUSTOM` - Custom/specialized monitoring

## Common Patterns

### Database Plugin Pattern

```python
class DatabasePlugin(PluginBase):
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        self.connection = None
    
    async def on_enable(self):
        await super().on_enable()
        self.connection = await self._connect()
    
    async def _connect(self):
        # Establish connection with retry logic
        pass
    
    async def collect_data(self) -> Dict[str, Any]:
        if not self.connection:
            await self._connect()
        # Collect metrics
        pass
    
    async def on_disable(self):
        if self.connection:
            await self.connection.close()
        await super().on_disable()
```

### HTTP Service Pattern

```python
class WebServicePlugin(PluginBase):
    async def collect_data(self) -> Dict[str, Any]:
        import aiohttp
        
        url = self.config["url"]
        timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 10))
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            start = time.time()
            async with session.get(url) as response:
                duration = time.time() - start
                
                return {
                    "url": url,
                    "status_code": response.status,
                    "response_time_ms": round(duration * 1000, 2),
                    "available": response.status < 500
                }
```

### File Monitoring Pattern

```python
class LogMonitorPlugin(PluginBase):
    def __init__(self, hub_client=None, config=None):
        super().__init__(hub_client, config)
        self.last_position = 0
    
    async def collect_data(self) -> Dict[str, Any]:
        log_file = self.config["log_file"]
        
        with open(log_file, 'r') as f:
            f.seek(self.last_position)
            new_lines = f.readlines()
            self.last_position = f.tell()
        
        # Analyze new lines
        errors = [line for line in new_lines if 'ERROR' in line]
        
        return {
            "lines_processed": len(new_lines),
            "errors_found": len(errors),
            "error_rate": len(errors) / len(new_lines) if new_lines else 0
        }
```

## Development Tools

Unity provides several tools to streamline plugin development:

- **Plugin Generator** - `python -m app.plugins.tools.plugin_generator`
  - Generate plugin boilerplate from templates
  - Support for all plugin categories
  - Includes tests and documentation

- **Plugin Validator** - `python -m app.plugins.tools.plugin_validator`
  - Validate plugin structure and code
  - Check metadata completeness
  - Verify config schema
  - Lint code quality

- **Plugin Tester** - `python -m app.plugins.tools.plugin_tester`
  - Test plugins with mock data
  - Simulate various scenarios
  - Measure performance
  - Validate output format

## Documentation

For comprehensive documentation, see:

- **[Built-in Plugins Catalog](../../docs/BUILTIN_PLUGINS.md)** - Complete catalog of all builtin plugins
- **[Plugin Development Guide](../../docs/PLUGIN_DEVELOPMENT.md)** - Full development guide with examples
- **[Architecture Overview](../../ARCHITECTURE.md)** - System architecture details

## Need Help?

- Check the [Plugin Development Guide](../../docs/PLUGIN_DEVELOPMENT.md)
- Review [example plugins](.) in this directory
- Open an issue on GitHub
- Join the community Discord

