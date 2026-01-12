# Database Migration Quick Start

**Status Check:** Run these commands to verify migration status

## Fast Track - Run Migrations Now

```bash
# Option 1: Use the migration job (RECOMMENDED)
kubectl apply -f /home/holon/Projects/unity/k8s/jobs/migrate-database.yaml
kubectl logs -n unity job/unity-db-migrate -f

# Option 2: Use the automated script
bash /home/holon/Projects/unity/check_migrations.sh

# Option 3: Manual commands
kubectl exec -n unity deployment/unity-backend -- alembic upgrade head
```

## Verify Migrations Are Current

```bash
# Check current version
kubectl exec -n unity deployment/unity-backend -- alembic current

# Check latest version
kubectl exec -n unity deployment/unity-backend -- alembic heads

# Both should show: add_plugin_execution (head)
```

## What Migrations Exist?

The Unity database has 8 migrations:
1. Initial setup (empty)
2. Users, API keys, audit logs
3. Notification channels and logs
4. OAuth authentication links
5. Alert rules for monitoring
6. Plugins table
7. Marketplace and dashboards
8. **Plugin execution tracking (latest)** ← This is what you need

## Expected Latest Version

**Current head:** `add_plugin_execution`

This migration adds three new tables:
- `plugin_executions` - Track plugin runs
- `plugin_metrics` - Store plugin metrics
- `plugin_alerts` - Plugin-specific alerts

## Files Reference

- **Automated script:** `/home/holon/Projects/unity/check_migrations.sh`
- **Migration job:** `/home/holon/Projects/unity/k8s/jobs/migrate-database.yaml`
- **Deployment with auto-migrations:** `/home/holon/Projects/unity/k8s/deployments/backend-with-migrations.yaml`
- **Full guide:** `/home/holon/Projects/unity/DATABASE_MIGRATION_GUIDE.md`
- **Migration details:** `/home/holon/Projects/unity/MIGRATION_STATUS.md`

## Quick Health Check After Migration

```bash
# Check backend is healthy
kubectl get pods -n unity -l app=unity-backend

# Check application health endpoint
kubectl exec -n unity deployment/unity-backend -- curl -s http://localhost:8000/health | grep -A 10 database

# Should show database status: "healthy"
```

## Troubleshooting

**Error: "No such file or directory"**
→ Alembic files missing from container, rebuild Docker image

**Error: Database connection failed**
→ Check postgres pod is running: `kubectl get pods -n unity | grep postgres`

**Error: Migration fails**
→ Check logs: `kubectl logs -n unity job/unity-db-migrate`

**Need more help?**
→ See full guide: `/home/holon/Projects/unity/DATABASE_MIGRATION_GUIDE.md`
