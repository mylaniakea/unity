# API Authentication Implementation Summary

## Overview
Implemented API key-based authentication for kc-booth to secure all endpoints and prevent unauthorized access to sensitive resources.

## Changes Made

### 1. Dependencies Added
- `passlib[bcrypt]` - Password hashing
- `python-jose[cryptography]` - Token handling utilities
- `python-multipart` - Form data support

### 2. New Database Models (`src/auth_models.py`)
- **User table**:
  - id, username (unique), hashed_password, is_active, created_at
  - Passwords hashed with bcrypt
- **APIKey table**:
  - id, key_hash (hashed API key), name, user_id (FK), is_active, created_at, last_used_at
  - API keys hashed for secure storage

### 3. Authentication Schemas (`src/auth_schemas.py`)
- `UserCreate` - Create new users (requires username, password)
- `User` - User response (password excluded)
- `APIKeyCreate` - Create API keys with description
- `APIKey` - API key response (actual key hash excluded)
- `APIKeyWithKey` - Shown only once at creation with plaintext key
- `LoginRequest` - Username/password login
- `Token` - API response format

### 4. Authentication Utilities (`src/auth.py`)
- **Password hashing**: `get_password_hash()`, `verify_password()` using bcrypt
- **API key generation**: `generate_api_key()` - 64-char hex (cryptographically secure)
- **API key hashing**: `get_api_key_hash()`, `verify_api_key()`
- **User authentication**: `authenticate_user()` - validates username/password
- **FastAPI dependency**: `get_current_user()` - validates API key from X-API-Key header
  - Supports `DISABLE_AUTH=true` for development (bypasses auth)
  - Returns 401 if key missing or invalid
  - Updates last_used_at timestamp on successful auth

### 5. CRUD Operations (`src/auth_crud.py`)
- **Users**: `create_user()`, `get_user()`, `get_user_by_username()`, `get_users()`
- **API Keys**: 
  - `create_api_key()` - generates and hashes key, returns both model and plaintext
  - `get_api_key()`, `get_all_api_keys()`, `get_user_api_keys()`
  - `update_api_key_last_used()` - tracks usage
  - `deactivate_api_key()` - soft delete

### 6. API Endpoints Added (`src/main.py`)

#### Authentication Endpoints
- `POST /auth/users/` - Create user (requires auth)
- `POST /auth/login` - Login with username/password, returns API key
- `POST /auth/api-keys/` - Create new API key (requires auth)
- `GET /auth/api-keys/` - List user's API keys (requires auth)
- `DELETE /auth/api-keys/{key_id}` - Revoke API key (requires auth)

#### Protected Endpoints
All existing endpoints now require authentication:
- SSH Keys: POST, GET (list/single)
- Servers: POST, GET (list/single)
- Certificates: GET (list)
- CA: GET fingerprint, POST issue certificate

### 7. Configuration Updates (`src/config.py`)
- Added `disable_auth` boolean setting (default: False)
- When `DISABLE_AUTH=true`, authentication is bypassed (for development)

### 8. Admin User Creation Script (`create_admin_user.py`)
- Interactive script to create initial admin user
- Validates configuration
- Creates database tables if needed
- Prompts for username and password with validation
- Optionally creates initial API key
- Shows plaintext API key once (must be saved)

## Usage

### Initial Setup

1. **Create admin user**:
   ```bash
   export ENCRYPTION_KEY="your-key"
   export DATABASE_URL="postgresql://..."
   export STEP_PROVISIONER_PASSWORD="..."
   python3 create_admin_user.py
   ```

2. **Save the API key** shown after creation

### API Usage

#### Login to get API key
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'
```

#### Use API key in requests
```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8001/ssh-keys/
```

#### Create additional API keys
```bash
curl -X POST http://localhost:8001/auth/api-keys/ \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production Key"}'
```

#### List your API keys
```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8001/auth/api-keys/
```

#### Revoke an API key
```bash
curl -X DELETE http://localhost:8001/auth/api-keys/1 \
  -H "X-API-Key: your-api-key-here"
```

### Development Mode

For local development, disable authentication:
```bash
export DISABLE_AUTH=true
docker compose up
```

All endpoints will be accessible without API keys.

## Security Features

1. **Password Security**:
   - Bcrypt hashing with automatic salt generation
   - Minimum 8 characters required
   - Never stored or returned in plaintext

2. **API Key Security**:
   - 64-character hexadecimal keys (256 bits of entropy)
   - Generated with `secrets.token_hex()` (cryptographically secure)
   - Hashed before storage (bcrypt)
   - Only shown once at creation
   - Can be revoked (soft delete)

3. **Access Control**:
   - Users can only see/revoke their own API keys
   - All sensitive endpoints require authentication
   - 401 responses for missing/invalid keys
   - 403 responses for unauthorized actions

4. **Audit Trail**:
   - `created_at` timestamp for users and keys
   - `last_used_at` updated on each authenticated request
   - Ability to track key usage patterns

5. **Development Safety**:
   - `DISABLE_AUTH` flag for local dev only
   - Clear warnings in startup messages
   - Explicit opt-in required

## Error Responses

- **401 Unauthorized**: Missing or invalid API key
  ```json
  {"detail": "API key required. Provide X-API-Key header."}
  ```

- **401 Unauthorized**: Invalid credentials
  ```json
  {"detail": "Incorrect username or password"}
  ```

- **403 Forbidden**: Not authorized for action
  ```json
  {"detail": "Not authorized to revoke this API key"}
  ```

- **400 Bad Request**: Duplicate username
  ```json
  {"detail": "Username already exists"}
  ```

## Future Enhancements

- Role-based access control (admin, read-only, etc.)
- API key scopes/permissions
- JWT tokens for web UI sessions
- OAuth2 integration
- API key expiration dates
- Rate limiting per API key
- Detailed audit logs
