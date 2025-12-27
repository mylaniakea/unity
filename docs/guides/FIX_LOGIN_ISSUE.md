# Fix Login Issue - Database Schema Mismatch

## Problem

The database `users` table has an **integer ID** but the User model expects a **UUID**. This causes login to fail with:
```
cannot cast type integer to uuid
```

## Solution

You have two options:

### Option 1: Quick Fix - Use Register Endpoint

```bash
# Register a new admin user (will have correct UUID)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "admin123",
    "full_name": "Admin User"
  }'

# Then update role to admin via database
docker compose exec db psql -U homelab_user -d homelab_db -c \
  "UPDATE users SET role = 'admin', is_superuser = true WHERE username = 'admin';"
```

### Option 2: Fix Database Schema (Recommended)

Convert the users table to use UUID:

```bash
docker compose exec db psql -U homelab_user -d homelab_db << EOF
-- Add new UUID column
ALTER TABLE users ADD COLUMN new_id UUID DEFAULT gen_random_uuid();

-- Copy data
UPDATE users SET new_id = gen_random_uuid();

-- Drop old constraints
ALTER TABLE users DROP CONSTRAINT users_pkey;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;

-- Rename columns
ALTER TABLE users DROP COLUMN id;
ALTER TABLE users RENAME COLUMN new_id TO id;
ALTER TABLE users ADD PRIMARY KEY (id);

-- Recreate constraints
ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username);
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
EOF
```

### Option 3: Temporary Workaround

The admin user exists in the database with integer ID. You can:

1. **Use the API with raw SQL** (bypassing ORM)
2. **Wait for proper migration** to fix the schema
3. **Use register endpoint** to create a new user with UUID

## Current Status

✅ Admin user exists in database:
- Username: `admin`
- Password: `admin123` (verified)
- Role: `admin`
- Active: `true`

❌ Login fails due to ID type mismatch (integer vs UUID)

## Quick Test

Test password verification:
```bash
docker compose exec backend python3 -c "
from app.core.database import engine
from app.services.auth.user_service import verify_password
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT username, hashed_password FROM users WHERE username = :username'), {'username': 'admin'})
    row = result.fetchone()
    if row and verify_password('admin123', row[1]):
        print('✅ Password works!')
    else:
        print('❌ Password failed')
"
```

## Next Steps

1. Run proper Alembic migrations to fix schema
2. Or use register endpoint to create new admin with UUID
3. Or manually fix the database schema (Option 2 above)

