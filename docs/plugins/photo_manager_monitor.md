# Photo Manager Monitor Plugin

## Overview
The **Photo Manager Monitor** tracks photo management platforms. Your memories, meticulously monitored!

## Features
- PhotoPrism monitoring
- Immich monitoring
- API health checks
- Version tracking
- Simple connectivity verification

## Configuration

### PhotoPrism
```yaml
plugins:
  photo-manager-monitor:
    enabled: true
    config:
      platform: "photoprism"
      url: "https://photos.example.com"
      timeout: 10
```

### Immich
```yaml
plugins:
  photo-manager-monitor:
    enabled: true
    config:
      platform: "immich"
      url: "https://immich.example.com"
      api_key: "your-api-key"  # Optional
      timeout: 10
```

## Requirements
- Running PhotoPrism or Immich instance
- Network access to the platform
- API key (optional, for enhanced Immich metrics)

## Metrics Collected
- Online/offline status
- Health check results
- Platform version
- API availability

## Use Cases
- Photo library availability
- Service uptime tracking
- Version monitoring for updates
- API health verification

## Example Output
```json
{
  "platform": "immich",
  "url": "https://immich.example.com",
  "summary": {
    "online": true,
    "healthy": true
  },
  "info": {
    "version": "1.91"
  }
}
```

## Tips
- Keep platforms updated for security
- Monitor during backup operations
- Track API response times
- Use HTTPS with reverse proxy
- Store API keys securely
