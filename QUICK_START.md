# Quick Start - Local Testing

## Step 1: Create .env File

```bash
cp .env.example .env
```

The defaults in `.env.example` are safe for local testing. For production, you'll need to change:
- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY` 
- `ENCRYPTION_KEY`

## Step 2: Start Docker

Make sure Docker Desktop or OrbStack is running:

```bash
# Check Docker status
docker info
```

If Docker isn't running, start Docker Desktop or OrbStack.

## Step 3: Run the Test

```bash
# Automated test
./test-local.sh

# OR manual test
docker compose up -d --build
```

## Step 4: Verify

```bash
# Check service status
docker compose ps

# Test endpoints
curl http://localhost:8000/health
curl http://localhost/

# View logs
docker compose logs -f
```

## Troubleshooting

### Docker daemon not running
- Start Docker Desktop or OrbStack
- Wait for it to fully start
- Run `docker info` to verify

### Port conflicts
If ports 80 or 8000 are already in use:
```bash
# Check what's using the ports
lsof -i :80
lsof -i :8000

# Stop conflicting services or change ports in docker-compose.yml
```

### Services not starting
```bash
# View detailed logs
docker compose logs backend
docker compose logs frontend
docker compose logs db

# Restart services
docker compose restart
```

### Clean start
```bash
# Stop and remove everything
docker compose down -v

# Rebuild and start
docker compose up -d --build
```

