# Unity Alerting System

Comprehensive guide to the Unity homelab monitoring platform's alerting system.

## Overview

The Unity alerting system provides automated monitoring, evaluation, and notification of infrastructure issues across your homelab. It supports multiple resource types, flexible alert conditions, configurable notification channels, and full alert lifecycle management.

## Architecture

### Components

1. **Alert Rules** - Define what to monitor and when to alert
2. **Alert Evaluator** - Periodically checks rules against current metrics
3. **Alert Lifecycle Service** - Manages alert state transitions
4. **Alert Scheduler** - Runs evaluations every 60 seconds
5. **Notification Service** - Delivers alerts via 78+ channels (Apprise)

### Data Flow

```
Alert Rule (enabled) → Scheduler (60s) → Evaluator → Condition Met? 
    → Lifecycle Service → Create Alert → Notification Service → Channel(s)
```

### Database Schema

**alert_rules** table:
- `id` - Primary key
- `name` - Rule name
- `description` - Optional description
- `resource_type` - What to monitor (server, device, pool, database)
- `metric_name` - Metric to check (e.g., cpu_usage, memory_used)
- `condition` - Comparison operator (gt, lt, gte, lte, eq, ne)
- `threshold` - Threshold value
- `severity` - Alert severity (info, warning, critical)
- `enabled` - Whether rule is active
- `notification_channels` - JSON array of channel IDs
- `cooldown_minutes` - Minimum time between alerts (default: 15)
- `created_at`, `updated_at` - Timestamps

**alerts** table:
- Links to alert_rules via `alert_rule_id`
- Tracks `resource_type` and `resource_id`
- Status: active → acknowledged → resolved
- Timestamps for triggered, acknowledged, resolved
- Support for snoozing

## Alert Rules

### Resource Types

- **server** - Monitored servers
- **device** - Storage devices
- **pool** - Storage pools
- **database** - Database instances

### Conditions

- **gt** - Greater than (>)
- **lt** - Less than (<)
- **gte** - Greater than or equal (>=)
- **lte** - Less than or equal (<=)
- **eq** - Equal (==)
- **ne** - Not equal (!=)

### Severity Levels

- **info** - Informational alerts
- **warning** - Warning condition
- **critical** - Critical issue requiring immediate attention

### Example Rules

#### High CPU Usage
```json
{
  "name": "High CPU Usage",
  "resource_type": "server",
  "metric_name": "cpu_usage",
  "condition": "gt",
  "threshold": 80.0,
  "severity": "warning",
  "enabled": true,
  "cooldown_minutes": 15
}
```

#### Low Disk Space
```json
{
  "name": "Low Disk Space",
  "resource_type": "device",
  "metric_name": "available_space_gb",
  "condition": "lt",
  "threshold": 10.0,
  "severity": "critical",
  "enabled": true,
  "cooldown_minutes": 60
}
```

#### Database Connection Failure
```json
{
  "name": "Database Unreachable",
  "resource_type": "database",
  "metric_name": "is_connected",
  "condition": "eq",
  "threshold": 0,
  "severity": "critical",
  "enabled": true,
  "cooldown_minutes": 5
}
```

## Alert Lifecycle

### States

1. **Active** - Alert triggered, condition met
2. **Acknowledged** - User has seen the alert
3. **Resolved** - Condition no longer met or manually resolved

### State Transitions

```
[Condition Met] → Active
Active → Acknowledged (manual)
Active → Resolved (auto or manual)
Acknowledged → Resolved (manual)
```

### Actions

- **Acknowledge** - Mark alert as seen (user_id tracked)
- **Resolve** - Close alert (auto when condition clears or manual)
- **Snooze** - Temporarily suppress notifications (duration in minutes)

### Cooldown Period

Prevents alert fatigue by enforcing a minimum time between alerts for the same rule and resource. Default is 15 minutes.

## Notification Channels

Unity uses Apprise for notification delivery, supporting 78+ services including:

- **Email** (SMTP)
- **Slack**
- **Discord**
- **Microsoft Teams**
- **Telegram**
- **PagerDuty**
- **Pushover**
- **ntfy**
- And many more...

