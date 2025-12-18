# Plugin API Usage Examples

This guide demonstrates how to interact with Unity plugins via the REST API.

**Base URL**: `http://localhost:8000`  
**API Version**: v2 (Secure)  
**Endpoint Prefix**: `/api/v2/plugins`

## Authentication

All plugin API endpoints require authentication. Include your JWT token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

## Available Endpoints

### 1. List All Plugins

Get a list of all registered plugins with their status.

**Endpoint**: `GET /api/v2/plugins`

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v2/plugins" \
  -H "Authorization: Bearer <token>"
```

**Example Response**:
```json
{
  "plugins": [
    {
      "id": "system-info",
      "name": "System Info",
      "version": "1.0.0",
      "enabled": true,
      "category": "SYSTEM",
      "description": "Provides comprehensive system information",
      "author": "Unity Team"
    },
    {
      "id": "postgres-monitor",
      "name": "PostgreSQL Monitor",
      "version": "1.0.0",
      "enabled": false,
      "category": "DATABASE",
      "description": "Monitors PostgreSQL server metrics",
      "author": "Unity Team"
    }
  ],
  "total": 16
}
```

---

### 2. Get Plugin Details

Retrieve detailed information about a specific plugin.

**Endpoint**: `GET /api/v2/plugins/{plugin_id}`

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v2/plugins/system-info" \
  -H "Authorization: Bearer <token>"
```

**Example Response**:
```json
{
  "id": "system-info",
  "name": "System Info",
  "version": "1.0.0",
  "enabled": true,
  "category": "SYSTEM",
  "description": "Provides comprehensive system information including CPU, memory, OS details, and hardware specifications",
  "author": "Unity Team",
  "tags": ["system", "hardware", "info"],
  "dependencies": ["psutil"],
  "supported_os": ["linux", "darwin", "windows"],
  "requires_sudo": false,
  "config_schema": {
    "type": "object",
    "properties": {
      "collection_interval": {
        "type": "integer",
        "default": 60
      }
    }
  }
}
```

---

### 3. Enable a Plugin

Enable a plugin to start collecting data.

**Endpoint**: `POST /api/v2/plugins/{plugin_id}/enable`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v2/plugins/postgres-monitor/enable" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Example Response**:
```json
{
  "success": true,
  "message": "Plugin postgres-monitor enabled successfully",
  "plugin_id": "postgres-monitor"
}
```

---

### 4. Disable a Plugin

Disable a plugin to stop data collection.

**Endpoint**: `POST /api/v2/plugins/{plugin_id}/disable`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v2/plugins/postgres-monitor/disable" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Example Response**:
```json
{
  "success": true,
  "message": "Plugin postgres-monitor disabled successfully",
  "plugin_id": "postgres-monitor"
}
```

---

### 5. Update Plugin Configuration

Update the configuration for a plugin.

**Endpoint**: `PUT /api/v2/plugins/{plugin_id}/config`

**Example Request**:
```bash
curl -X PUT "http://localhost:8000/api/v2/plugins/postgres-monitor/config" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "monitor_user",
    "password": "secure_password",
    "collection_interval": 30
  }'
```

**Example Response**:
```json
{
  "success": true,
  "message": "Configuration updated for plugin postgres-monitor",
  "plugin_id": "postgres-monitor"
}
```

---

### 6. Execute Plugin Data Collection

Manually trigger data collection for a plugin.

**Endpoint**: `POST /api/v2/plugins/{plugin_id}/execute`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v2/plugins/system-info/execute" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Example Response**:
```json
{
  "success": true,
  "plugin_id": "system-info",
  "execution_time": 0.234,
  "data": {
    "cpu": {
      "usage_percent": 45.2,
      "count": 8,
      "frequency": 2400.0
    },
    "memory": {
      "total_gb": 16.0,
      "used_gb": 8.5,
      "percent": 53.1
    },
    "os": {
      "system": "Linux",
      "release": "5.15.0",
      "version": "Ubuntu 22.04"
    }
  },
  "timestamp": "2025-12-17T23:15:00Z"
}
```

---

### 7. Register a Custom Plugin

Register a new external plugin with Unity.

**Endpoint**: `POST /api/v2/plugins/register`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v2/plugins/register" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "custom-monitor",
    "name": "Custom Monitor",
    "version": "1.0.0",
    "description": "Custom monitoring plugin",
    "category": "APPLICATION",
    "author": "Your Name",
    "external": true,
    "callback_url": "https://your-plugin-service.com/callback"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "message": "Plugin custom-monitor registered successfully",
  "plugin_id": "custom-monitor",
  "api_key": "pk_live_abc123def456..."
}
```

---

### 8. Report Plugin Metrics

External plugins can report metrics to Unity.

**Endpoint**: `POST /api/v2/plugins/{plugin_id}/metrics/report`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v2/plugins/custom-monitor/metrics/report" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {
      "requests_per_second": 125.5,
      "error_rate": 0.02,
      "avg_response_time_ms": 45.3
    },
    "timestamp": "2025-12-17T23:20:00Z"
  }'
```

**Example Response**:
```json
{
  "success": true,
  "message": "Metrics received for plugin custom-monitor",
  "plugin_id": "custom-monitor"
}
```

---

### 9. Report Plugin Health

External plugins can report their health status.

**Endpoint**: `POST /api/v2/plugins/{plugin_id}/health/report`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v2/plugins/custom-monitor/health/report" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "healthy": true,
    "status": "operational",
    "details": {
      "uptime_seconds": 86400,
      "last_error": null
    }
  }'
