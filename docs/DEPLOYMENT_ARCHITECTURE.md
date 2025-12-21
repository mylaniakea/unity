# Unity Deployment Architecture

**Last Updated**: December 21, 2024  
**Version**: 1.0.0 (Runs 1-5 Complete)

## Overview

Unity is deployed as a multi-container application using Docker Compose. This document describes the deployment architecture, component interactions, and configuration.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                    (homelab-net)                         │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Frontend   │─────▶│   Backend    │                │
│  │   (React)    │      │   (FastAPI)  │                │
│  │   Port: 80   │      │   Port: 8000 │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                                │                         │
│                        ┌───────▼────────┐               │
│                        │   PostgreSQL   │               │
│                        │   Port: 5432   │               │
│                        └────────────────┘               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Backend (FastAPI)

**Container**: `homelab-backend` (or `homelab-backend-dev`)
**Image**: Built from `./backend/Dockerfile`
**Port**: 8000
**Responsibilities**:
- REST API endpoints (10 active endpoints)
- WebSocket real-time streaming
- Plugin scheduler (APScheduler)
- Metrics collection and storage
- Data processing pipeline

**Key Files**:
- `backend/app/main.py` - Application entry point
- `backend/app/api/` - API routes
- `backend/app/services/plugin_scheduler.py` - Background scheduler
- `backend/app/models/` - Database models

**Health Check**: `GET /health`

### 2. Database (PostgreSQL)

**Container**: `homelab-db` (or `homelab-db-dev`)
**Image**: `postgres:16-alpine`
**Port**: 5432
**Database**: `homelab_db`
**Responsibilities**:
- Store plugin registrations
- Store time-series metrics
- Store plugin execution history
- Store plugin health status

**Data Persistence**: 
- Volume: `homelab_db_data` or `homelab_db_data_dev`
- Location: `/var/lib/postgresql/data`

**Optional**: Can use SQLite for development (`sqlite:///./data/homelab.db`)

### 3. Frontend (React)

**Container**: `homelab-frontend` (or `homelab-frontend-dev`)
**Image**: Built from `./frontend/Dockerfile`
**Port**: 80 (production), 5173 (dev server)
**Responsibilities**:
- User interface
- Real-time dashboard
- Plugin management UI
- WebSocket client for live updates

**Status**: Planned (not yet implemented in Runs 1-5)

## Network Configuration

**Network Name**: `homelab-net`
**Driver**: bridge

**Port Mapping**:
- `80` → Frontend (HTTP)
- `8000` → Backend (API)
- `5432` → PostgreSQL (Database)
- `5173` → Vite dev server (development only)

## Data Flow

### Plugin Execution Flow
```
1. PluginScheduler triggers plugin
   ↓
2. Plugin.collect_data() executes
   ↓
3. Metrics stored in PostgreSQL
   ↓
4. WebSocket broadcast to connected clients
   ↓
5. API serves metrics on demand
```

### API Request Flow
```
1. Client → HTTP Request → Backend:8000
   ↓
2. FastAPI router handles request
   ↓
3. Query PostgreSQL database
   ↓
4. Return JSON response
```

### Real-time Updates Flow
```
1. Client connects to ws://backend:8000/ws/metrics
   ↓
2. PluginScheduler executes plugin
   ↓
3. Metrics stored in database
   ↓
4. WebSocket broadcast sent to all connected clients
   ↓
5. Client receives real-time update
```

## Deployment Modes

### Development Mode

**File**: `docker-compose.dev.yml`

**Features**:
- Hot-reload enabled for backend (code changes auto-restart)
- Hot-reload enabled for frontend (Vite dev server)
- Debug logging enabled
- Source code mounted as volumes
- Development database (separate volume)

**Start**:
```bash
docker-compose -f docker-compose.dev.yml up
```

### Production Mode

**File**: `docker-compose.yml`

**Features**:
- Optimized builds
- No source code mounting
- Info-level logging
- Restart policies: `unless-stopped`
- Persistent data volumes

**Start**:
```bash
docker-compose up -d
```

## Environment Configuration

See `.env.example` for all available settings. Key variables:

**Required**:
- `DATABASE_URL` - Database connection string
- `ENCRYPTION_KEY` - For credential encryption

**Optional**:
- `DEBUG` - Enable debug mode (default: false)
- `LOG_LEVEL` - Logging level (default: info)
- `CORS_ORIGINS` - Allowed CORS origins
- `JWT_SECRET_KEY` - For authentication (when implemented)

## Data Persistence

### Volumes

**Production**:
- `homelab_db_data` - PostgreSQL data
- `./backend/data` - SQLite (if used), logs, SSH keys

**Development**:
- `homelab_db_data_dev` - PostgreSQL data (separate from prod)
- `./backend` - Mounted for hot-reload

### Backup Locations

**Database**: 
- PostgreSQL: `/var/lib/postgresql/data` in container
- SQLite: `./backend/data/homelab.db` on host

**Application Data**:
- `./backend/data/` - Logs, keys, SQLite

## Scaling Considerations

### Current Architecture (Runs 1-5)
- Single backend instance
- Single database instance
- Suitable for: Single homelab, <100 plugins, <10 servers

### Future Scaling Options
- **Horizontal**: Multiple backend instances behind load balancer
- **Caching**: Redis for metrics caching (partially implemented)
- **Database**: TimescaleDB for time-series optimization
- **Monitoring**: Prometheus/Grafana integration

## Security

### Network Isolation
- All services on private `homelab-net` bridge network
- Only frontend and backend expose public ports
- Database not directly accessible from host

### Secrets Management
- Environment variables via `.env` file
- Encryption key for stored credentials
- JWT tokens for authentication (when implemented)
- **Important**: Change default secrets in production!

## Monitoring

### Health Checks

**Backend**:
```bash
curl http://localhost:8000/health
# Returns: {"status": "healthy", "scheduler": "running"}
```

**Database**:
```bash
docker exec homelab-db pg_isready -U homelab_user
```

### Logs

**View logs**:
```bash
docker-compose logs -f backend
docker-compose logs -f db
```

**Log locations** (in containers):
- Backend: stdout (captured by Docker)
- PostgreSQL: `/var/lib/postgresql/data/log/`

## Troubleshooting

### Backend won't start
- Check database connection: `docker-compose logs db`
- Verify `DATABASE_URL` in environment
- Check port 8000 not in use: `lsof -i :8000`

### Database connection failed
- Ensure database container is running: `docker ps`
- Check credentials match in docker-compose and .env
- Wait for database to initialize (takes ~10s on first start)

### Port conflicts
- Check ports not in use: `lsof -i :80,8000,5432`
- Change port mappings in docker-compose if needed

## References

- Docker Compose files: `docker-compose.yml`, `docker-compose.dev.yml`
- Environment template: `.env.example`
- API documentation: `docs/RUN4_API_LAYER.md`
- Testing guide: `docs/RUN5_TESTING.md`

---

**Next**: See `DEVELOPMENT_SETUP.md` for local setup instructions
