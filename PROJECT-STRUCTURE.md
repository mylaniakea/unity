# Unity Project Structure

## Overview
Unity is a monorepo containing a FastAPI backend and React frontend for homelab intelligence and monitoring.

## Directory Layout

```
unity/
├── backend/                    # FastAPI backend application
│   ├── app/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── database.py        # Database connection and session management
│   │   ├── models/            # SQLAlchemy ORM models (organized by domain)
│   │   │   ├── __init__.py    # Exports all models for backward compatibility
│   │   │   ├── core.py        # Core business models (ServerProfile, Settings, etc.)
│   │   │   ├── monitoring.py  # Monitoring models (ThresholdRule, Alert, etc.)
│   │   │   ├── users.py       # User and authentication models
│   │   │   ├── plugins.py     # Plugin system models
│   │   │   ├── credentials.py # Credential management models
│   │   │   ├── infrastructure.py  # Infrastructure monitoring models
│   │   │   ├── alert_rules.py # Alert rule definitions
│   │   │   └── error_tracking.py  # Collection error tracking
│   │   ├── routers/           # FastAPI route handlers
│   │   │   ├── profiles.py    # Server profile management
│   │   │   ├── knowledge.py   # Knowledge base operations
│   │   │   ├── reports.py     # Report generation
│   │   │   ├── plugins*.py    # Plugin API endpoints
│   │   │   ├── credentials.py # Credential management
│   │   │   └── infrastructure.py  # Infrastructure monitoring (45+ endpoints)
│   │   ├── services/          # Business logic services
│   │   │   ├── infrastructure/    # Infrastructure monitoring services (10 services)
│   │   │   │   ├── ssh_service.py         # SSH connection management
│   │   │   │   ├── collection_task.py     # Data collection orchestration
│   │   │   │   ├── server_discovery.py    # Server discovery
│   │   │   │   ├── storage_discovery.py   # Storage device discovery
│   │   │   │   ├── pool_discovery.py      # Storage pool discovery
│   │   │   │   ├── database_discovery.py  # Database discovery
│   │   │   │   ├── mdadm_discovery.py     # RAID discovery
│   │   │   │   ├── mysql_metrics.py       # MySQL metrics collection
│   │   │   │   ├── postgres_metrics.py    # PostgreSQL metrics collection
│   │   │   │   ├── alert_evaluator.py     # Alert rule evaluation
│   │   │   │   └── data_retention.py      # Data retention policies
│   │   │   ├── credentials/       # Credential services
│   │   │   │   └── encryption.py  # Encryption/decryption service
│   │   │   └── notification_service.py    # Multi-channel notifications
│   │   ├── utils/             # Utility functions and parsers
│   │   │   └── parsers.py     # System output parsers (lsblk, smartctl, etc.)
│   │   ├── schedulers/        # Background task schedulers
│   │   │   ├── snapshot_tasks.py          # Snapshot scheduling
│   │   │   └── infrastructure_tasks.py    # Infrastructure collection scheduling
│   │   └── schemas_*.py       # Pydantic request/response schemas
│   ├── tests/                 # Test suite
│   │   ├── conftest.py        # Pytest fixtures and configuration
│   │   ├── test_infrastructure_models.py  # Infrastructure model tests
│   │   └── test_alert_evaluator.py        # Alert evaluator tests
│   ├── scripts/               # Utility scripts
│   │   ├── validate_imports.py    # Import validation
│   │   ├── split_models.py        # Model refactoring script
│   │   └── generate_encryption_key.py  # Key generation
│   ├── data/                  # Data directory (SQLite removed, now PostgreSQL)
│   ├── Dockerfile             # Backend container definition
│   ├── requirements.txt       # Python dependencies
│   └── .dockerignore          # Docker build exclusions
├── frontend/                  # React/TypeScript frontend
│   ├── src/
│   │   ├── App.tsx            # Main application component
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   └── utils/             # Frontend utilities
│   ├── public/                # Static assets
│   ├── nginx/                 # Nginx configuration
│   ├── Dockerfile             # Frontend container definition
│   ├── package.json           # Node.js dependencies
│   └── vite.config.ts         # Vite build configuration
├── bd-store-staging/          # BD-Store reference codebase (for integration)
├── kc-booth-staging/          # KC-Booth reference codebase (integrated)
├── docker-compose.yml         # Production Docker Compose
├── docker-compose.dev.yml     # Development Docker Compose (hot-reload)
├── .env                       # Environment variables (not in git)
├── .env.example               # Environment variable template
├── .gitignore                 # Git exclusions
├── README.md                  # Project overview
├── START_HERE.md              # Getting started guide
├── CONTRIBUTING.md            # Development guidelines
├── DOCKER.md                  # Docker usage guide
├── PHASE-3-COMPLETE.md        # Phase 3 completion summary
├── PROJECT-STRUCTURE.md       # This file
├── SECURITY.md                # Security documentation
├── TESTING-GUIDE.md           # Testing documentation
└── README_ALEMBIC.md          # Database migration guide
```

