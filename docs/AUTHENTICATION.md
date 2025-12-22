# Unity Authentication System

**Version**: 1.0  
**Status**: Production Ready (Phase 2A Complete)

## Overview

Unity now includes a comprehensive authentication and authorization system with:

- **Username/Password Authentication** with JWT tokens
- **API Key Authentication** for programmatic access
- **Role-Based Access Control (RBAC)** with three roles
- **Session Management** via Redis
- **Comprehensive Audit Logging** for security tracking

## Quick Start

### 1. Run Database Migrations

```bash
cd backend
source .venv_new/bin/activate
PYTHONPATH=/home/matthew/projects/HI/unity/backend:$PYTHONPATH alembic upgrade head
```

This creates the auth tables: `users`, `api_keys`, `audit_logs`

### 2. Create Admin User

After running migrations, you can create an admin user via the API:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@unity.local",
    "password": "YourSecurePassword123",
    "full_name": "System Administrator"
  }'
```

**Production Note**: Disable `/auth/register` or make it admin-only after creating your first admin.

### 3. Login and Get Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "YourSecurePassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid-here",
    "username": "admin",
    "email": "admin@unity.local",
    "role": "viewer",
    ...
  }
}
```

### 4. Use the Token

Include the token in the `Authorization` header:

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Authentication Methods

### 1. JWT Tokens (Recommended for UI)

**Login**: `POST /auth/login`
```json
{
  "username": "admin",
  "password": "password"
}
```

**Usage**: Add to Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Expiry**: 30 minutes (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)

### 2. API Keys (Recommended for Scripts/Automation)

**Create Key**: `POST /api-keys`
```json
{
  "name": "My Automation Script",
  "scopes": ["read", "write"],
  "expires_days": 90
}
```

Response includes plaintext key (only shown once!):
```json
{
  "api_key": "unity_abc123...",
  "key_info": { ... }
}
```

**Usage**: Three methods supported:

1. Header (recommended):
```
X-API-Key: unity_abc123...
```

2. Query parameter:
```
?api_key=unity_abc123...
```

3. Bearer token:
```
Authorization: Bearer unity_abc123...
```

### 3. Session Cookies (Future)

Redis-based sessions for web applications. Currently JWT is used; sessions are planned for Phase 2B.

## User Roles & Permissions

### Role Hierarchy

```
admin > editor > viewer
```

Roles are hierarchical: admins can do everything editors can, editors can do everything viewers can.

### Role Permissions

| Role | Permissions | Use Case |
|------|-------------|----------|
| **viewer** | Read-only access to all data | Monitoring dashboards, read-only users |
| **editor** | Read + Create/Update data | Developers, operators who manage infrastructure |
| **admin** | Full access including user management | System administrators |

### Endpoints by Role

**Public (No Auth)**:
- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `POST /auth/register` (disable in production!)

**Viewer** (Any authenticated user):
- `GET /auth/me`
- `GET /plugins/*`
- `GET /metrics/*`
- `GET /system/dashboard-stats`

**Editor** (Modify operations):
- `POST/PUT/PATCH` for plugins, containers, infrastructure
- `POST /api-keys` (own keys)
- `PUT /auth/me`

**Admin** (Full control):
- `GET/POST/PUT/DELETE /users/*`
- `GET /audit-logs/*`
- `PUT /users/{id}/role`
- `DELETE *` (delete operations)

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | Public* |
| POST | `/auth/login` | Login with credentials | Public |
| POST | `/auth/logout` | Logout | Yes |
| GET | `/auth/me` | Get current user info | Yes |
| PUT | `/auth/me` | Update profile | Yes |
| PUT | `/auth/me/password` | Change password | Yes |

\* Should be restricted in production

