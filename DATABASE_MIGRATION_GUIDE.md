# Unity Database Migration Guide

This guide provides multiple methods to verify and apply database migrations in the Unity Kubernetes deployment.

---

## Quick Start - Choose Your Method

### Method 1: Run Migration Job (Recommended)
```bash
# Apply the migration job
kubectl apply -f /home/holon/Projects/unity/k8s/jobs/migrate-database.yaml

# Watch the job status
kubectl get jobs -n unity -w

# View migration logs
kubectl logs -n unity job/unity-db-migrate

# Clean up the job when done
kubectl delete job unity-db-migrate -n unity
```

### Method 2: Manual kubectl exec
```bash
# Run the automated script
bash /home/holon/Projects/unity/check_migrations.sh

# Or run commands manually:
kubectl exec -n unity deployment/unity-backend -- alembic current
kubectl exec -n unity deployment/unity-backend -- alembic heads
kubectl exec -n unity deployment/unity-backend -- alembic upgrade head
```

### Method 3: Add Init Container (Automatic on Pod Restart)
```bash
# Replace the current deployment with one that includes init container
kubectl apply -f /home/holon/Projects/unity/k8s/deployments/backend-with-migrations.yaml

# This will automatically run migrations whenever pods restart
```

---

## Detailed Instructions

### Method 1: Migration Job (Best for One-Time Updates)

**Advantages:**
- Dedicated job for migrations
- Clear logs and status
- Doesn't affect running pods
- Easy to retry on failure

**Steps:**

1. **Apply the migration job:**
   ```bash
   kubectl apply -f /home/holon/Projects/unity/k8s/jobs/migrate-database.yaml
   ```

2. **Monitor the job:**
   ```bash
   # Check job status
   kubectl get jobs -n unity

   # Expected output when successful:
   # NAME               COMPLETIONS   DURATION   AGE
   # unity-db-migrate   1/1           15s        30s
   ```

3. **View detailed logs:**
   ```bash
   kubectl logs -n unity job/unity-db-migrate
   ```

4. **Expected successful output:**
   ```
   ==============================================
   Unity Database Migration Job
   ==============================================

   Step 1: Checking current migration version...
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   <current_version> (head)

   Step 2: Checking latest available version...
   add_plugin_execution (head)

   Step 3: Running migrations...
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running upgrade -> add_plugin_execution

   Step 4: Verifying final version...
   add_plugin_execution (head)

   ==============================================
   Migration completed successfully!
   ==============================================
   ```

5. **Clean up (optional):**
   ```bash
   # Job auto-deletes after 1 hour, or delete manually:
   kubectl delete job unity-db-migrate -n unity
   ```

6. **Re-run if needed:**
   ```bash
   # Delete old job first
   kubectl delete job unity-db-migrate -n unity

   # Apply again
   kubectl apply -f /home/holon/Projects/unity/k8s/jobs/migrate-database.yaml
   ```

---

### Method 2: Manual kubectl exec (Quick Check)

**Advantages:**
- Quick verification
- No additional resources needed
- Direct interaction with running pod

**Steps:**

1. **Check current migration version:**
   ```bash
   kubectl exec -n unity deployment/unity-backend -- alembic current
   ```

   **Expected output if up to date:**
   ```
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   add_plugin_execution (head)
   ```

2. **Check latest available version:**
   ```bash
   kubectl exec -n unity deployment/unity-backend -- alembic heads
   ```

   **Expected output:**
   ```
   add_plugin_execution (head)
   ```

3. **If migrations are behind, upgrade:**
   ```bash
   kubectl exec -n unity deployment/unity-backend -- alembic upgrade head
   ```

4. **Verify the upgrade:**
   ```bash
   kubectl exec -n unity deployment/unity-backend -- alembic current
   ```

**Automated Script:**
```bash
# Make executable
chmod +x /home/holon/Projects/unity/check_migrations.sh

# Run the script
bash /home/holon/Projects/unity/check_migrations.sh
```

---

### Method 3: Init Container (Automatic Migrations)

**Advantages:**
- Migrations run automatically on every pod restart
- Ensures database is always up to date
- No manual intervention needed

**Disadvantages:**
- Slightly longer pod startup time
- Migrations run on every pod restart (can be wasteful)

**Steps:**

1. **Review the updated deployment:**
   ```bash
   cat /home/holon/Projects/unity/k8s/deployments/backend-with-migrations.yaml
   ```

2. **Apply the updated deployment:**
   ```bash
   kubectl apply -f /home/holon/Projects/unity/k8s/deployments/backend-with-migrations.yaml
   ```

3. **Watch pods restart:**
   ```bash
   kubectl get pods -n unity -w
   ```

4. **Check init container logs:**
   ```bash
   # Get the pod name
   POD=$(kubectl get pods -n unity -l app=unity-backend -o jsonpath='{.items[0].metadata.name}')

   # View init container logs
   kubectl logs -n unity $POD -c migrate
   ```

5. **Expected init container output:**
   ```
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL.
   INFO  [alembic.runtime.migration] Running upgrade -> add_plugin_execution
   ```

---

## Migration Chain Reference

Current migration order (from oldest to newest):

```
1. 6a00ea433c25    - Initial migration (empty)
2. 12e8b371598f   - Add authentication tables (users, api_keys, audit_logs)
3. 70974ae864ff   - Add notification tables
4. 12df4f8e6ba9   - Add OAuth links
5. 8f3d9e2a1c45   - Add alert rules
6. 00001_add_plugins - Add plugins table
7. a1b2c3d4e5f6   - Add marketplace and dashboard tables
8. add_plugin_execution - Add plugin execution tables (LATEST)
```

