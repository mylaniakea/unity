# Built-in Plugins

This directory contains built-in plugins that ship with Unity.

## Available Plugins

### System Monitoring

#### system-info
**Category:** System  
**Description:** Collects comprehensive system information including CPU, memory, disk, and network stats.  
**Requirements:** psutil  
**Configurable:** Yes (network stats can be toggled)

#### process-monitor
**Category:** System  
**Description:** Monitors system processes, tracks top CPU/memory consumers, and provides process counts by status.  
**Requirements:** psutil  
**Configurable:** Yes (top N processes, sort by CPU/memory, include command lines)

### Network Monitoring

#### network-monitor
**Category:** Network  
**Description:** Monitors network interface statistics, throughput, errors, and active connections.  
**Requirements:** psutil  
**Configurable:** Yes (interface filtering, connection tracking)

### Storage Monitoring

#### disk-monitor
**Category:** Storage  
**Description:** Monitors disk usage, I/O statistics, and mounted partitions with configurable warning thresholds.  
**Requirements:** psutil  
**Configurable:** Yes (exclude filesystem types, I/O stats, warning threshold)

---

## Creating a New Built-in Plugin

### 1. Create Plugin File

Create a new Python file in this directory: `your_plugin_name.py`

### 2. Implement PluginBase

```python
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory
from typing import Dict, Any

class YourPlugin(PluginBase):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="your-plugin",
            name="Your Plugin",
            version="1.0.0",
            description="What your plugin does",
            author="Your Name",
            category=PluginCategory.SYSTEM,  # or NETWORK, STORAGE, etc.
            tags=["monitoring", "example"],
            requires_sudo=False,
            supported_os=["linux", "darwin", "windows"],
            dependencies=["psutil"],
            config_schema={
                "type": "object",
                "properties": {
                    "option": {
                        "type": "boolean",
                        "default": True,
                        "description": "An example config option"
                    }
                }
            }
        )
    
    async def collect_data(self) -> Dict[str, Any]:
        """Collect your metrics here"""
        return {
            "timestamp": "...",
            "your_metrics": "..."
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Optional: Check if plugin is healthy"""
        return {
            "healthy": True,
            "message": "Plugin is operational"
        }
```

### 3. Test Your Plugin

Restart Unity and your plugin will be automatically discovered:

```bash
cd backend
uvicorn app.main:app --reload
```

You should see in the logs:
```
📦 Discovered 5 plugin(s):
   - Your Plugin (your-plugin) [○ disabled]
```

### 4. Enable and Test

Use the API to enable and test your plugin:

```bash
# Enable
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/your-plugin/enable

# Execute manually
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/your-plugin/execute

# Check metrics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/your-plugin/metrics
```

---

## Plugin Best Practices

### 1. Error Handling
Always handle exceptions in `collect_data()`. The base class catches them, but you should handle expected errors gracefully.

### 2. Performance
Keep `collect_data()` fast (< 5 seconds). Use caching if needed.

### 3. Configuration
Make plugins configurable via `config_schema`. Use sensible defaults.

### 4. Health Checks
Implement `health_check()` to verify dependencies and prerequisites.

### 5. Validation
Override `on_config_change()` to validate configuration when it changes.

### 6. Documentation
Include clear docstrings explaining what your plugin does and what data it collects.

---

## Categories

Choose the appropriate category for your plugin:

- `PluginCategory.SYSTEM` - System-level monitoring (CPU, memory, processes)
- `PluginCategory.NETWORK` - Network monitoring and statistics
- `PluginCategory.STORAGE` - Disk and storage monitoring
- `PluginCategory.THERMAL` - Temperature and cooling monitoring
- `PluginCategory.CONTAINER` - Container orchestration (Docker, K8s)
- `PluginCategory.DATABASE` - Database monitoring
- `PluginCategory.APPLICATION` - Application-specific monitoring
- `PluginCategory.SECURITY` - Security monitoring and alerts
- `PluginCategory.AI_ML` - AI/ML monitoring and metrics
- `PluginCategory.CUSTOM` - Custom/uncategorized plugins

---

## Testing

Run the plugin directly for quick testing:

```python
import asyncio
from your_plugin_name import YourPlugin

async def test():
    plugin = YourPlugin(config={"option": True})
    metadata = plugin.get_metadata()
    print(f"Testing: {metadata.name}")
    
    health = await plugin.health_check()
    print(f"Health: {health}")
    
    data = await plugin.collect_data()
    print(f"Data: {data}")

asyncio.run(test())
```

---

## Need Help?

- See existing plugins in this directory for examples
- Check [TESTING-GUIDE.md](../../../../TESTING-GUIDE.md) for API usage
- Read [HUB-IMPLEMENTATION-PLAN.md](../../../../HUB-IMPLEMENTATION-PLAN.md) for architecture details