### API Keys

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api-keys` | Create new API key | Yes |
| GET | `/api-keys` | List user's API keys | Yes |
| GET | `/api-keys/{id}` | Get key details | Yes |
| PUT | `/api-keys/{id}` | Update key name/scopes | Yes |
| DELETE | `/api-keys/{id}` | Revoke API key | Yes |

### User Management (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Get user details |
| PUT | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Deactivate user |
| PUT | `/users/{id}/role` | Change user role |
| PUT | `/users/{id}/password` | Reset user password |
| GET | `/users/{id}/audit-logs` | Get user's audit logs |

### Audit Logs (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/audit-logs` | List all audit logs |
| GET | `/audit-logs/{id}` | Get specific log |
| GET | `/audit-logs/actions/list` | List action types |
| GET | `/audit-logs/stats/summary` | Get audit statistics |

## Configuration

### Environment Variables

```bash
# JWT Settings
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis Settings
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# Session Settings
SESSION_EXPIRY_HOURS=24
SESSION_COOKIE_NAME=unity_session
SESSION_COOKIE_SECURE=false  # Set true in production with HTTPS

# API Key Settings
API_KEY_EXPIRY_DAYS=90
API_KEY_PREFIX=unity_

# Password Policy
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGITS=true
PASSWORD_REQUIRE_SPECIAL=false
BCRYPT_ROUNDS=12

# Rate Limiting (Future)
MAX_LOGIN_ATTEMPTS=5
LOGIN_ATTEMPT_WINDOW_MINUTES=15
LOCKOUT_DURATION_MINUTES=30
```

### Docker Compose

Redis is now included in `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: homelab-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - homelab_redis_data:/data
    ports:
      - "6379:6379"
```

## Security Best Practices

### In Production

1. **Change default secrets**:
   - Set a strong `JWT_SECRET_KEY` (32+ random characters)
   - Set a strong database password
   - Enable `SESSION_COOKIE_SECURE=true` with HTTPS

2. **Disable public registration**:
   - Remove or protect `/auth/register` endpoint
   - Create users via admin panel only

3. **Use HTTPS**:
   - Enable TLS/SSL for all API traffic
   - Set `SESSION_COOKIE_SECURE=true`

4. **Rotate API keys**:
   - Set reasonable expiry times (30-90 days)
   - Rotate keys regularly
   - Revoke unused keys

5. **Monitor audit logs**:
   - Review failed login attempts
   - Check for suspicious activity
   - Set up alerts for admin actions

6. **Use least privilege**:
   - Default new users to `viewer` role
   - Only grant `editor`/`admin` when needed
   - Use API keys with limited scopes

## Troubleshooting

### "Not authenticated" error

Check:
1. Token is included in header: `Authorization: Bearer TOKEN`
2. Token hasn't expired (30 min default)
3. User account is active

### "Insufficient permissions" error

Check:
1. User's role in database
2. Endpoint required role
3. Role hierarchy (admin > editor > viewer)

### Redis connection failed

Check:
1. Redis container is running: `docker ps | grep redis`
2. Redis URL is correct in environment
3. Redis is accessible: `redis-cli ping`

### Can't create admin user

If registration is disabled:
1. Use SQL to create user directly
2. Or temporarily enable registration
3. Or use existing admin to create new users

## Development

### Adding Auth to New Endpoints

```python
from app.core.dependencies import require_viewer, require_editor, require_admin
from app.models.users import User

# Viewer level (read-only)
@router.get("/data")
async def get_data(
    current_user: User = Depends(require_viewer()),
    db: Session = Depends(get_db)
):
    return {"data": "..."}

# Editor level (modifications)
@router.post("/data")
async def create_data(
    data: DataModel,
    current_user: User = Depends(require_editor()),
    db: Session = Depends(get_db)
):
    return {"created": True}

# Admin only
@router.delete("/data/{id}")
async def delete_data(
    id: str,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    return {"deleted": True}
```

### Testing Auth Locally

```bash
# Create test user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"test1234"}'

# Login
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test1234"}' \
  | jq -r '.access_token')

# Use token
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## Next Steps: Phase 2B (OAuth2/SSO)

Future enhancements planned:
- OAuth2 providers (GitHub, Google, GitLab)
- SAML support
- 2FA/TOTP
- LDAP/Active Directory integration
- Advanced session management
- Rate limiting & brute force protection

See `MARKET_RESEARCH_TODO.md` for complete roadmap.

---

**Questions or issues?** Check the audit logs or contact your system administrator.
