# Unity Plugin System - Testing Guide

This guide walks you through testing the plugin system end-to-end.

---

## Prerequisites

- Python 3.11+ installed
- PostgreSQL or SQLite database
- Unity backend dependencies installed

---

## Step 1: Database Setup

### Option A: Fresh Database (Recommended for Testing)

```bash
cd backend

# Set up a test database
export DATABASE_URL="sqlite:///./test_unity.db"

# Create plugin tables
python create_plugin_tables.py
```

**Expected Output:**
```
============================================================
Unity Plugin System - Database Setup
============================================================

Creating plugin tables...
  - plugins
  - plugin_metrics
  - plugin_executions
  - plugin_api_keys

✅ Plugin tables created successfully!
...
============================================================
```

### Option B: Use Existing Database

If Unity is already set up, the tables will be created automatically on startup.

---

## Step 2: Start Unity

```bash
cd backend

# Make sure environment variables are set
export JWT_SECRET_KEY="test-secret-key-do-not-use-in-production"
export DATABASE_URL="sqlite:///./test_unity.db"  # or your PostgreSQL URL

# Start the server
uvicorn app.main:app --reload
```

**Expected Output:**
```
============================================================
Unity - Homelab Intelligence Hub Starting...
============================================================

🔌 Initializing Plugin System...
✅ Plugin system initialized successfully
📦 Discovered 1 plugin(s):
   - System Info (system-info) [○ disabled]

⏰ Configuring scheduled jobs...
   ...
   - Plugin execution: every 5 minutes

✅ Scheduler started successfully

============================================================
🚀 Unity is ready!
============================================================
```

---

## Step 3: Create a User (First Time Only)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "email": "admin@example.com",
    "role": "admin"
  }'
```

---

## Step 4: Get JWT Token

```bash
# Login
curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=admin123"
```

**Save the access_token from response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**For convenience, set as variable:**
```bash
export TOKEN="eyJhbGc..."
```

---

## Step 5: Test Plugin API

### List Plugins

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2
```

**Expected Response:**
```json
{
  "plugins": [
    {
      "id": "system-info",
      "name": "System Info",
      "version": "1.0.0",
      "category": "system",
      "description": "Collects basic system information...",
      "enabled": false,
      "external": false,
      "health_status": "unknown",
      "last_health_check": null
    }
  ],
  "total": 1
}
```

### Get Plugin Details

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/system-info
```

### Enable Plugin

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/system-info/enable
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Plugin system-info enabled",
  "plugin_id": "system-info"
}
```

### Execute Plugin Manually

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/system-info/execute
```

**Expected Response:**
```json
{
  "success": true,
  "plugin_id": "system-info",
  "timestamp": "2025-12-15T02:30:00.000000",
  "data": {
    "timestamp": "2025-12-15T02:30:00.000000",
    "cpu": {
      "usage_percent": 15.2,
      "count": 8,
      "frequency_mhz": 2400.0
    },
    "memory": {
      "total_gb": 16.0,
      "used_gb": 8.5,
      "available_gb": 7.5,
      "percent": 53.1
    },
    ...
  }
}
```

### Get Plugin Metrics

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/system-info/metrics?limit=10
```

### Check Plugin Health

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/system-info/health
```

---

## Step 6: Test API Key System (External Plugins)

### Create API Key

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/plugins/keys \
  -d '{
    "plugin_id": "system-info",
    "name": "Test API Key",
    "permissions": ["report_metrics", "update_health", "get_config"],
    "expires_days": 30
  }'
```

**Save the api_key from response - it's only shown once!**
```json
{
  "api_key": "abc123...",
  "key_info": {
    "id": 1,
    "plugin_id": "system-info",
    "name": "Test API Key",
    ...
  }
}
```

### Use API Key to Report Metrics (as External Plugin)

```bash
curl -X POST \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/plugins/v2/system-info/metrics/report \
  -d '{
    "data": {
      "test_metric": 123,
      "timestamp": "2025-12-15T02:30:00"
    }
  }'
```

---

## Step 7: Monitor Scheduled Execution

After enabling the plugin, it will execute automatically every 5 minutes.

**Watch the logs:**
```
Running plugin execution job...
Executing plugin: system-info
Plugin system-info executed successfully
Plugin execution job completed
```

**Check metrics in database:**
```bash
# View recent metrics
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/plugins/v2/system-info/metrics?limit=5"
```

---

## Step 8: Test Rate Limiting

Try executing the plugin rapidly:

```bash
# This should succeed
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/system-info/execute

# Repeat 10 more times quickly...
# The 11th request should be rate limited

# Expected error response:
{
  "detail": "Rate limit exceeded for plugin_execution: 10 per 60s"
}
```

---

## Step 9: Test Input Validation

### Try Invalid Plugin ID

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/v2/../../../etc/passwd/enable
```

**Expected Response:**
```json
{
  "detail": "Plugin ID contains invalid pattern: ../"
}
```

### Try Oversized Config

```bash
# Create a config larger than 100KB
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/plugins/v2/system-info/config \
  -d '{"config": {"huge_data": "..."}}'  # Over 100KB
```

**Expected Response:**
```json
{
  "detail": "Configuration too large (max 100KB)"
}
```

---

## Troubleshooting

### Plugin Not Found
- Check plugin was discovered on startup
- Verify plugin file is in `backend/app/plugins/builtin/`
- Check logs for plugin loading errors

### Permission Denied
- Verify JWT token is valid (use `/auth/token` to get new one)
- Check user role (some operations require admin)
- Ensure API key has correct permissions (for external plugin endpoints)

### Rate Limited
- Wait 60 seconds for rate limit window to reset
- Or restart the server to reset in-memory rate limiter

### Database Errors
- Verify database tables exist: `python create_plugin_tables.py`
- Check database URL is correct
- Ensure database is accessible

---

## Success Criteria

✅ Plugin system initializes on startup  
✅ Plugin discovered and registered  
✅ Can enable/disable plugin via API  
✅ Plugin executes and stores metrics  
✅ Can query metrics via API  
✅ API key authentication works  
✅ Rate limiting prevents abuse  
✅ Input validation blocks malicious input  
✅ Audit logs capture operations  

---

## Next Steps

Once basic testing is complete:

1. **Create additional plugins** - Follow system-info example
2. **Test external plugins** - Deploy a plugin as separate service
3. **Frontend integration** - Build UI for plugin management
4. **Production deployment** - Set proper JWT secrets, use PostgreSQL
5. **Monitoring** - Watch audit logs, set up alerts

---

**Last Updated:** December 15, 2025
