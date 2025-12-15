# Audit Logging

## Overview
kc-booth includes comprehensive audit logging for compliance and security tracking. All user actions are logged to the database with details about who performed what action on which resource.

## Audit Log Structure
Each audit log entry contains:
- **Timestamp** - When the action occurred (UTC)
- **User ID & Username** - Who performed the action
- **Action** - What was done (CREATE, UPDATE, DELETE, LOGIN, etc.)
- **Resource Type** - Type of resource affected (server, ssh_key, certificate, api_key, user)
- **Resource ID & Name** - Specific resource affected
- **Details** - Additional context (JSON string)
- **IP Address** - Client IP that initiated the action
- **Correlation ID** - Request trace ID for cross-referencing with logs

## Tracked Actions
- `CREATE` - Resource creation
- `UPDATE` - Resource modification
- `DELETE` - Resource deletion
- `LOGIN` - User authentication
- `ISSUE_CERTIFICATE` - Certificate issuance
- `ROTATE_CERTIFICATE` - Automated certificate rotation
- `DISTRIBUTE_CERTIFICATE` - Certificate distribution to server

## API Endpoints

### Get Audit Logs
```bash
GET /audit/logs/
```

Query parameters:
- `user_id` (optional) - Filter by user ID
- `resource_type` (optional) - Filter by resource type
- `action` (optional) - Filter by action
- `limit` (default: 100) - Max results
- `offset` (default: 0) - Pagination offset

Example:
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8001/audit/logs/?resource_type=server&action=CREATE&limit=50"
```

### Get Resource Audit Trail
```bash
GET /audit/resource/{resource_type}/{resource_id}/
```

Get complete history for a specific resource.

Example:
```bash
# Get all audit logs for server ID 5
curl -H "X-API-Key: your-key" \
  "http://localhost:8001/audit/resource/server/5/"
```

## Integration Example

### Manual Audit Logging
```python
from src.audit import log_audit_event
from src import logger as log_module

# Log server creation
log_audit_event(
    db=db,
    action="CREATE",
    resource_type="server",
    user_id=current_user.id,
    username=current_user.username,
    resource_id=new_server.id,
    resource_name=new_server.hostname,
    details='{"ip": "192.168.1.10"}',
    ip_address=request.client.host,
    correlation_id=log_module.get_correlation_id()
)
```

### Automatic Audit Logging (TODO)
To automatically log all CRUD operations, add audit logging to crud.py functions:

```python
# In crud.py
from . import audit

def create_server(db: Session, server: schemas.ServerCreate, user_id: int, username: str):
    db_server = models.Server(**server.model_dump())
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    
    # Audit log
    audit.log_audit_event(
        db, "CREATE", "server",
        user_id=user_id, username=username,
        resource_id=db_server.id, resource_name=db_server.hostname
    )
    
    return db_server
```

## Compliance Reports

### All Actions by User
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8001/audit/logs/?user_id=1&limit=1000"
```

### All Deletions
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8001/audit/logs/?action=DELETE"
```

### Certificate Operations
```bash
curl -H "X-API-Key: your-key" \
  "http://localhost:8001/audit/logs/?resource_type=certificate"
```

## Database Queries

### Direct SQL Queries
```sql
-- Recent actions (last 24 hours)
SELECT * FROM audit_logs 
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- All actions on a specific server
SELECT * FROM audit_logs
WHERE resource_type = 'server' AND resource_id = 5
ORDER BY timestamp ASC;

-- Failed login attempts
SELECT * FROM audit_logs
WHERE action = 'LOGIN' AND details LIKE '%failed%'
ORDER BY timestamp DESC;

-- Actions by user
SELECT action, resource_type, COUNT(*) as count
FROM audit_logs
WHERE user_id = 1
GROUP BY action, resource_type;
```

## Retention Policy
Consider implementing log retention policies:

```sql
-- Delete audit logs older than 1 year
DELETE FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '1 year';
```

Add to crontab for automated cleanup:
```cron
# Monthly audit log cleanup (keep 1 year)
0 3 1 * * docker exec kc-booth-db psql -U kc-booth-user -d kc-booth-db -c "DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '1 year';"
```

## Security Considerations
- **Access Control**: Only authenticated users can query audit logs
- **Immutability**: Audit logs should never be modified or deleted (except by retention policy)
- **Storage**: Consider archiving old logs to cold storage for long-term compliance
- **Monitoring**: Alert on suspicious patterns (e.g., mass deletions, failed logins)

## Export for Analysis
```bash
# Export to CSV
docker exec kc-booth-db psql -U kc-booth-user -d kc-booth-db -c "\COPY (SELECT * FROM audit_logs ORDER BY timestamp DESC) TO STDOUT WITH CSV HEADER" > audit_logs.csv

# Export to JSON
docker exec kc-booth-db psql -U kc-booth-user -d kc-booth-db -t -c "SELECT json_agg(audit_logs) FROM audit_logs" > audit_logs.json
```
