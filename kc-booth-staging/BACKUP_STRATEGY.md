# Backup Strategy

## Overview
This document outlines backup procedures for kc-booth's PostgreSQL database, which contains critical SSH keys, server configurations, and certificates.

## Database Backup

### Manual Backup
```bash
# Full database backup
docker exec kc-booth-db pg_dump -U kc-booth-user -d kc-booth-db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker exec kc-booth-db pg_dump -U kc-booth-user -d kc-booth-db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Custom format (recommended - supports parallel restore)
docker exec kc-booth-db pg_dump -U kc-booth-user -d kc-booth-db -Fc -f /tmp/backup.dump
docker cp kc-booth-db:/tmp/backup.dump ./backup_$(date +%Y%m%d_%H%M%S).dump
```

### Automated Backup Script
Create `backup.sh`:
```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/backups/kc-booth"
RETENTION_DAYS=30
DB_CONTAINER="kc-booth-db"
DB_USER="kc-booth-user"
DB_NAME="kc-booth-db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kc-booth_$TIMESTAMP.sql.gz"

# Perform backup
echo "Starting backup at $(date)"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup completed: $BACKUP_FILE ($SIZE)"
else
    echo "ERROR: Backup failed!"
    exit 1
fi

# Remove old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "kc-booth_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully at $(date)"
```

Make executable:
```bash
chmod +x backup.sh
```

### Cron Schedule
Add to crontab (`crontab -e`):
```cron
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/kc-booth-backup.log 2>&1

# Weekly backup at 3 AM on Sundays
0 3 * * 0 /path/to/backup.sh >> /var/log/kc-booth-backup-weekly.log 2>&1
```

## Restore Procedures

### From SQL Dump
```bash
# Uncompress and restore
gunzip -c backup_20250101_020000.sql.gz | docker exec -i kc-booth-db psql -U kc-booth-user -d kc-booth-db

# Or from uncompressed
docker exec -i kc-booth-db psql -U kc-booth-user -d kc-booth-db < backup_20250101_020000.sql
```

### From Custom Format
```bash
# Copy dump into container
docker cp backup_20250101_020000.dump kc-booth-db:/tmp/restore.dump

# Restore with parallel jobs
docker exec kc-booth-db pg_restore -U kc-booth-user -d kc-booth-db -j 4 /tmp/restore.dump
```

### Fresh Restore (drop existing)
```bash
# WARNING: This will DELETE all existing data!

# Stop the application
docker compose down

# Start only the database
docker compose up -d db

# Drop and recreate database
docker exec -it kc-booth-db psql -U kc-booth-user -d postgres -c "DROP DATABASE IF EXISTS \"kc-booth-db\";"
docker exec -it kc-booth-db psql -U kc-booth-user -d postgres -c "CREATE DATABASE \"kc-booth-db\";"

# Restore from backup
gunzip -c backup_20250101_020000.sql.gz | docker exec -i kc-booth-db psql -U kc-booth-user -d kc-booth-db

# Start application
docker compose up -d
```

## Backup Verification

### Test Restore (in separate environment)
```bash
# Create test database
docker exec kc-booth-db psql -U kc-booth-user -d postgres -c "CREATE DATABASE test_restore;"

# Restore to test database
gunzip -c backup.sql.gz | docker exec -i kc-booth-db psql -U kc-booth-user -d test_restore

# Verify data
docker exec kc-booth-db psql -U kc-booth-user -d test_restore -c "SELECT COUNT(*) FROM servers;"
docker exec kc-booth-db psql -U kc-booth-user -d test_restore -c "SELECT COUNT(*) FROM ssh_keys;"

# Clean up
docker exec kc-booth-db psql -U kc-booth-user -d postgres -c "DROP DATABASE test_restore;"
```

### Backup Health Check
```bash
#!/bin/bash
# check_backup.sh

BACKUP_DIR="/opt/backups/kc-booth"
MAX_AGE_HOURS=26  # Alert if last backup is older than 26 hours

LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/kc-booth_*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backups found!"
    exit 1
fi

# Check age
AGE_SECONDS=$(( $(date +%s) - $(stat -c %Y "$LATEST_BACKUP") ))
AGE_HOURS=$(( AGE_SECONDS / 3600 ))

if [ $AGE_HOURS -gt $MAX_AGE_HOURS ]; then
    echo "WARNING: Latest backup is $AGE_HOURS hours old (>$MAX_AGE_HOURS)"
    exit 1
fi

echo "OK: Latest backup is $AGE_HOURS hours old"
echo "File: $LATEST_BACKUP"
du -h "$LATEST_BACKUP"
```

## Encryption Key Backup

**CRITICAL**: The `ENCRYPTION_KEY` must be backed up separately and securely!

Without it, encrypted passwords and SSH keys in the database cannot be decrypted.

```bash
# Backup encryption key (store in secure location, NOT with database backups!)
echo "$ENCRYPTION_KEY" > encryption_key.txt
chmod 600 encryption_key.txt

# Recommended: Use a secrets management service
# - HashiCorp Vault
# - AWS Secrets Manager
# - Azure Key Vault
# - 1Password / LastPass (for smaller deployments)
```

## Disaster Recovery Checklist

1. ☐ Restore PostgreSQL database from latest backup
2. ☐ Restore encryption key from secure storage
3. ☐ Verify `.env` configuration matches production
4. ☐ Start services: `docker compose up -d`
5. ☐ Verify health: `curl http://localhost:8001/health`
6. ☐ Test authentication: Login and create test API key
7. ☐ Verify encrypted data: Check that server passwords are accessible
8. ☐ Test certificate rotation on a single server
9. ☐ Monitor logs for errors: `docker compose logs -f app`

## Remote Backup Storage

Consider storing backups off-site:

```bash
# AWS S3
aws s3 cp backup.sql.gz s3://my-bucket/kc-booth-backups/

# rsync to remote server
rsync -avz --delete /opt/backups/kc-booth/ backup-server:/backups/kc-booth/

# rclone (supports multiple cloud providers)
rclone copy /opt/backups/kc-booth/ remote:kc-booth-backups/
```

## Backup Storage Requirements

- **Frequency**: Daily (minimum), hourly for critical environments
- **Retention**: 30 days (daily), 12 months (weekly), 7 years (monthly for compliance)
- **Location**: Off-site + different availability zone/region
- **Encryption**: Backups should be encrypted at rest
- **Testing**: Restore test monthly to verify backup integrity

## Monitoring

Set up alerts for:
- Backup failures
- Backup age exceeds threshold
- Backup size anomalies (too small = incomplete)
- Disk space on backup storage

Example with email notification:
```bash
# In backup.sh, add at the end:
if [ $? -eq 0 ]; then
    echo "Backup successful" | mail -s "kc-booth backup OK" admin@example.com
else
    echo "Backup FAILED!" | mail -s "kc-booth backup FAILED" admin@example.com
fi
```
