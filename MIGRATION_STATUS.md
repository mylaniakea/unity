# Unity Database Migration Status Report

**Generated:** 2026-01-04
**Project:** Unity Kubernetes Deployment
**Database:** PostgreSQL (Alembic migrations)

---

## Migration Chain

The Unity backend uses Alembic for database migrations. The current migration chain is:

```
6a00ea433c25 (Initial migration)
 └─> 12e8b371598f (Add authentication tables)
     └─> 70974ae864ff (Add notification tables)
         └─> 12df4f8e6ba9 (Add OAuth links)
             └─> 8f3d9e2a1c45 (Add alert rules)
                 └─> 00001_add_plugins (Add plugins table)
                     └─> a1b2c3d4e5f6 (Add marketplace and dashboard tables)
                         └─> add_plugin_execution (Add plugin execution tables) ← LATEST
```

## Migration Files

All migration files are located in: `/home/holon/Projects/unity/backend/alembic/versions/`

### 1. Initial Migration (6a00ea433c25)
- **File:** `6a00ea433c25_initial_migration.py`
- **Date:** 2025-12-15
- **Changes:** Empty initial migration

### 2. Authentication Tables (12e8b371598f)
- **File:** `12e8b371598f_add_authentication_tables.py`
- **Date:** 2025-12-21
- **Changes:**
  - Creates `users` table
  - Creates `api_keys` table
  - Creates `audit_logs` table
  - Adds indexes for performance

### 3. Notification Tables (70974ae864ff)
- **File:** `70974ae864ff_add_notification_tables.py`
- **Date:** 2025-12-22
- **Changes:**
  - Creates `notification_channels` table
  - Creates `notification_logs` table
  - Supports Apprise notification system

### 4. OAuth Links (12df4f8e6ba9)
- **File:** `12df4f8e6ba9_add_oauth_links.py`
- **Date:** 2025-12-22
- **Changes:**
  - Creates `user_oauth_links` table
  - Supports OAuth authentication providers

### 5. Alert Rules (8f3d9e2a1c45)
- **File:** `8f3d9e2a1c45_add_alert_rules.py`
- **Date:** 2025-12-22
- **Changes:**
  - Creates `alert_rules` table
  - Adds monitoring and alerting capabilities

### 6. Plugins Table (00001_add_plugins)
- **File:** `00001_add_plugins_table.py`
- **Date:** 2026-01-03
- **Changes:**
  - Creates `plugins` table
  - Supports plugin system with metadata and configuration

### 7. Marketplace and Dashboard Tables (a1b2c3d4e5f6)
- **File:** `a1b2c3d4e5f6_add_marketplace_and_dashboard_tables.py`
- **Date:** 2025-12-17
- **Changes:**
  - Creates `marketplace_plugins` table
  - Creates `plugin_reviews` table
  - Creates `plugin_installations` table
  - Creates `plugin_downloads` table
  - Creates `dashboards` table
  - Creates `dashboard_widgets` table
  - Adds `conditions_json` column to `alert_rules`

### 8. Plugin Execution Tables (add_plugin_execution) ← **LATEST**
- **File:** `1767484908_add_plugin_execution_tables.py`
- **Date:** 2026-01-03
- **Changes:**
  - Creates `plugin_executions` table
  - Creates `plugin_metrics` table
  - Creates `plugin_alerts` table
  - Supports plugin execution tracking and metrics

---

## How to Verify and Update Migrations

### Option 1: Using the Automated Script

A shell script has been created to automate the migration verification process:

```bash
# Make the script executable (if not already)
chmod +x /home/holon/Projects/unity/check_migrations.sh

# Run the script
./check_migrations.sh
```

The script will:
1. Check the current migration version in the deployed pod
2. Check the latest available migration version
3. Automatically run migrations if needed
4. Verify the migration completed successfully

### Option 2: Manual Verification

Run these commands manually to check and update migrations:

```bash
# 1. Check current migration version
kubectl exec -n unity deployment/unity-backend -- alembic current

# 2. Check latest available migration version
kubectl exec -n unity deployment/unity-backend -- alembic heads

# 3. If migrations are behind, upgrade to latest
kubectl exec -n unity deployment/unity-backend -- alembic upgrade head

# 4. Verify the migration completed
kubectl exec -n unity deployment/unity-backend -- alembic current
```

### Expected Output

When migrations are **up to date**, you should see:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
add_plugin_execution (head)
```

When migrations are **behind**, the output will show an older revision ID or no revision at all.

---

## Troubleshooting

### Issue: "No such file or directory" error
**Cause:** The alembic configuration or migration files are not present in the container.
**Solution:** Ensure the backend Docker image includes the `alembic/` directory and `alembic.ini` file.

### Issue: Database connection error
**Cause:** The database credentials or connection settings are incorrect.
**Solution:** Check the database environment variables in the deployment configuration.

### Issue: Migration fails with constraint violations
**Cause:** Existing data conflicts with new schema changes.
**Solution:**
1. Review the migration file to understand what's changing
2. Manually fix conflicting data if necessary
3. Consider creating a data migration script

### Issue: "Target database is not up to date"
**Cause:** Multiple migration heads or branched migration history.
**Solution:** Run `alembic heads` to see all heads, then merge or upgrade appropriately.

---

## Database Schema Summary

After all migrations are applied, the database contains these tables:

### Authentication & Users
- `users` - User accounts
- `api_keys` - API authentication keys
- `audit_logs` - Security and activity logs
- `user_oauth_links` - OAuth provider connections

### Notifications & Alerts
- `notification_channels` - Notification delivery channels
- `notification_logs` - Notification history
- `alert_rules` - Monitoring alert definitions

### Plugins
- `plugins` - Installed plugins
- `marketplace_plugins` - Available marketplace plugins
- `plugin_reviews` - User reviews of plugins
- `plugin_installations` - Plugin installation tracking
- `plugin_downloads` - Plugin download statistics
- `plugin_executions` - Plugin execution history
- `plugin_metrics` - Plugin performance metrics
- `plugin_alerts` - Plugin-specific alerts

### Dashboards
- `dashboards` - User dashboard configurations
- `dashboard_widgets` - Dashboard widget layouts

---

## Next Steps

1. **Run the verification script** or manual commands to check migration status
2. **Apply any pending migrations** using `alembic upgrade head`
3. **Verify the application** is running correctly after migrations
4. **Monitor logs** for any database-related errors
5. **Test plugin functionality** to ensure the execution tables are working

---

## References

- Alembic documentation: https://alembic.sqlalchemy.org/
- Backend configuration: `/home/holon/Projects/unity/backend/alembic.ini`
- Migration files: `/home/holon/Projects/unity/backend/alembic/versions/`
- Database models: `/home/holon/Projects/unity/backend/app/models/`
