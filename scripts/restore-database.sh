#!/bin/bash
set -e

# Unity Database Restore Script
# Restores database from a backup file

BACKUP_FILE="$1"
CONTAINER_NAME="${CONTAINER_NAME:-homelab-db}"
DB_USER="${POSTGRES_USER:-homelab_user}"
DB_NAME="${POSTGRES_DB:-homelab_db}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "❌ Error: Backup file not specified"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/database/unity_backup_*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "⚠️  WARNING: This will replace the current database!"
echo "   Database: ${DB_NAME}"
echo "   Backup file: ${BACKUP_FILE}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

echo ""
echo "🔄 Starting database restore..."

# Stop the backend to prevent connections
echo "   Stopping backend container..."
docker stop homelab-backend 2>/dev/null || true

# Wait a moment for connections to close
sleep 2

# Restore the backup
echo "   Restoring from backup..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

# Restart the backend
echo "   Restarting backend container..."
docker start homelab-backend

echo ""
echo "✅ Database restore completed successfully!"
echo ""
echo "⚠️  Note: If you restored from a different schema version,"
echo "   you may need to run migrations:"
echo "   docker exec homelab-backend alembic upgrade head"
