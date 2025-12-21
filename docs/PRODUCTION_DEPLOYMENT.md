# Unity Production Deployment Guide

**Last Updated**: December 21, 2024  
**Version**: 1.0.0 (Runs 1-5 Complete)

## Overview

This guide covers deploying Unity to production using Docker Compose. For development setup, see `DEVELOPMENT_SETUP.md`.

## Pre-Deployment Checklist

### Security
- [ ] Change all default passwords in `.env`
- [ ] Generate new `ENCRYPTION_KEY`
- [ ] Generate new `JWT_SECRET_KEY`
- [ ] Set `DEBUG=false`
- [ ] Configure proper `CORS_ORIGINS` (remove wildcards)
- [ ] Review exposed ports

### Infrastructure
- [ ] Ensure Docker 20.10+ installed
- [ ] Ensure Docker Compose 2.0+ installed
- [ ] Allocate sufficient resources (minimum: 2GB RAM, 10GB disk)
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificate (if exposing externally)

### Data
- [ ] Plan backup strategy
- [ ] Configure volume mounts for persistence
- [ ] Test database connection

## Production Deployment Steps

### 1. Prepare Environment

```bash
# Clone repository
git clone <repository-url>
cd unity

# Create production .env from template
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with production values:

```bash
# === CRITICAL: Change These ===
ENCRYPTION_KEY=<generate-with-script>
JWT_SECRET_KEY=<use-strong-random-key>
DATABASE_URL=postgresql+psycopg2://homelab_user:<STRONG_PASSWORD>@db:5432/homelab_db

# === Application ===
DEBUG=false
LOG_LEVEL=info

# === Security ===
CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com

# === Database Password ===
# Also update in docker-compose.yml POSTGRES_PASSWORD
```

**Generate encryption key**:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Generate JWT secret**:
```bash
openssl rand -hex 32
```

### 3. Update Docker Compose

Edit `docker-compose.yml`:

```yaml
services:
  db:
    environment:
      POSTGRES_PASSWORD: <STRONG_PASSWORD>  # Match .env
    volumes:
      - /path/to/persistent/storage/db:/var/lib/postgresql/data
  
  backend:
    restart: always  # Changed from unless-stopped
    environment:
      - DATABASE_URL=postgresql+psycopg2://homelab_user:<STRONG_PASSWORD>@db:5432/homelab_db
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    # Remove development volume mounts
```

### 4. Build and Start Services

```bash
# Build images
docker-compose build

# Start in detached mode
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Expected output**:
```
NAME                IMAGE              STATUS
homelab-backend     unity-backend      Up 10 seconds
homelab-db          postgres:16-alpine Up 15 seconds
homelab-frontend    unity-frontend     Up 10 seconds (if implemented)
```

### 5. Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# Check logs
docker-compose logs backend | tail -20

# Check scheduler is running
docker-compose logs backend | grep "Plugin scheduler started"
```

### 6. Initialize Database (First Time Only)

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Verify tables created
docker-compose exec db psql -U homelab_user -d homelab_db -c "\dt"
```

### 7. Configure Plugins

Register and enable plugins via API:

```bash
# Example: Enable docker_monitor plugin
curl -X POST http://localhost:8000/api/plugins/docker_monitor/enable \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "config": {"interval": 60}}'
```

## SSL/TLS Configuration

### Option 1: Reverse Proxy (Recommended)

Use nginx or Caddy as reverse proxy:

```nginx
# /etc/nginx/sites-available/unity
server {
    listen 443 ssl http2;
    server_name unity.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/unity.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/unity.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
    }

    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Option 2: Direct HTTPS

Modify docker-compose.yml to mount certificates:

```yaml
backend:
  volumes:
    - ./certs:/certs:ro
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile /certs/key.pem --ssl-certfile /certs/cert.pem
```

## Backup Strategy

### Database Backup

**Automated daily backup**:
```bash
# Create backup script: /opt/unity/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/unity/backups"
mkdir -p $BACKUP_DIR

docker-compose exec -T db pg_dump -U homelab_user homelab_db | gzip > $BACKUP_DIR/unity_db_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "unity_db_*.sql.gz" -mtime +30 -delete
```

**Add to crontab**:
```bash
0 2 * * * /opt/unity/backup.sh
```

### Restore from Backup

```bash
# Stop backend to prevent conflicts
docker-compose stop backend

