# Plugin Templates

Ready-to-use templates for creating Unity monitoring plugins.

## Available Templates

1. **http_service_template.py** - Monitor HTTP/HTTPS endpoints
   - Health checks
   - Response time monitoring
   - SSL verification
   - Custom status codes

## Quick Start

```bash
# 1. Copy template
cp app/plugins/templates/http_service_template.py app/plugins/builtin/my_monitor.py

# 2. Edit the plugin
# - Change plugin ID
# - Update metadata
# - Customize collect_data() logic

# 3. Test it
python -c "
from app.plugins.builtin.my_monitor import MyMonitorPlugin
import asyncio
plugin = MyMonitorPlugin(config={'url': 'https://example.com'})
print(asyncio.run(plugin.collect_data()))
"

# 4. Enable in Unity
curl -X POST http://localhost:8000/api/plugins/v2/enable/my-monitor
```

## Template Structure

All templates include:
- ✅ Complete PluginMetadata
- ✅ Configuration schema with validation
- ✅ Error handling
- ✅ Type hints
- ✅ Docstrings
- ✅ Example usage

## Customization Guide

See [Plugin Development Guide](../../../docs/PLUGIN_DEVELOPMENT_GUIDE.md) for:
- Configuration schemas
- Error handling patterns
- Best practices
- Testing strategies