### Configuration

Notification channels are managed via the notification_channels API:

```bash
POST /api/notifications/channels
{
  "name": "Slack Alerts",
  "apprise_url": "slack://token/channel",
  "service_type": "slack",
  "is_active": true
}
```

### Alert Notifications

When an alert is triggered, acknowledged, or resolved, notifications are sent with:

- Emoji indicators (🚨 triggered, 👀 acknowledged, ✅ resolved)
- Alert ID and severity
- Resource information
- Alert message
- Timestamp

## API Endpoints

### Alert Rules

#### List Rules
```http
GET /api/v1/monitoring/alert-rules?enabled=true&severity=critical
```

Query parameters:
- `enabled` - Filter by enabled status
- `resource_type` - Filter by resource type
- `severity` - Filter by severity
- `skip`, `limit` - Pagination

#### Create Rule
```http
POST /api/v1/monitoring/alert-rules
Content-Type: application/json

{
  "name": "High Memory Usage",
  "metric": "memory_percent",
  "condition": "gt",
  "threshold_value": 90.0,
  "severity": "warning",
  "enabled": true
}
```

#### Get Rule
```http
GET /api/v1/monitoring/alert-rules/{rule_id}
```

#### Update Rule
```http
PUT /api/v1/monitoring/alert-rules/{rule_id}
Content-Type: application/json

{
  "threshold_value": 85.0,
  "enabled": false
}
```

#### Delete Rule
```http
DELETE /api/v1/monitoring/alert-rules/{rule_id}
```

#### Enable/Disable Rule
```http
POST /api/v1/monitoring/alert-rules/{rule_id}/enable
POST /api/v1/monitoring/alert-rules/{rule_id}/disable
```

#### Test Rule
```http
POST /api/v1/monitoring/alert-rules/{rule_id}/test
```

Response:
```json
{
  "success": true,
  "rule_id": 1,
  "rule_name": "High CPU Usage",
  "triggered": 2,
  "resolved": 0,
  "message": "Evaluated rule 'High CPU Usage': 2 triggered, 0 resolved"
}
```

### Alerts

#### List Alerts
```http
GET /api/v1/monitoring/alerts?unresolved_only=true&limit=50
```

#### Acknowledge Alert
```http
POST /api/v1/monitoring/alerts/{alert_id}/acknowledge
```

#### Resolve Alert
```http
POST /api/v1/monitoring/alerts/{alert_id}/resolve
```

#### Snooze Alert
```http
POST /api/v1/monitoring/alerts/{alert_id}/snooze
Content-Type: application/json

{
  "duration_minutes": 60
}
```

#### Bulk Operations
```http
POST /api/v1/monitoring/alerts/acknowledge-all
POST /api/v1/monitoring/alerts/resolve-all

# With specific alert IDs
{
  "alert_ids": [1, 2, 3]
}
```

## Configuration

### Environment Variables

```bash
# Scheduler interval (seconds)
ALERT_EVALUATION_INTERVAL=60

# Default cooldown (minutes)
ALERT_DEFAULT_COOLDOWN=15

# Enable/disable alert scheduler
ENABLE_ALERT_SCHEDULER=true
```

### Application Settings

The alert scheduler is automatically started when the Unity application starts:

```python
# In app/main.py
alert_scheduler = get_alert_scheduler(interval_seconds=60)
alert_scheduler.start()
```

## Monitoring & Debugging

### Logs

Alert system logs are written with the following logger names:
- `app.services.monitoring.alert_scheduler` - Scheduler events
- `app.services.monitoring.alert_lifecycle` - Alert state changes
- `app.services.infrastructure.alert_evaluator` - Rule evaluation

Example log output:
```
2025-12-22 15:20:00 - INFO - Alert scheduler started (interval: 60s)
2025-12-22 15:21:00 - INFO - Alert evaluation complete: 5 rules evaluated, 2 triggered, 0 auto-resolved, 0 errors (duration: 0.35s)
2025-12-22 15:21:01 - INFO - Alert triggered: 42 for rule High CPU Usage
2025-12-22 15:21:01 - INFO - Notification sent for alert 42: 2 channels succeeded, 0 failed
```

