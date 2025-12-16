# Unity Project Structure

**Version**: 2.0 (Post-Refactoring)  
**Last Updated**: December 16, 2025

## Overview

This document provides a complete reference for the Unity codebase structure after the comprehensive refactoring completed in December 2025.

## Directory Tree

```
unity/
├── backend/                    # FastAPI backend application
│   ├── app/                   # Main application code
│   │   ├── core/              # Core configuration and database
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Centralized settings (30+ options)
│   │   │   └── database.py    # SQLAlchemy setup
│   │   │
│   │   ├── models/            # SQLAlchemy ORM models (9 modules)
│   │   │   ├── __init__.py
│   │   │   ├── core.py        # Core entities
│   │   │   ├── users.py
│   │   │   ├── monitoring.py
│   │   │   ├── infrastructure.py
│   │   │   ├── containers.py
│   │   │   ├── credentials.py
│   │   │   ├── plugins.py
│   │   │   ├── alert_rules.py
│   │   │   └── error_tracking.py
│   │   │
│   │   ├── schemas/           # Pydantic validation schemas (9 modules)
│   │   │   ├── __init__.py
│   │   │   ├── core.py
│   │   │   ├── users.py
│   │   │   ├── alerts.py
│   │   │   ├── credentials.py
│   │   │   ├── knowledge.py
│   │   │   ├── notifications.py
│   │   │   ├── plugins.py
│   │   │   └── reports.py
│   │   │
│   │   ├── services/          # Business logic layer (7 modules)
│   │   │   ├── auth/
│   │   │   │   ├── __init__.py
│   │   │   │   └── auth_service.py
│   │   │   ├── monitoring/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── threshold_monitor.py
│   │   │   │   ├── alert_channels.py
│   │   │   │   ├── notification_service.py
│   │   │   │   └── push_notifications.py
│   │   │   ├── plugins/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── plugin_manager.py
│   │   │   │   ├── plugin_registry.py
│   │   │   │   └── plugin_security.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── snapshot_service.py
│   │   │   │   ├── system_info.py
│   │   │   │   ├── report_generation.py
│   │   │   │   ├── ssh.py
│   │   │   │   └── encryption.py
│   │   │   ├── ai/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ai.py
│   │   │   │   └── ai_provider.py
│   │   │   ├── containers/    # Container management services
│   │   │   ├── credentials/   # Credential management services
│   │   │   └── infrastructure/ # Infrastructure monitoring services
│   │   │
│   │   ├── routers/           # FastAPI route definitions
│   │   │   ├── plugins/       # Plugin API endpoints (4 routers)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── legacy.py  # v1 API
│   │   │   │   ├── v2.py      # v2 API
│   │   │   │   ├── v2_secure.py # Production v2 API
│   │   │   │   └── keys.py    # API key management
│   │   │   ├── monitoring/    # Monitoring endpoints (3 routers)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alerts.py
│   │   │   │   ├── thresholds.py
│   │   │   │   └── push.py
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── users.py
│   │   │   ├── profiles.py
│   │   │   ├── system.py
│   │   │   ├── ai.py
│   │   │   ├── settings.py
│   │   │   ├── reports.py
│   │   │   ├── knowledge.py
│   │   │   ├── terminal.py
│   │   │   ├── containers.py
│   │   │   ├── credentials.py
│   │   │   └── infrastructure.py
│   │   │
│   │   ├── utils/             # Utility functions
│   │   │   ├── __init__.py
│   │   │   └── parsers.py     # System command parsers
│   │   │
│   │   ├── schedulers/        # Background job schedulers
│   │   │   ├── container_tasks.py
│   │   │   ├── credential_tasks.py
│   │   │   └── infrastructure_tasks.py
│   │   │
│   │   ├── plugins/           # Plugin system
│   │   │   ├── base.py
│   │   │   ├── hub_client.py
│   │   │   ├── loader.py
│   │   │   └── builtin/       # Built-in plugins
│   │   │
│   │   └── main.py            # FastAPI application entry point
│   │
│   ├── tests/                 # Test suite (48 tests)
│   │   ├── conftest.py        # Test fixtures
│   │   ├── pytest.ini         # Pytest configuration
│   │   ├── README.md          # Testing documentation
│   │   ├── test_core_config.py
│   │   ├── test_api_endpoints.py
│   │   ├── test_alert_evaluator.py
│   │   ├── test_infrastructure_models.py
│   │   └── test_containers/
│   │       ├── test_models.py
│   │       └── test_api.py
│   │
│   ├── alembic/               # Database migrations
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile
│   └── .dockerignore
│
├── frontend/                  # React frontend (Vue in transition)
│   ├── public/
│   ├── src/
│   └── package.json
│
├── wiki/                      # GitHub wiki content
│   ├── Home.md
│   ├── API-Documentation.md
│   └── Setup-Guide.md
│
├── docs/                      # Additional documentation
│   └── [various docs]
│
├── scripts/                   # Utility scripts
│   └── push-wiki.sh
│
├── docker-compose.yml         # Docker orchestration
├── .gitignore
├── .env.example              # Environment template
│
└── Documentation Files
    ├── README.md              # Main project README
    ├── ARCHITECTURE.md        # Architecture documentation (NEW)
    ├── PROJECT-STRUCTURE.md   # This file (NEW)
    ├── MIGRATION_GUIDE.md     # Migration guide (NEW)
    ├── CONTRIBUTING.md        # Development guidelines
    ├── REFACTORING_PROGRESS.md # Refactoring history
    ├── SESSION_SUMMARY.md     # Latest session summary
    ├── ROADMAP.md             # Development roadmap
    └── PHASE7_VALIDATION.md   # Validation report
```

