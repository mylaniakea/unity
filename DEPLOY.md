# Unity Production Deployment Guide

## Quick Start with GitHub Container Registry

### Prerequisites
- Docker and Docker Compose installed
- GitHub account access
- 2GB RAM minimum, 4GB recommended

### 1. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` and set **required** values:
```bash
# Database
POSTGRES_PASSWORD=<strong-password>

# Security (REQUIRED for production)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Optional: Configure CORS
CORS_ORIGINS=http://your-domain.com
```

### 2. Deploy from GHCR

```bash
# Pull and start services
docker compose -f docker-compose.prod.yml up -d

# Run database migrations
docker exec homelab-backend python -c "
from alembic.config import Config
from alembic import command
cfg = Config('alembic.ini')
command.upgrade(cfg, 'head')
"
```

### 3. Access Unity

- **Frontend**: http://localhost (or your domain)
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Create Admin User

```bash
docker exec -it homelab-backend python -c "
from app.core.database import SessionLocal
from app.services.auth.user_service import create_user
from app.models.auth import UserRole

db = SessionLocal()
user = create_user(
    db,
    username='admin',
    email='admin@localhost',
    password='changeme123',
    full_name='Admin User',
    role=UserRole.ADMIN
)
print(f'Created admin user: {user.username}')
"
```

**⚠️ Change the default password immediately after first login!**

## Configuration Reference

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | `strong-password-123` |
| `JWT_SECRET_KEY` | JWT signing key | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | Credential encryption | `Fernet.generate_key()` |

### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `info` | Logging level |
| `CORS_ORIGINS` | `*` | Allowed origins (comma-separated) |
| `DEPLOYMENTS_ENABLED` | `true` | Enable stack deployments |

## Post-Deployment

### Enable Plugins

1. Login to Unity frontend
2. Navigate to Plugins page
3. Enable desired monitoring plugins
4. Configure plugin settings

### Create Dashboard

1. Go to Dashboards
2. Click "Create Dashboard"
3. Add widgets from available plugins
4. Save and view real-time metrics

## Troubleshooting

### Check Container Status
```bash
docker compose -f docker-compose.prod.yml ps
```

### View Logs
```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

### Reset Database
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
# Re-run migrations
```

## Building from Source

If you want to build locally instead of using GHCR:

```bash
docker compose build
docker compose up -d
```

## Security Checklist

- [ ] Changed default passwords
- [ ] Set strong JWT_SECRET_KEY
- [ ] Set ENCRYPTION_KEY
- [ ] Configure CORS_ORIGINS (no wildcards)
- [ ] Set DEBUG=false
- [ ] Enable HTTPS (reverse proxy recommended)
- [ ] Regular backups configured
- [ ] Monitor logs for suspicious activity

## Support

- Documentation: `/docs` directory
- API Docs: http://localhost:8000/docs
- GitHub: https://github.com/mylaniakea/unity
