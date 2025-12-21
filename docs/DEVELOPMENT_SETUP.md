# Unity Development Setup Guide

**Last Updated**: December 21, 2024  
**Target Audience**: Developers setting up Unity for local development

## Prerequisites

### Required
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+
- **Git**

### Optional
- **Node.js** 18+ (for frontend development)
- **PostgreSQL Client** (for database inspection)

## Quick Start (5 minutes)

### 1. Clone Repository

```bash
git clone <repository-url>
cd unity
```

### 2. Create Environment File

```bash
cp .env.example .env
# Edit .env if needed - defaults work for local development
```

### 3. Start with Docker Compose

**Development mode** (with hot-reload):
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**Or production mode**:
```bash
docker-compose up -d
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs

# Check logs
docker-compose logs -f backend
```

**Expected output**:
```json
{
  "status": "healthy",
  "scheduler": "running",
  "cache": "disconnected",
  "timestamp": "..."
}
```

## Development Without Docker

For local Python development without Docker:

### 1. Set up Python Environment

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set up Database

**Option A: Use SQLite** (simplest):
```bash
# In .env or export:
export DATABASE_URL="sqlite:///./data/homelab.db"

# Initialize database
python -m alembic upgrade head
```

**Option B: Use PostgreSQL**:
```bash
# Start PostgreSQL with Docker
docker run -d \
  --name unity-postgres \
  -e POSTGRES_DB=homelab_db \
  -e POSTGRES_USER=homelab_user \
  -e POSTGRES_PASSWORD=homelab_password \
  -p 5432:5432 \
  postgres:16-alpine

# In .env:
export DATABASE_URL="postgresql+psycopg2://homelab_user:homelab_password@localhost:5432/homelab_db"

# Initialize database
python -m alembic upgrade head
```

### 3. Run Development Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access API at: http://localhost:8000

## Project Structure

```
unity/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Application entry
│   │   ├── api/            # API endpoints
│   │   │   ├── plugins.py  # Plugin API
│   │   │   └── websocket.py # WebSocket streaming
│   │   ├── models/         # Database models
│   │   │   └── plugin.py   # Plugin models
│   │   ├── services/       # Business logic
│   │   │   ├── plugin_scheduler.py # Background scheduler
│   │   │   └── cache.py    # Redis caching
│   │   ├── plugins/        # Plugin implementations
│   │   │   └── builtin/    # Built-in plugins
│   │   └── core/           # Core utilities
│   ├── tests/              # Test suite
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── frontend/               # React frontend (planned)
├── docs/                   # Documentation
├── docker-compose.yml      # Production compose
├── docker-compose.dev.yml  # Development compose
└── .env.example           # Environment template
```

## Development Workflow

### Making Code Changes

**With Docker (hot-reload enabled)**:
1. Edit files in `backend/app/`
2. Changes automatically reload
3. Check logs: `docker-compose logs -f backend`

**Without Docker**:
1. Edit files in `backend/app/`
2. uvicorn with `--reload` automatically restarts
3. Check terminal for reload confirmation

### Running Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_plugin_api.py -v

# Run with markers
pytest -m api              # API tests only
pytest -m "not slow"       # Skip performance tests

# With coverage
pytest --cov=app --cov-report=html
```

### Database Migrations

**Create new migration**:
```bash
cd backend
alembic revision --autogenerate -m "Description of change"
```

**Apply migrations**:
```bash
alembic upgrade head
```

**Rollback migration**:
```bash
alembic downgrade -1
```

### Adding a New Plugin

1. Create plugin file in `backend/app/plugins/builtin/`
2. Inherit from `PluginBase`
3. Implement `collect_data()` and `health_check()` methods
4. Register plugin in database:

```python
from app.models.plugin import Plugin
from app.core.database import SessionLocal

db = SessionLocal()
plugin = Plugin(
    plugin_id="my_new_plugin",
    name="My New Plugin",
    enabled=True
)
db.add(plugin)
db.commit()
```

### Testing WebSocket

```bash
# Using websocat (install: cargo install websocat)
websocat ws://localhost:8000/ws/metrics

# Or using Python
python backend/test_api.py
```

## Common Development Tasks

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f db

# Last N lines
docker-compose logs --tail=100 backend
```

### Access Database

**With Docker**:
```bash
# PostgreSQL
docker exec -it homelab-db psql -U homelab_user -d homelab_db

# Common queries
\dt                          # List tables
SELECT * FROM plugins;       # View plugins
SELECT * FROM plugin_metrics LIMIT 10;  # View metrics
```

**SQLite**:
```bash
sqlite3 backend/data/homelab.db
.tables
SELECT * FROM plugins;
```

### Reset Database

```bash
# Stop containers
docker-compose down

# Remove volumes
docker volume rm unity_homelab_db_data

# Start fresh
docker-compose up -d
```

### Run Single Plugin Manually

```bash
cd backend
python -c "
from app.plugins.builtin.system_info import SystemInfoPlugin
import asyncio

async def test():
    plugin = SystemInfoPlugin()
    data = await plugin.collect_data()
    print(data)

asyncio.run(test())
"
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose
ports:
  - "8001:8000"  # Host:Container
```

### Database Connection Error

```bash
# Check database is running
docker ps | grep homelab-db

# Check connection string
echo $DATABASE_URL

# Wait for database to initialize
docker-compose logs db | grep "ready to accept connections"
```

### Module Import Errors

```bash
# Reinstall dependencies
cd backend
pip install -r requirements.txt --upgrade

# Or rebuild Docker image
docker-compose build backend
```

### Hot-reload Not Working

```bash
# Ensure using dev compose file
docker-compose -f docker-compose.dev.yml up

# Check volume mounts
docker inspect homelab-backend-dev | grep Mounts -A 10

# Restart container
docker-compose restart backend
```

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Pylance
- Docker
- REST Client

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

1. Open `backend/` as project root
2. Configure interpreter: `.venv/bin/python`
3. Mark `app/` as Sources Root
4. Configure pytest as test runner
5. Add Docker Compose run configuration

## Performance Tips

### Development Mode
- Use SQLite for faster startup
- Disable unnecessary plugins
- Use `--reload-delay` with uvicorn for slower machines

### Testing
- Use `pytest -n auto` for parallel test execution (requires pytest-xdist)
- Skip slow tests: `pytest -m "not slow"`

## Next Steps

- **API Development**: See `docs/RUN4_API_LAYER.md`
- **Testing**: See `docs/RUN5_TESTING.md`
- **Deployment**: See `DEPLOYMENT_ARCHITECTURE.md`
- **Production**: See `PRODUCTION_DEPLOYMENT.md`

---

**Questions?** Check troubleshooting section or create an issue.
