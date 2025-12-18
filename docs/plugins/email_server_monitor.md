# Email Server Monitor Plugin

## Overview
The **Email Server Monitor** tracks self-hosted email servers. Self-hosting email: brave, possibly foolish, definitely monitored!

## Features
- Mail queue monitoring (Postfix/Exim)
- Service status checks (SMTP/IMAP)
- Queue size tracking and alerting
- Multiple MTA support
- Health threshold detection

## Configuration
```yaml
plugins:
  email-server-monitor:
    enabled: true
    config:
      mta: "postfix"  # or "exim"
      check_services: true
```

## Requirements
- Running mail server (Postfix, Exim, etc.)
- `mailq` or `exim` commands available
- Systemd (for service checks)

## Metrics Collected
- Mail queue size and messages
- Queue status (empty/active)
- Service status (postfix, dovecot, exim4)
- Overall health assessment

## Use Cases
- Queue buildup detection
- Service downtime alerts
- Mail delivery monitoring
- Spam/backlog detection

## Example Output
```json
{
  "summary": {
    "queue_size": 3,
    "queue_healthy": true,
    "services_healthy": true,
    "overall_healthy": true
  },
  "queue": {
    "total": 3,
    "status": "active"
  },
  "services": {
    "postfix": {"active": true},
    "dovecot": {"active": true}
  }
}
```

## Tips
- Alert if queue > 100 messages
- Monitor service restarts
- Track queue trends over time
- Check logs for delivery failures
- Keep MTA and security updates current
