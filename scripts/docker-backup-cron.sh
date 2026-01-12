#!/bin/bash
# Add this to your crontab for automated backups
# Example: 0 2 * * * /path/to/unity/scripts/docker-backup-cron.sh

cd "$(dirname "$0")/.."
./scripts/backup-database.sh >> ./backups/backup.log 2>&1
