# Run 2: Database Schema & Migration System

**Status**: ✅ Complete  
**Date**: December 18, 2024

## What We Built

### SQLAlchemy Models
Created comprehensive database models in `backend/app/models/plugin.py`:

- **Plugin**: Plugin registration and configuration
- **PluginMetric**: Time-series metrics storage
- **PluginStatus**: Current plugin health tracking
- **Alert**: Alert configuration
- **AlertHistory**: Alert trigger history

**Features**:
- PostgreSQL JSONB for flexible plugin data
- Proper foreign key relationships
- Optimized indexes for common queries
- UUID primary keys
- Timestamps with timezone support

### Alembic Migration System
Set up complete migration infrastructure:

- `alembic.ini` - Configuration
- `alembic/env.py` - Environment setup with auto-import
- `alembic/script.py.mako` - Migration template
- `alembic/versions/` - Migration history

**Features**:
- Auto-imports all models
- Uses settings from config
- Supports offline and online migrations

### TimescaleDB Integration
Created `backend/app/core/timescaledb.py` with full TimescaleDB support:

**Capabilities**:
- Auto-detect TimescaleDB extension
- Enable extension if available
- Create hypertables for time-series tables
- Set up compression policies
- Configure data retention
- Graceful fallback to standard PostgreSQL

**Hypertables**:
- `plugin_metrics` - 7-day chunks, 30-day retention, compression after 7 days
- `alert_history` - 7-day chunks, 90-day retention

### Database Initialization Script
Single-command setup: `backend/scripts/init_database.py`

```bash
python3 backend/scripts/init_database.py
```

**What it does**:
1. Creates all tables
2. Detects database type (PostgreSQL/MySQL/SQLite)
3. Enables TimescaleDB if available
4. Creates hypertables
5. Sets up compression and retention
6. Reports status

## Database Schema

### plugins
```sql
id              UUID PRIMARY KEY
plugin_id       VARCHAR(100) UNIQUE
name            VARCHAR(200)
version         VARCHAR(50)
description     TEXT
category        VARCHAR(50)
enabled         BOOLEAN
config          JSONB
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

### plugin_metrics (Hypertable)
```sql
time            TIMESTAMPTZ PRIMARY KEY
plugin_id       VARCHAR(100) PRIMARY KEY
metric_name     VARCHAR(200) PRIMARY KEY
value           JSONB
tags            JSONB

-- Indexes
idx_metrics_plugin_time (plugin_id, time)
idx_metrics_name (metric_name)
idx_metrics_tags (tags) USING GIN
```

### plugin_status
```sql
plugin_id           VARCHAR(100) PRIMARY KEY
last_run            TIMESTAMPTZ
last_success        TIMESTAMPTZ
last_error          TEXT
error_count         INTEGER
consecutive_errors  INTEGER
health_status       VARCHAR(20)
updated_at          TIMESTAMPTZ
```

### alerts
```sql
id              UUID PRIMARY KEY
plugin_id       VARCHAR(100)
name            VARCHAR(200)
description     TEXT
condition       JSONB
severity        VARCHAR(20)
enabled         BOOLEAN
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

### alert_history (Hypertable)
```sql
time            TIMESTAMPTZ PRIMARY KEY
alert_id        UUID PRIMARY KEY
triggered       BOOLEAN
value           JSONB
message         TEXT

-- Indexes
idx_alert_history_time (alert_id, time)
```

## Usage

### Initialize Database
```bash
# SQLite (dev)
export DATABASE_URL="sqlite:///./data/unity.db"
python3 backend/scripts/init_database.py

# PostgreSQL
export DATABASE_URL="postgresql://user:pass@localhost/unity"
python3 backend/scripts/init_database.py

# PostgreSQL with TimescaleDB
# 1. Install TimescaleDB extension on your PostgreSQL instance
# 2. Run init script (it will auto-detect and configure)
python3 backend/scripts/init_database.py
```

### Create Migration
```bash
cd backend
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

### Verify Setup
```python
from app.core.database import SessionLocal
from app.models import Plugin

session = SessionLocal()
plugins = session.query(Plugin).all()
print(f"Found {len(plugins)} plugins")
```

## TimescaleDB Benefits

When using TimescaleDB:
- **30-50% faster** inserts for metrics
- **10x faster** time-range queries
- **Automatic compression** saves 90%+ storage
- **Automatic retention** manages old data
- **No query changes** - standard SQL works

## Database Compatibility

| Feature | PostgreSQL + TimescaleDB | PostgreSQL | MySQL | SQLite |
|---------|-------------------------|------------|-------|--------|
| Core Tables | ✅ | ✅ | ✅ | ✅ |
| Hypertables | ✅ | ❌ | ❌ | ❌ |
| Compression | ✅ | ❌ | ❌ | ❌ |
| Auto Retention | ✅ | Manual | Manual | Manual |
| JSONB | ✅ | ✅ | JSON | TEXT |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

## Next Steps (Run 3)

Ready to implement:
1. PluginScheduler for collection orchestration
2. DataProcessor for validation and transformation  
3. Batch insert optimization
4. Redis/Valkey cache integration
5. Error handling and retry logic

---

*Database foundation by Matthew and Warp AI*  
*Co-Authored-By: Warp <agent@warp.dev>*
