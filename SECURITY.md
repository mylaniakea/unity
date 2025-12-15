# Security Best Practices - Unity Plugin System

This document outlines the security measures implemented in the Unity plugin system.

## Authentication & Authorization

### User Authentication (JWT)
- All user-facing endpoints require JWT token authentication
- Tokens validated using `get_current_active_user` dependency
- Role-Based Access Control (RBAC): admin, operator, user

### External Plugin Authentication (API Keys)
- API keys are hashed (SHA-256) before storage
- Keys validated using `verify_plugin_api_key` dependency
- Granular permissions: report_metrics, update_health, get_config

## Input Validation

- Plugin ID: 1-100 chars, alphanumeric + dash/underscore only
- Dangerous patterns blocked: `../`, `/etc/`, `<script`, `eval(`, etc.
- Size limits: Config (100KB), Metrics (500KB)

## Rate Limiting

| Operation | Limit | Window |
|-----------|-------|--------|
| Plugin execution | 10 requests | 60 seconds |
| Metric reporting | 100 requests | 60 seconds |

## Audit Logging

All plugin operations logged with format:
```
PLUGIN_AUDIT: [SUCCESS/FAILED] user=<username> plugin=<id> action=<action>
```

## Best Practices

1. Use strong JWT secrets in production
2. Set API key expiration dates
3. Monitor audit logs for suspicious activity
4. Use HTTPS for all communications
5. Regular security updates

