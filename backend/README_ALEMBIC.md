# Database Migrations with Alembic

## Setup

Alembic is configured in `requirements.txt`. To initialize:

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic init alembic
```

## Configuration

Edit `alembic/env.py` to import models:
```python
from app.core.database import Base
from app import models
target_metadata = Base.metadata
```

Edit `alembic.ini` with your database URL:
```ini
sqlalchemy.url = postgresql+psycopg2://user:pass@localhost:5432/dbname
```

## Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Review the generated migration file in alembic/versions/

# Apply migration
alembic upgrade head
```

## Commands

```bash
# Check current version
alembic current

# View history
alembic history

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision>
```

## Migration Script

A helper script is provided:

```bash
./scripts/migrate.sh
```

## Notes

- Always review auto-generated migrations before applying
- Test migrations on dev/staging before production
- Keep migrations in version control
- Never edit applied migrations
