#!/bin/bash
set -e

# Unity Database Backup Script
# Creates timestamped backups with optional retention policy

BACKUP_DIR="${BACKUP_DIR:-./backups/database}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/unity_backup_${TIMESTAMP}.sql.gz"

# Docker container name
CONTAINER_NAME="${CONTAINER_NAME:-homelab-db}"

# Database credentials (from docker-compose.yml or environment)
DB_USER="${POSTGRES_USER:-homelab_user}"
DB_NAME="${POSTGRES_DB:-homelab_db}"

echo "🔄 Starting Unity database backup..."
echo "   Container: ${CONTAINER_NAME}"
echo "   Database: ${DB_NAME}"
echo "   User: ${DB_USER}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Perform the backup
echo "   Creating backup: ${BACKUP_FILE}"
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists | gzip > "${BACKUP_FILE}"

# Verify the backup was created
if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ Backup completed successfully!"
    echo "   File: ${BACKUP_FILE}"
    echo "   Size: ${SIZE}"
else
    echo "❌ Backup failed - file not created"
    exit 1
fi

# Clean up old backups
if [ "${RETENTION_DAYS}" -gt 0 ]; then
    echo "🧹 Cleaning up backups older than ${RETENTION_DAYS} days..."
    find "${BACKUP_DIR}" -name "unity_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    echo "   Cleanup completed"
fi

# List recent backups
echo ""
echo "📁 Recent backups:"
ls -lh "${BACKUP_DIR}"/unity_backup_*.sql.gz 2>/dev/null | tail -5 || echo "   No backups found"

echo ""
echo "✨ Backup process completed!"