---

## Troubleshooting

### Problem: "No such file or directory" when running alembic

**Cause:** Alembic configuration or migration files missing from container

**Solution:**
```bash
# Verify alembic files are in the container
kubectl exec -n unity deployment/unity-backend -- ls -la /app/alembic/versions/
kubectl exec -n unity deployment/unity-backend -- cat /app/alembic.ini
```

If files are missing, rebuild the Docker image:
```bash
cd /home/holon/Projects/unity/backend
docker build -t unity-backend:latest .
```

---

### Problem: Database connection error

**Cause:** Database credentials or connection settings incorrect

**Solution:**
```bash
# Check database secret exists
kubectl get secret unity-secrets -n unity

# Verify database is running
kubectl get pods -n unity | grep postgres

# Test connection from backend pod
kubectl exec -n unity deployment/unity-backend -- env | grep DATABASE_URL
```

---

### Problem: Migration fails with "Target database is not up to date"

**Cause:** Multiple migration heads or branched migration history

**Solution:**
```bash
# Check for multiple heads
kubectl exec -n unity deployment/unity-backend -- alembic heads

# View migration history
kubectl exec -n unity deployment/unity-backend -- alembic history

# If multiple heads exist, you may need to merge them
# This requires creating a merge migration locally
```

---

### Problem: Migration fails with constraint violations

**Cause:** Existing data conflicts with new schema changes

**Solution:**
1. Review the failing migration to understand the change
2. Check database for conflicting data
3. Manually fix data or create a data migration
4. Re-run the migration

```bash
# Connect to database to inspect data
kubectl exec -n unity deployment/postgres -- psql -U homelab_user -d homelab_db

# Example: Check for duplicate values
SELECT column_name, COUNT(*)
FROM table_name
GROUP BY column_name
HAVING COUNT(*) > 1;
```

---

### Problem: Job shows "BackoffLimitExceeded"

**Cause:** Migration failed multiple times

**Solution:**
```bash
# View job details
kubectl describe job unity-db-migrate -n unity

# Check pod logs for error details
kubectl logs -n unity job/unity-db-migrate

# Fix the underlying issue, then delete and recreate job
kubectl delete job unity-db-migrate -n unity
kubectl apply -f /home/holon/Projects/unity/k8s/jobs/migrate-database.yaml
```

---

## Verification Checklist

After running migrations, verify everything is working:

- [ ] **Check migration version matches latest:**
  ```bash
  kubectl exec -n unity deployment/unity-backend -- alembic current
  # Should show: add_plugin_execution (head)
  ```

- [ ] **Verify backend pods are running:**
  ```bash
  kubectl get pods -n unity -l app=unity-backend
  # Should show: Running status
  ```

- [ ] **Check backend logs for errors:**
  ```bash
  kubectl logs -n unity deployment/unity-backend --tail=50
  # Should not show database-related errors
  ```

- [ ] **Test health endpoint:**
  ```bash
  kubectl exec -n unity deployment/unity-backend -- curl http://localhost:8000/health
  # Should return healthy status with database component
  ```

- [ ] **Verify tables were created:**
  ```bash
  kubectl exec -n unity deployment/postgres -- psql -U homelab_user -d homelab_db -c "\dt"
  # Should list all tables including plugin_executions, plugin_metrics, plugin_alerts
  ```

- [ ] **Test plugin functionality:**
  - Access Unity frontend
  - Navigate to Plugins page
  - Enable/disable a plugin
  - Check plugin execution logs

---

## Files Created

This guide references the following files:

1. **Migration Check Script:**
   - Location: `/home/holon/Projects/unity/check_migrations.sh`
   - Purpose: Automated script to check and apply migrations
   - Usage: `bash check_migrations.sh`

2. **Migration Status Report:**
   - Location: `/home/holon/Projects/unity/MIGRATION_STATUS.md`
   - Purpose: Detailed information about all migrations
   - Usage: Reference document

3. **Deployment with Init Container:**
   - Location: `/home/holon/Projects/unity/k8s/deployments/backend-with-migrations.yaml`
   - Purpose: Backend deployment that auto-runs migrations
   - Usage: `kubectl apply -f k8s/deployments/backend-with-migrations.yaml`

4. **Migration Job:**
   - Location: `/home/holon/Projects/unity/k8s/jobs/migrate-database.yaml`
   - Purpose: One-time job to run migrations
   - Usage: `kubectl apply -f k8s/jobs/migrate-database.yaml`

---

## Best Practices

1. **Always backup database before migrations:**
   ```bash
   kubectl exec -n unity deployment/postgres -- pg_dump -U homelab_user homelab_db > backup.sql
   ```

2. **Test migrations in development first:**
   - Create a copy of production database
   - Run migrations on the copy
   - Verify application works
   - Then apply to production

3. **Use the Job method for production:**
   - More controlled
   - Better logging
   - Easy to monitor and retry

4. **Monitor application after migrations:**
   - Check logs for errors
   - Test critical functionality
   - Monitor performance metrics

5. **Keep migration history in version control:**
   - All migration files are tracked in Git
   - Never modify existing migrations
   - Create new migrations for schema changes

---

## Support

For issues or questions:
- Check logs: `kubectl logs -n unity deployment/unity-backend`
- Review migration files: `/home/holon/Projects/unity/backend/alembic/versions/`
- Consult Alembic docs: https://alembic.sqlalchemy.org/
