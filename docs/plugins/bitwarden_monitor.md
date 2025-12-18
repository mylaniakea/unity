# Bitwarden/Vaultwarden Monitor Plugin

## Overview
The **Bitwarden/Vaultwarden Monitor** tracks your password manager instance health. Because your secrets vault should never be a secret failure!

## Features
- API availability monitoring
- Web vault accessibility checks
- Identity/OAuth endpoint validation
- Vaultwarden admin diagnostics (optional)
- Overall availability percentage

## Configuration
```yaml
plugins:
  bitwarden-monitor:
    enabled: true
    config:
      url: "https://vault.example.com"
      admin_token: "your-admin-token"  # Optional: for Vaultwarden diagnostics
      timeout: 10
```

## Requirements
- Running Bitwarden or Vaultwarden instance
- Network access to the server
- Admin token (optional, for enhanced Vaultwarden metrics)

## Metrics Collected
- `/alive` endpoint status
- Web vault accessibility
- Identity API availability
- Admin diagnostics (version, database type)
- Overall health score

## Use Cases
- Critical service monitoring
- Uptime tracking
- API health verification
- Version tracking for updates

## Example Output
```json
{
  "summary": {
    "healthy": true,
    "checks_passed": 4,
    "checks_total": 4,
    "availability_percent": 100
  },
  "checks": {
    "alive": {"status": true},
    "web_vault": {"status": true},
    "identity_api": {"status": true},
    "admin_diagnostics": {"status": true, "version": "1.30.1"}
  }
}
```

## Tips
- Keep admin token secure in config
- Alert on any check failures immediately
- Monitor version for security updates
- Track availability trends over time