# Restore database
gunzip -c /opt/unity/backups/unity_db_20241221_020000.sql.gz | \
  docker-compose exec -T db psql -U homelab_user homelab_db

# Restart backend
docker-compose start backend
```

### Application Data Backup

```bash
# Backup data directory
tar -czf unity_data_$(date +%Y%m%d).tar.gz backend/data/
```

## Monitoring

### Health Checks

Create monitoring script `/opt/unity/healthcheck.sh`:

```bash
#!/bin/bash
HEALTH=$(curl -s http://localhost:8000/health)
STATUS=$(echo $HEALTH | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
    echo "Unity is unhealthy: $HEALTH"
    # Send alert (email, Slack, etc.)
    exit 1
fi
```

Run every 5 minutes:
```bash
*/5 * * * * /opt/unity/healthcheck.sh
```

### Log Monitoring

```bash
# Check for errors
docker-compose logs backend | grep ERROR

# Monitor scheduler
docker-compose logs backend | grep -i scheduler

# Watch real-time
docker-compose logs -f --tail=100 backend
```

### Resource Usage

```bash
# Container stats
docker stats homelab-backend homelab-db

# Disk usage
docker system df
du -sh backend/data/
```

## Scaling Considerations

### Current Limits (Single Instance)
- ~100 plugins
- ~10 monitored servers
- ~1000 metrics/minute

### When to Scale
- High CPU usage (>80% sustained)
- Slow API response times (>500ms)
- Database connection pool exhaustion
- Large number of plugins (>200)

### Scaling Options
1. **Vertical**: Increase container resources
2. **Horizontal**: Multiple backend instances + load balancer
3. **Database**: Separate PostgreSQL server
4. **Caching**: Enable Redis for metrics caching

## Updating Unity

### Update Process

```bash
# 1. Backup first!
/opt/unity/backup.sh

# 2. Pull latest code
git pull origin main

# 3. Rebuild images
docker-compose build

# 4. Stop services
docker-compose down

# 5. Run migrations
docker-compose run --rm backend alembic upgrade head

# 6. Start with new version
docker-compose up -d

# 7. Verify
curl http://localhost:8000/health
```

### Rollback

```bash
# Stop current version
docker-compose down

# Checkout previous version
git checkout <previous-commit>

# Restore database if schema changed
# (see Backup Strategy section)

# Start previous version
docker-compose up -d
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs backend

# Check disk space
df -h

# Check port conflicts
lsof -i :8000,5432

# Restart services
docker-compose restart
```

### High Memory Usage

```bash
# Check container memory
docker stats

# Reduce plugin collection frequency
# Or disable unused plugins via API

# Increase container memory limit in docker-compose.yml:
services:
  backend:
    mem_limit: 2g
```

### Database Performance Issues

```bash
# Check database size
docker-compose exec db psql -U homelab_user homelab_db -c "
SELECT pg_size_pretty(pg_database_size('homelab_db'));"

# Check active connections
docker-compose exec db psql -U homelab_user homelab_db -c "
SELECT count(*) FROM pg_stat_activity;"

# Consider retention policy
# Set RETENTION_DAYS in .env to limit historical data
```

## Security Best Practices

1. **Never commit `.env` to version control**
2. **Use strong passwords (20+ characters)**
3. **Enable firewall - only expose necessary ports**
4. **Keep Docker and images updated**
5. **Monitor logs for suspicious activity**
6. **Use SSL/TLS for external access**
7. **Implement authentication (when available)**
8. **Regular security audits**

## Performance Tuning

See `PERFORMANCE_TUNING.md` for detailed optimization guide.

**Quick wins**:
- Enable Redis caching (when implemented)
- Adjust plugin collection intervals
- Configure database connection pooling
- Use PostgreSQL instead of SQLite

## Support

- Documentation: `docs/` directory
- Architecture: `DEPLOYMENT_ARCHITECTURE.md`
- Development: `DEVELOPMENT_SETUP.md`
- Testing: `docs/RUN5_TESTING.md`
- API Reference: `docs/RUN4_API_LAYER.md`

---

**Production Deployment**: ✅ Complete  
**Next Steps**: Configure monitoring and backups