## Module Details

### Core Module (`app/core/`)

**Purpose**: Fundamental application configuration

| File | Purpose | Key Features |
|------|---------|--------------|
| `config.py` | Settings management | 30+ config options, env var support, type-safe |
| `database.py` | Database setup | SQLAlchemy engine, session factory, Base model |

### Models Module (`app/models/`)

**Purpose**: Database schema definitions

| File | Entities | Purpose |
|------|----------|---------|
| `core.py` | ServerProfile, KnowledgeBase | Core entities |
| `users.py` | User | Authentication |
| `monitoring.py` | Alert, AlertRule, ThresholdRule | Monitoring system |
| `infrastructure.py` | MonitoredServer, StorageDevice, NetworkInterface | Infrastructure tracking |
| `containers.py` | Container, ContainerImage | Container management |
| `credentials.py` | Credential, Certificate | Secure storage |
| `plugins.py` | Plugin, PluginMetric, PluginAPIKey | Plugin system |
| `alert_rules.py` | AlertRule, AlertCondition | Alert configuration |
| `error_tracking.py` | ErrorLog | Error tracking |

### Schemas Module (`app/schemas/`)

**Purpose**: Request/response validation

Mirrors model organization for consistency. Each schema module contains:
- Request schemas (Create, Update)
- Response schemas
- List/pagination schemas

### Services Module (`app/services/`)

**Purpose**: Business logic implementation

| Module | Files | Purpose |
|--------|-------|---------|
| `auth/` | auth_service.py | JWT, password hashing |
| `monitoring/` | 4 files | Alerts, notifications, thresholds |
| `plugins/` | 3 files | Plugin lifecycle, security |
| `core/` | 5 files | Snapshots, reports, SSH, encryption |
| `ai/` | 2 files | AI integration |
| `containers/` | Multiple | Container management |
| `credentials/` | Multiple | Credential management |
| `infrastructure/` | Multiple | Infrastructure monitoring |

### Routers Module (`app/routers/`)

**Purpose**: API endpoint definitions

**Organized Routers**:
- `plugins/` - 4 plugin API versions
- `monitoring/` - 3 monitoring endpoints

**Flat Routers**: 12 single-purpose routers (auth, users, profiles, etc.)

### Utils Module (`app/utils/`)

**Purpose**: Reusable utilities

Currently contains parsers for:
- lsblk (block devices)
- smartctl (SMART data)
- nvme (NVMe metrics)
- zpool (ZFS pools)
- lvm (LVM volumes)

### Tests Module (`backend/tests/`)

**Purpose**: Automated testing

- 48 tests total
- Comprehensive fixtures in conftest.py
- Test markers for organization (unit, api, smoke, etc.)
- Full testing documentation in README.md

## Import Patterns

### Correct Import Examples

```python
# Core
from app.core.config import settings
from app.core.database import get_db, Base

# Models
from app import models
from app.models import User, Plugin

# Schemas
from app.schemas.users import UserCreate, UserResponse
from app.schemas.plugins import PluginInfo

# Services
from app.services.auth.auth_service import create_access_token
from app.services.plugins.plugin_manager import PluginManager

# Routers (in main.py)
from app.routers import auth, users, profiles
from app.routers.plugins import legacy, v2_secure, keys
from app.routers.monitoring import alerts, thresholds, push

# Utils
from app.utils import LsblkParser, SmartctlParser
```

## File Naming Conventions

- **Modules**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_*.py` or `*_test.py`

## Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `pytest.ini` | Pytest configuration |
| `.env.example` | Environment variable template |
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | Backend container definition |
| `alembic.ini` | Database migration config |

## Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview |
| `ARCHITECTURE.md` | High-level architecture |
| `PROJECT-STRUCTURE.md` | This file - structure reference |
| `MIGRATION_GUIDE.md` | Migration from old structure |
| `CONTRIBUTING.md` | Development guidelines |
| `REFACTORING_PROGRESS.md` | Refactoring history |
| `ROADMAP.md` | Development roadmap |
| `backend/tests/README.md` | Testing guide |

## Quick Navigation

### Adding a New Feature

1. **Model**: `app/models/{domain}.py`
2. **Schema**: `app/schemas/{domain}.py`
3. **Service**: `app/services/{domain}/{service}.py`
4. **Router**: `app/routers/{domain}.py`
5. **Tests**: `backend/tests/test_{domain}.py`

### Finding Code

- **Configuration**: `app/core/config.py`
- **Database**: `app/core/database.py`
- **Auth**: `app/services/auth/` and `app/routers/auth.py`
- **Plugins**: `app/services/plugins/` and `app/routers/plugins/`
- **Monitoring**: `app/services/monitoring/` and `app/routers/monitoring/`
- **Tests**: `backend/tests/`

## Metrics

- **Total Modules**: 20+ organized modules
- **Total Files**: 100+ Python files
- **Lines of Code**: ~20,000+ LOC
- **Test Coverage**: 48 tests
- **Breaking Changes**: 0 (maintained compatibility)

## See Also

- `ARCHITECTURE.md` - Architectural patterns and decisions
- `MIGRATION_GUIDE.md` - Migrating from old structure
- `CONTRIBUTING.md` - Development workflow
- `backend/tests/README.md` - Testing documentation
