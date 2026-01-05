# Database Migration Resources

This directory contains comprehensive resources for managing database migrations in the Unity Kubernetes deployment.

## Quick Links

- **Start Here:** [MIGRATION_QUICKSTART.md](MIGRATION_QUICKSTART.md) - Fast commands to verify and apply migrations
- **Full Summary:** [MIGRATION_VERIFICATION_SUMMARY.md](MIGRATION_VERIFICATION_SUMMARY.md) - Complete analysis and recommendations
- **Detailed Guide:** [DATABASE_MIGRATION_GUIDE.md](DATABASE_MIGRATION_GUIDE.md) - Step-by-step instructions with troubleshooting
- **Migration Details:** [MIGRATION_STATUS.md](MIGRATION_STATUS.md) - Information about each migration
- **Visual Reference:** [migration-chain.txt](migration-chain.txt) - ASCII diagram of migration flow

## Tools Available

### 1. Automated Script
**File:** `check_migrations.sh`

Run this script to automatically check and apply migrations:
```bash
chmod +x check_migrations.sh
bash check_migrations.sh
```

### 2. Kubernetes Migration Job
**File:** `k8s/jobs/migrate-database.yaml`

Apply migrations using a dedicated Kubernetes Job:
```bash
kubectl apply -f k8s/jobs/migrate-database.yaml
kubectl logs -n unity job/unity-db-migrate -f
```

### 3. Auto-Migration Deployment
**File:** `k8s/deployments/backend-with-migrations.yaml`

Deploy backend with init container that runs migrations automatically:
```bash
kubectl apply -f k8s/deployments/backend-with-migrations.yaml
```

## Fastest Path to Verify Migrations

```bash
# 1. Check current status
kubectl exec -n unity deployment/unity-backend -- alembic current

# 2. If not showing "add_plugin_execution (head)", run migrations:
kubectl apply -f k8s/jobs/migrate-database.yaml

# 3. Watch the migration job
kubectl logs -n unity job/unity-db-migrate -f

# 4. Verify success
kubectl exec -n unity deployment/unity-backend -- alembic current
```

## Expected Result

Your database should be at version: **add_plugin_execution (head)**

This is migration #8, which adds plugin execution tracking, metrics, and alerts.

## Need Help?

1. Check the [Quick Start Guide](MIGRATION_QUICKSTART.md) for common commands
2. Review the [Troubleshooting Section](DATABASE_MIGRATION_GUIDE.md#troubleshooting) in the full guide
3. Examine [Migration Details](MIGRATION_STATUS.md) for specific migration information
4. View the [Visual Chain](migration-chain.txt) to understand the migration sequence

## File Index

| File | Purpose |
|------|---------|
| `README_MIGRATIONS.md` | This file - overview and index |
| `MIGRATION_QUICKSTART.md` | Quick reference for fast execution |
| `MIGRATION_VERIFICATION_SUMMARY.md` | Complete analysis and recommendations |
| `DATABASE_MIGRATION_GUIDE.md` | Comprehensive step-by-step guide |
| `MIGRATION_STATUS.md` | Detailed information about each migration |
| `migration-chain.txt` | Visual diagram of migration flow |
| `check_migrations.sh` | Automated verification and migration script |
| `k8s/jobs/migrate-database.yaml` | Kubernetes Job for migrations |
| `k8s/deployments/backend-with-migrations.yaml` | Deployment with auto-migration init container |

## Migration Files Location

Source migration files are located at:
```
/home/holon/Projects/unity/backend/alembic/versions/
```

These files are copied into the Docker container during build and available at:
```
/app/alembic/versions/
```

## Support

For issues or questions about migrations:
- Review the documentation above
- Check backend logs: `kubectl logs -n unity deployment/unity-backend`
- Verify database connectivity: `kubectl get pods -n unity | grep postgres`
- Consult Alembic documentation: https://alembic.sqlalchemy.org/

---

**Last Updated:** 2026-01-04
