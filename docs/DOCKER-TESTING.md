# Docker Testing Guide for Credential Management

## Quick Start with Docker

### 1. Build and Start Services

```bash
cd /home/matthew/projects/HI/unity

# Build and start all services (PostgreSQL, backend, frontend)
docker-compose up -d --build

# Check logs
docker-compose logs -f backend
```

### 2. Verify Services

```bash
# Check all containers are running
docker-compose ps

# Test backend health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

### 3. Test Credential Management API

```bash
# Get statistics (requires auth - create user first)
curl http://localhost:8000/api/credentials/stats

# View all available endpoints
curl http://localhost:8000/openapi.json | jq '.paths | keys[] | select(contains("credentials"))'
```

## Environment Variables

The following are configured in docker-compose.yml:

- **PostgreSQL Database**:
  - `POSTGRES_DB=homelab_db`
  - `POSTGRES_USER=homelab_user`
  - `POSTGRES_PASSWORD=homelab_password`

- **Backend**:
  - `DATABASE_URL=postgresql+psycopg2://homelab_user:homelab_password@db:5432/homelab_db`
  - `ENCRYPTION_KEY=6ty12Z9TYTSM5ESuOuXd_RxLBgunI3G0_TJbCpBb9FU=`
  - `ALLOW_ORIGINS=*`

## Database Schema Creation

On first startup, Unity will automatically create all tables including:
- `ssh_keys`
- `certificates`
- `server_credentials`
- `credential_audit_logs`
- All other Unity tables

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Troubleshooting

### Backend won't start
```bash
# Check backend logs
docker-compose logs backend

# Rebuild backend
docker-compose up -d --build backend
```

### Database connection issues
```bash
# Check if PostgreSQL is ready
docker-compose exec db pg_isready

# Access PostgreSQL directly
docker-compose exec db psql -U homelab_user -d homelab_db
```

### ENCRYPTION_KEY not set
```bash
# Verify environment variable in container
docker-compose exec backend env | grep ENCRYPTION_KEY
```

## Development Mode

For hot-reloading during development, uncomment this line in docker-compose.yml:

```yaml
volumes:
  - ./backend/app:/app/app
```

Then restart:
```bash
docker-compose restart backend
```

## Production Deployment

Before deploying to production:

1. **Change passwords** in docker-compose.yml:
   - PostgreSQL password
   - JWT secret (add to environment)

2. **Generate new encryption key**:
   ```bash
   python3 backend/generate_encryption_key.py
   ```
   Update docker-compose.yml with new key

3. **Remove debug flags**:
   - Change `--log-level debug` to `--log-level info`
   - Set `DEBUG=false`

4. **Enable HTTPS**:
   - Add reverse proxy (nginx/traefik)
   - Configure SSL certificates

5. **Backup database**:
   ```bash
   docker-compose exec db pg_dump -U homelab_user homelab_db > backup.sql
   ```
