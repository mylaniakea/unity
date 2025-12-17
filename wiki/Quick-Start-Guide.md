# Quick Start Guide

Get Unity up and running in under 10 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10+ (for local development)
- PostgreSQL 16+ (or use Docker)
- Git

## 🚀 Quick Start with Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/mylaniakea/unity.git
cd unity
```

### 2. Configure Environment

```bash
cp docker-compose.yml.example docker-compose.yml
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set required variables:
```env
# Database
DATABASE_URL=postgresql://homelab:homelab@homelab-db:5432/homelab

# Security
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ENCRYPTION_KEY=your-fernet-key-here  # Generate with KC-Booth script

# Optional
ENABLE_K8S=false
ENABLE_TRIVY=false
ENABLE_CONTAINER_AI=true
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Unity backend API (port 8000)
- Unity frontend (port 3000)

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec homelab-backend alembic upgrade head

# Create admin user
docker-compose exec homelab-backend python -m app.cli create-admin
```

### 5. Access Unity

Open your browser:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/system/health

Default credentials:
- Username: `admin`
- Password: (set during admin creation)

## 📋 Verify Installation

### Check Services Status

```bash
docker-compose ps
```

All services should show "Up":
```
homelab-db        Up      5432/tcp
homelab-backend   Up      8000/tcp
homelab-frontend  Up      3000/tcp
```

### Test API

```bash
curl http://localhost:8000/api/v1/system/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### Get Authentication Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

Save the `access_token` from the response.

## 🎯 Next Steps

Now that Unity is running, explore the features:

### 1. Set Up SSH Keys (KC-Booth)

```bash
curl -X POST http://localhost:8000/api/v1/credentials/ssh-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-homelab-key",
    "key_type": "ed25519",
    "description": "SSH key for homelab servers"
  }'
```

### 2. Add a Server (BD-Store - Phase 3)

```bash
curl -X POST http://localhost:8000/api/v1/infrastructure/servers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "server1.local",
    "ip_address": "192.168.1.100",
    "username": "root",
    "ssh_key_id": 1,
    "monitoring_enabled": true
  }'
```

### 3. Configure Container Host (Uptainer - Phase 4)

```bash
curl -X POST http://localhost:8000/api/v1/containers/hosts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "docker-host",
    "host_type": "docker",
    "api_url": "unix:///var/run/docker.sock"
  }'
```

## 🔧 Common Tasks

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f homelab-backend

# Last 100 lines
docker-compose logs --tail=100 homelab-backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart backend only
docker-compose restart homelab-backend
```

### Stop Services

```bash
docker-compose down
```

### Update to Latest Version

```bash
git pull origin main
docker-compose down
docker-compose up -d --build
docker-compose exec homelab-backend alembic upgrade head
```

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Check database logs
docker-compose logs homelab-db

# Test database connection
docker-compose exec homelab-db psql -U homelab -d homelab -c "SELECT version();"
```

### Backend Not Starting

```bash
# Check backend logs for errors
docker-compose logs homelab-backend

# Verify environment variables
docker-compose exec homelab-backend env | grep DATABASE_URL
```

### Port Conflicts

If ports 3000, 5432, or 8000 are already in use, edit `docker-compose.yml`:

```yaml
services:
  homelab-backend:
    ports:
      - "8001:8000"  # Changed from 8000
```

## 📚 Learn More

- [[Installation]] - Detailed installation guide
- [[Configuration]] - Configuration reference
- [[API Overview]] - API documentation
- [[Troubleshooting]] - Common issues and solutions
- [[Development Setup]] - Set up local development environment

## 🆘 Need Help?

- Check [[Troubleshooting]] for common issues
- Search [GitHub Issues](https://github.com/mylaniakea/unity/issues)
- Join [GitHub Discussions](https://github.com/mylaniakea/unity/discussions)

---

**Next**: [[Configuration]] | [[API Overview]]