### Metrics

Monitor alert system health via:
- Number of active alerts
- Evaluation duration
- Notification success/failure rates
- Rules evaluated per cycle

### Manual Trigger

For testing, manually trigger an evaluation:

```python
from app.services.monitoring.alert_scheduler import get_alert_scheduler

scheduler = get_alert_scheduler()
scheduler.trigger_evaluation_now()
```

## Troubleshooting

### Alerts Not Triggering

1. **Check rule is enabled**
   ```bash
   GET /api/v1/monitoring/alert-rules/{rule_id}
   ```

2. **Verify metric exists on resource**
   - Check that the resource has the metric you're monitoring
   - Use the test endpoint to manually evaluate

3. **Check cooldown period**
   - Recent alerts may be blocked by cooldown
   - View alert history to see last trigger time

4. **Verify scheduler is running**
   - Check application logs for scheduler startup
   - Look for periodic evaluation log messages

### Notifications Not Delivering

1. **Check channel is active**
   ```bash
   GET /api/notifications/channels
   ```

2. **Test channel independently**
   ```bash
   POST /api/v1/monitoring/alerts/channels/{channel_id}/test
   ```

3. **Check notification logs**
   ```bash
   GET /api/v1/monitoring/alerts/notification-logs?alert_id={alert_id}
   ```

4. **Verify Apprise URL format**
   - See [Apprise documentation](https://github.com/caronc/apprise) for URL formats

### High Alert Volume

1. **Increase cooldown period**
   - Edit rule and increase `cooldown_minutes`

2. **Adjust thresholds**
   - Fine-tune thresholds to reduce false positives

3. **Use snooze functionality**
   - Temporarily suppress known issues

4. **Disable noisy rules**
   ```bash
   POST /api/v1/monitoring/alert-rules/{rule_id}/disable
   ```

## Best Practices

1. **Start with higher thresholds** - Tune down to reduce false positives
2. **Use appropriate severity levels** - Reserve "critical" for urgent issues
3. **Set reasonable cooldowns** - Balance alert fatigue vs. information loss
4. **Test rules before enabling** - Use the test endpoint to validate
5. **Monitor notification delivery** - Check success rates regularly
6. **Document custom rules** - Add meaningful descriptions
7. **Regular review** - Periodically review and optimize rules
8. **Staged rollout** - Test rules on non-critical resources first

## Examples

### Complete Workflow

1. **Create a notification channel**
```bash
curl -X POST http://localhost:8000/api/notifications/channels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Slack Ops",
    "apprise_url": "slack://T00000000/B00000000/XXXXXXXXXXXX",
    "service_type": "slack",
    "is_active": true
  }'
```

2. **Create an alert rule**
```bash
curl -X POST http://localhost:8000/api/v1/monitoring/alert-rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Memory Pressure",
    "metric": "memory_percent",
    "condition": "gt",
    "threshold_value": 85.0,
    "severity": "warning",
    "enabled": true
  }'
```

3. **Test the rule**
```bash
curl -X POST http://localhost:8000/api/v1/monitoring/alert-rules/1/test
```

4. **Monitor alerts**
```bash
curl http://localhost:8000/api/v1/monitoring/alerts?unresolved_only=true
```

5. **Acknowledge an alert**
```bash
curl -X POST http://localhost:8000/api/v1/monitoring/alerts/42/acknowledge
```

## Migration from Legacy System

If migrating from threshold_rules or plugin-based alerts:

1. Export existing rules
2. Map to new alert_rules schema
3. Create rules via API
4. Disable old system
5. Monitor for 24-48 hours
6. Remove old rules

## Future Enhancements

- Alert templates
- Complex conditions (AND/OR logic)
- Alert dependencies
- Escalation policies
- Maintenance windows
- Alert history analytics
- ML-based threshold recommendations

## Support

For issues or questions:
- GitHub Issues: [unity/issues](https://github.com/your-repo/unity/issues)
- Documentation: [unity/docs](https://github.com/your-repo/unity/docs)