## Key Patterns

### Models (Domain-Driven Design)
Models are organized by domain:
- **core.py**: Business entities (ServerProfile, Settings, Report, etc.)
- **monitoring.py**: Monitoring and alerting (ThresholdRule, Alert, etc.)
- **users.py**: Authentication and users
- **plugins.py**: Plugin system
- **credentials.py**: Secure credential storage
- **infrastructure.py**: Infrastructure resources (servers, storage, databases)
- **alert_rules.py**: Alert rule definitions

### Services (Business Logic Layer)
Services contain business logic and are organized by functionality:
- **infrastructure/**: 10 services for infrastructure monitoring
- **credentials/**: Credential encryption/decryption
- **notification_service.py**: Multi-channel notifications (SMTP, Telegram, etc.)

### Routers (API Layer)
Routers define FastAPI endpoints and handle HTTP requests:
- Each router corresponds to a major feature area
- **infrastructure.py** has 45+ endpoints for infrastructure monitoring

### Utils (Shared Utilities)
- **parsers.py**: Parse system command output (lsblk, smartctl, zpool, etc.)

### Schedulers (Background Tasks)
- **snapshot_tasks.py**: Scheduled snapshots
- **infrastructure_tasks.py**: 5-minute infrastructure collection cycle

## Database

- **Production**: PostgreSQL 16 (via Docker)
- **Development**: PostgreSQL 16 (via Docker)
- **Migrations**: Alembic (configured, see README_ALEMBIC.md)
- **ORM**: SQLAlchemy 2.0

## Configuration Files

### Docker
- `docker-compose.yml` - Production (port 80 frontend, 8000 backend, 5432 db)
- `docker-compose.dev.yml` - Development with hot-reload and mounted volumes

### Environment Variables
- `.env` - Local configuration (not committed)
- `.env.example` - Template with all required variables

### Dependencies
- `backend/requirements.txt` - Python packages
- `frontend/package.json` - Node.js packages

## Testing

- **Framework**: pytest with pytest-asyncio
- **Location**: `backend/tests/`
- **Fixtures**: `conftest.py`
- **Coverage**: 80%+ of critical paths
- **Run**: `pytest backend/tests/`

## Port Allocation

| Service | Production Port | Dev Port | Purpose |
|---------|----------------|----------|---------|
| Frontend | 80 | 80 | React UI |
| Backend | 8000 | 8000 | FastAPI |
| Frontend Dev | - | 5173 | Vite dev server |
| PostgreSQL | 5432 | 5432 | Database |

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Development Workflow

1. **Start Development Environment**
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

2. **Make Changes**
   - Backend: Auto-reload on file changes
   - Frontend: Vite hot-reload

3. **Run Tests**
   ```bash
   docker exec homelab-backend-dev pytest
   ```

4. **Database Migrations**
   ```bash
   docker exec homelab-backend-dev alembic revision --autogenerate -m "Description"
   docker exec homelab-backend-dev alembic upgrade head
   ```

5. **Access Logs**
   ```bash
   docker logs -f homelab-backend-dev
   docker logs -f homelab-frontend-dev
   ```

## Production Deployment

1. **Build Images**
   ```bash
   docker compose build
   ```

2. **Start Services**
   ```bash
   docker compose up -d
   ```

3. **Check Health**
   ```bash
   curl http://localhost:8000/
   curl http://localhost:8000/api/infrastructure/health/detailed
   ```

## Git Workflow

- **main**: Production-ready code
- **feature/kc-booth-integration**: KC-Booth integration (Phase 1-2)
- **feature/bd-store-integration**: BD-Store integration (Phase 3-3.5) ← Current
- **feature/uptainer-integration**: Uptainer integration (Phase 4) ← Next

## Key Dependencies

### Backend (Python)
- FastAPI - Web framework
- SQLAlchemy - ORM
- Alembic - Database migrations
- APScheduler - Task scheduling
- asyncssh - SSH connections
- pymysql / psycopg2 - Database drivers
- pytest - Testing framework

### Frontend (Node.js)
- React - UI framework
- TypeScript - Type safety
- Vite - Build tool
- TanStack Query - Data fetching
- Tailwind CSS - Styling

## Staging Directories

- **bd-store-staging/**: Reference implementation for Phase 3 (integrated)
- **kc-booth-staging/**: Reference implementation for Phase 1-2 (integrated)
- These directories contain original codebases for reference during integration

## Documentation Files

- **START_HERE.md**: Quick start guide
- **README.md**: Project overview
- **CONTRIBUTING.md**: Development guidelines
- **DOCKER.md**: Docker usage guide
- **SECURITY.md**: Security best practices
- **TESTING-GUIDE.md**: Testing documentation
- **README_ALEMBIC.md**: Migration instructions
- **PHASE-3-COMPLETE.md**: Phase 3 completion summary
- **PROJECT-STRUCTURE.md**: This file

## Next Steps

See `PHASE-3-COMPLETE.md` for current status and next actions (Phase 4: Uptainer integration).
