# Backend Scripts

## Active Utilities

Scripts in the backend root directory are active utilities:

- `create_plugin_tables.py` - Creates plugin-related database tables
- `generate_encryption_key.py` - Generates encryption keys for secure storage
- `verify_ai_config.py` - Verifies AI provider configuration

## Archived Scripts

### `migrations_archive/`

Contains one-time migration scripts that were used during development but are no longer needed:

- `migrate_sqlite_to_postgres.py` - Original SQLite to PostgreSQL migration
- `migrate_add_*.py` - Various schema migration scripts (now handled by Alembic)

**Note:** All schema changes should now be handled through Alembic migrations (`backend/alembic/versions/`). These scripts are preserved for historical reference only.

## Usage

For active utilities, run from the project root:

```bash
# Generate encryption key
python backend/generate_encryption_key.py

# Verify AI configuration
python backend/verify_ai_config.py

# Create plugin tables (if needed)
python backend/create_plugin_tables.py
```

For database migrations, use Alembic:

```bash
cd backend
alembic upgrade head
```