```

**Example Response**:
```json
{
  "success": true,
  "message": "Health status updated for plugin custom-monitor",
  "plugin_id": "custom-monitor"
}
```

---

### 10. Fetch Plugin Configuration

External plugins can fetch their configuration from Unity.

**Endpoint**: `GET /api/v2/plugins/{plugin_id}/config/fetch`

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v2/plugins/custom-monitor/config/fetch" \
  -H "Authorization: Bearer <token>"
```

**Example Response**:
```json
{
  "plugin_id": "custom-monitor",
  "config": {
    "collection_interval": 60,
    "alert_threshold": 80,
    "custom_setting": "value"
  }
}
```

---

## Python SDK Example

Here's a complete Python example using the `requests` library:

```python
import requests
from typing import Dict, Any

class UnityPluginClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def list_plugins(self) -> Dict[str, Any]:
        """List all plugins."""
        response = requests.get(
            f"{self.base_url}/api/v2/plugins",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin details."""
        response = requests.get(
            f"{self.base_url}/api/v2/plugins/{plugin_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def enable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Enable a plugin."""
        response = requests.post(
            f"{self.base_url}/api/v2/plugins/{plugin_id}/enable",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def execute_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """Execute plugin data collection."""
        response = requests.post(
            f"{self.base_url}/api/v2/plugins/{plugin_id}/execute",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def update_config(self, plugin_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update plugin configuration."""
        response = requests.put(
            f"{self.base_url}/api/v2/plugins/{plugin_id}/config",
            headers=self.headers,
            json=config
        )
        response.raise_for_status()
        return response.json()

# Usage example
if __name__ == "__main__":
    client = UnityPluginClient(
        base_url="http://localhost:8000",
        token="your_jwt_token_here"
    )
    
    # List all plugins
    plugins = client.list_plugins()
    print(f"Found {plugins['total']} plugins")
    
    # Enable PostgreSQL monitor
    result = client.enable_plugin("postgres-monitor")
    print(result["message"])
    
    # Update configuration
    config = {
        "host": "localhost",
        "port": 5432,
        "database": "mydb"
    }
    client.update_config("postgres-monitor", config)
    
    # Collect data
    data = client.execute_plugin("postgres-monitor")
    print(f"Collected data in {data['execution_time']:.3f}s")
```

---

## Common Use Cases

### 1. Setting up a Database Monitor

```bash
# 1. Enable the plugin
curl -X POST "http://localhost:8000/api/v2/plugins/postgres-monitor/enable" \
  -H "Authorization: Bearer <token>"

# 2. Configure connection
curl -X PUT "http://localhost:8000/api/v2/plugins/postgres-monitor/config" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 5432,
    "database": "production",
    "username": "monitor",
    "password": "secure_pass"
  }'

# 3. Test data collection
curl -X POST "http://localhost:8000/api/v2/plugins/postgres-monitor/execute" \
  -H "Authorization: Bearer <token>"
```

### 2. Monitoring System Resources

```bash
# Enable system monitoring plugins
curl -X POST "http://localhost:8000/api/v2/plugins/system-info/enable" \
  -H "Authorization: Bearer <token>"

curl -X POST "http://localhost:8000/api/v2/plugins/process-monitor/enable" \
  -H "Authorization: Bearer <token>"

curl -X POST "http://localhost:8000/api/v2/plugins/thermal-monitor/enable" \
  -H "Authorization: Bearer <token>"

# Collect all system data
for plugin in system-info process-monitor thermal-monitor; do
  curl -X POST "http://localhost:8000/api/v2/plugins/$plugin/execute" \
    -H "Authorization: Bearer <token>"
done
```

### 3. Creating a Custom Monitoring Dashboard

```python
import requests
from datetime import datetime

def get_all_metrics(base_url: str, token: str):
    """Collect metrics from all enabled plugins."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get enabled plugins
    plugins_resp = requests.get(f"{base_url}/api/v2/plugins", headers=headers)
    plugins = [p for p in plugins_resp.json()["plugins"] if p["enabled"]]
    
    # Collect data from each
    metrics = {}
    for plugin in plugins:
        try:
            resp = requests.post(
                f"{base_url}/api/v2/plugins/{plugin['id']}/execute",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                metrics[plugin["id"]] = resp.json()["data"]
        except Exception as e:
            print(f"Error collecting from {plugin['id']}: {e}")
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics
    }
```

---

## Error Handling

### Common Error Responses

**Plugin Not Found (404)**:
```json
{
  "detail": "Plugin system-info-typo not found"
}
```

**Plugin Already Enabled (400)**:
```json
{
  "detail": "Plugin postgres-monitor is already enabled"
}
```

**Invalid Configuration (422)**:
```json
{
  "detail": "Invalid configuration: missing required field 'host'"
}
```

**Unauthorized (401)**:
```json
{
  "detail": "Not authenticated"
}
```

---

## Best Practices

1. **Always check plugin status** before enabling/disabling
2. **Validate configuration** against the plugin's `config_schema`
3. **Handle errors gracefully** with try/catch blocks
4. **Use appropriate collection intervals** to avoid overloading
5. **Monitor plugin health** regularly for external plugins
6. **Secure API keys** for external plugins (never commit to version control)

---

## Related Documentation

- [Plugin Development Guide](./PLUGIN_DEVELOPMENT.md) (Coming Soon)
- [Wiki: Plugin Development Progress](https://github.com/mylaniakea/unity/wiki/Plugin-Development-Progress)
- [Plugin Showcase](./unity_plugins_showcase.html)
- [Plugin Validator Tool](../backend/app/plugins/tools/plugin_validator.py)
