# Docker Deployment Guide

Unity is designed as a fully containerized application using Docker and Docker Compose.

## Quick Start

### Production Deployment
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development Mode
```bash
# Use development compose file with hot-reloading
docker-compose -f docker-compose.dev.yml up

# Run with build
docker-compose -f docker-compose.dev.yml up --build
```

## Services

### Database (PostgreSQL 16)
- **Container**: `homelab-db`
- **Port**: 5432
- **Credentials**: Set in docker-compose.yml
- **Volume**: `homelab_db_data` (persistent)

### Backend (FastAPI)
- **Container**: `homelab-backend`
- **Port**: 8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/infrastructure/health/detailed
- **Volume**: `./backend/data` for SQLite/uploads

### Frontend (React)
- **Container**: `homelab-frontend`  
- **Port**: 80
- **URL**: http://localhost

## Environment Variables

Edit `docker-compose.yml` or create `.env`:

```env
# Database
POSTGRES_DB=homelab_db
POSTGRES_USER=homelab_user
POSTGRES_PASSWORD=change_in_production

# Backend
DATABASE_URL=postgresql+psycopg2://homelab_user:homelab_password@db:5432/homelab_db
ENCRYPTION_KEY=generate_with_backend/scripts/generate_encryption_key.py
JWT_SECRET_KEY=your-secret-key-change-in-production

# API Keys (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## Database Migrations

After schema changes, run migrations inside the container:

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations
alembic upgrade head

# Exit container
exit
```

## Running Tests

```bash
# Run tests in backend container
docker-compose exec backend pytest tests/ -v

# With coverage
docker-compose exec backend pytest tests/ --cov=app --cov-report=html
```

## Development Workflow

### Backend Development
```bash
# Use dev compose for hot-reloading
docker-compose -f docker-compose.dev.yml up backend

# Code changes auto-reload
# Edit files in ./backend/app/
```

### Frontend Development
```bash
# Use dev compose
docker-compose -f docker-compose.dev.yml up frontend

# Access Vite dev server
# http://localhost:5173
```

## Rebuilding Containers

```bash
# Rebuild after dependency changes
docker-compose build backend

# Rebuild all
docker-compose build

# Force rebuild without cache
docker-compose build --no-cache
```

## Data Persistence

### Database
PostgreSQL data is stored in Docker volume `homelab_db_data`

```bash
# Backup database
docker-compose exec db pg_dump -U homelab_user homelab_db > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T db psql -U homelab_user homelab_db
```

### Backend Data
Application data stored in `./backend/data/`:
- SQLite database (if not using PostgreSQL)
- Uploaded files
- Generated SSH keys
- Logs

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend

# Check if port is in use
sudo lsof -i :8000
```

### Database connection errors
```bash
# Verify database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db psql -U homelab_user -d homelab_db
```

### Permission issues
```bash
# Fix backend/data permissions
sudo chown -R $USER:$USER backend/data/
```

### Clean restart
```bash
# Stop and remove all containers, networks
docker-compose down

# Remove volumes (WARNING: deletes data!)
docker-compose down -v

# Fresh start
docker-compose up -d
```

## Production Considerations

1. **Change default passwords** in docker-compose.yml
2. **Generate secure ENCRYPTION_KEY**:
   ```bash
   docker-compose exec backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. **Use environment files** instead of hardcoded values
4. **Enable HTTPS** with reverse proxy (nginx/traefik)
5. **Set up backup strategy** for database and data volume
6. **Configure resource limits** in docker-compose.yml
7. **Use Docker secrets** for sensitive data
8. **Monitor container logs** with external logging service

## Docker Compose Files

- `docker-compose.yml` - Production configuration
- `docker-compose.dev.yml` - Development with hot-reloading
- `backend/Dockerfile` - Backend image definition
- `frontend/Dockerfile` - Frontend image definition
- `backend/.dockerignore` - Excludes tests, scripts from image

## Networking

All services communicate via `homelab-net` bridge network:
- Backend → Database: `db:5432`
- Frontend → Backend: `backend:8000`
- External → Frontend: `localhost:80`
- External → Backend: `localhost:8000`
- External → Database: `localhost:5432` (dev only)

## Resource Requirements

**Minimum**:
- 2 CPU cores
- 4GB RAM
- 10GB disk space

**Recommended**:
- 4 CPU cores
- 8GB RAM
- 50GB disk space (for logs, backups, data)
