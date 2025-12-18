# Syncthing Monitor Plugin

## Overview
The **Syncthing Monitor** tracks your P2P file synchronization instances. Decentralized sync, centralized monitoring!

## Features
- Device connection status
- Folder synchronization tracking
- System resource usage
- Version monitoring
- API-based monitoring (no local dependencies)

## Configuration
```yaml
plugins:
  syncthing-monitor:
    enabled: true
    config:
      url: "http://localhost:8384"
      api_key: "your-api-key-here"
      timeout: 10
```

## Requirements
- Running Syncthing instance
- API access enabled
- API key from Syncthing settings

## Metrics Collected
- Total and connected device counts
- Folder statistics and last sync times
- CPU and memory usage
- Uptime tracking
- Sync activity detection

## Use Cases
- Multi-device sync verification
- Network connectivity monitoring
- Performance tracking
- Sync failure detection

## Example Output
```json
{
  "summary": {
    "my_id": "ABCDEFG...",
    "uptime_seconds": 86400,
    "total_devices": 5,
    "connected_devices": 4,
    "total_folders": 3,
    "syncing": true
  },
  "system": {
    "version": "v1.23.7",
    "cpu_percent": 2.5
  }
}
```

## Tips
- Enable GUI authentication for security
- Use HTTPS with reverse proxy
- Monitor device disconnections for alerts
- Track folder last sync for stale detection
- Keep API key secure in config
