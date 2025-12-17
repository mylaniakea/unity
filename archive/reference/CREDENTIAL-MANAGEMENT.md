# Credential Management System

Integrated from KC-Booth, Unity's credential management system provides secure storage and management of SSH keys, certificates, and server credentials.

## Features

- **SSH Key Management**: Generate, store, and manage SSH key pairs with encryption
- **Certificate Management**: Store SSL/TLS certificates with auto-renewal support
- **Server Credentials**: Link credentials to Unity's ServerProfile system
- **Encryption at Rest**: Fernet encryption for all sensitive data
- **Comprehensive Audit Logging**: Track all credential operations with IP and user agent
- **REST API**: 27 secure endpoints for credential operations

## Architecture

### Components

1. **Database Models** (`backend/app/models.py`)
   - `SSHKey`: SSH key pairs with metadata
   - `Certificate`: SSL/TLS certificates with expiry tracking
   - `ServerCredential`: Server login credentials linked to ServerProfile
   - `CredentialAuditLog`: Complete audit trail

2. **Services** (`backend/app/services/credentials/`)
   - `EncryptionService`: Fernet encryption/decryption
   - `SSHKeyService`: SSH key CRUD operations
   - `CertificateService`: Certificate CRUD and validation
   - `ServerCredentialService`: Credential CRUD
   - `CredentialAuditService`: Audit logging

3. **API Router** (`backend/app/routers/credentials.py`)
   - 27 REST API endpoints
   - JWT authentication required
   - Separate endpoints for accessing secrets

4. **Pydantic Schemas** (`backend/app/schemas_credentials.py`)
   - Input validation
   - Response models with sensitive data exclusion

## Setup

### 1. Generate Encryption Key

```bash
cd /home/matthew/projects/HI/unity/backend
python3 generate_encryption_key.py
```

Copy the generated key to your `.env` file:

```bash
ENCRYPTION_KEY=<generated-key>
```

### 2. Database Migration

The credential models are already integrated into Unity's database schema. Run migrations if needed:

```bash
cd /home/matthew/projects/HI/unity/backend
# Add migration if needed
```

### 3. Start Unity

The credential API will be available at `/api/credentials` when Unity starts.

## API Endpoints

### SSH Keys (8 endpoints)

```bash
# Upload existing key pair
POST /api/credentials/ssh-keys
{
  "name": "production-key",
  "description": "Production server SSH key",
  "public_key": "ssh-rsa AAAA...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "key_type": "rsa",
  "key_size": 4096
}

# Generate new key pair
POST /api/credentials/ssh-keys/generate
{
  "name": "dev-key",
  "description": "Development SSH key",
  "key_type": "ed25519"
}

# List all SSH keys (private keys excluded)
GET /api/credentials/ssh-keys

# Get SSH key details
GET /api/credentials/ssh-keys/{id}

# Get SSH key with private key (requires auth, creates audit log)
GET /api/credentials/ssh-keys/{id}/private

# Delete SSH key
DELETE /api/credentials/ssh-keys/{id}
```

### Certificates (9 endpoints)

```bash
# Upload existing certificate
POST /api/credentials/certificates
{
  "name": "wildcard-cert",
  "description": "Wildcard SSL certificate",
  "certificate": "-----BEGIN CERTIFICATE-----\n...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "chain": "-----BEGIN CERTIFICATE-----\n...",
  "provider": "letsencrypt",
  "auto_renew": true,
  "renewal_days": 30
}

# Generate self-signed certificate
POST /api/credentials/certificates/generate-self-signed
{
  "name": "test-cert",
  "common_name": "example.com",
  "organization": "MyOrg",
  "validity_days": 365
}

# List all certificates
GET /api/credentials/certificates

# Get certificates expiring soon
GET /api/credentials/certificates/expiring?days=30

# Get certificate details
GET /api/credentials/certificates/{id}

# Get certificate with private key (requires auth)
GET /api/credentials/certificates/{id}/private

# Renew certificate
PUT /api/credentials/certificates/{id}/renew
{
  "certificate": "-----BEGIN CERTIFICATE-----\n...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "chain": "-----BEGIN CERTIFICATE-----\n..."
}

# Delete certificate
DELETE /api/credentials/certificates/{id}
```

### Server Credentials (7 endpoints)

```bash
# Create server credential
POST /api/credentials/server-credentials
{
  "server_profile_id": 1,
  "username": "admin",
  "password": "secret123",
  "ssh_key_id": 5,
  "sudo_password": "sudo123"
}

# List all credentials (passwords excluded)
GET /api/credentials/server-credentials

# Get credential details
GET /api/credentials/server-credentials/{id}

# Get credential by server
GET /api/credentials/server-credentials/server/{server_profile_id}

# Get credential with passwords (requires auth)
GET /api/credentials/server-credentials/{id}/secrets

# Update credential
PUT /api/credentials/server-credentials/{id}
{
  "username": "newadmin",
  "password": "newsecret",
  "ssh_key_id": 6
}

# Delete credential
DELETE /api/credentials/server-credentials/{id}
```

### Audit & Statistics (3 endpoints)

```bash
# Get recent audit logs
GET /api/credentials/audit-logs?skip=0&limit=100

# Get audit logs for specific resource
GET /api/credentials/audit-logs/resource/ssh_key/5

# Get credential statistics
GET /api/credentials/stats
```

## Security Features

### Encryption
- **Fernet symmetric encryption** for all sensitive data
- Private keys and passwords encrypted at rest
- Decryption only when explicitly requested

### Authentication
- **JWT authentication** required for all endpoints
- Uses Unity's existing auth system
- Role-based access (future: admin-only for sensitive operations)

### Audit Logging
- All operations logged with:
  - Action type (create, read, update, delete, use)
  - Resource type and ID
  - User ID
  - IP address
  - User agent
  - Success/failure status
- Separate audit table: `credential_audit_logs`

### Sensitive Data Access
- Standard endpoints exclude sensitive fields (private keys, passwords)
- Separate `/private` and `/secrets` endpoints for accessing sensitive data
- Accessing sensitive data:
  - Creates audit log entry
  - Updates `last_used` timestamp
  - Requires explicit authentication

### Input Validation
- Pydantic schemas validate all inputs
- Regex patterns prevent injection attacks
- Length limits on all string fields
- Format validation for keys and certificates

## Integration with Unity

### ServerProfile Integration
`ServerCredential` links directly to Unity's `ServerProfile` table, enabling:
- Automatic credential lookup when connecting to servers
- Centralized credential management
- Credential rotation without server reconfiguration

### Plugin Integration
Plugins can access credentials via:
```python
from app.services.credentials import ServerCredentialService, encryption_service

# Get credential for server
credential = ServerCredentialService.get_credential_by_server(
    db, server_profile_id, encryption_service, decrypt=True
)

# Use in SSH connection
ssh_connection = connect_ssh(
    hostname=server.hostname,
    username=credential.username,
    password=credential.password
)
```

## Database Schema

### SSH Keys
```sql
CREATE TABLE ssh_keys (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    public_key TEXT NOT NULL,
    private_key TEXT NOT NULL,  -- Encrypted
    key_type VARCHAR(20) NOT NULL,
    key_size INTEGER,
    fingerprint VARCHAR(100),
    created_by INTEGER,
    created_at TIMESTAMP,
    last_used TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id)
);
```

### Certificates
```sql
CREATE TABLE certificates (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    certificate TEXT NOT NULL,
    private_key TEXT,  -- Encrypted
    chain TEXT,
    provider VARCHAR(50),
    auto_renew BOOLEAN,
    renewal_days INTEGER,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    last_renewed TIMESTAMP,
    created_by INTEGER,
    created_at TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id)
);
```

### Server Credentials
```sql
CREATE TABLE server_credentials (
    id INTEGER PRIMARY KEY,
    server_profile_id INTEGER NOT NULL,
    username VARCHAR(100) NOT NULL,
    password TEXT,  -- Encrypted
    ssh_key_id INTEGER,
    sudo_password TEXT,  -- Encrypted
    created_by INTEGER,
    created_at TIMESTAMP,
    last_used TIMESTAMP,
    FOREIGN KEY(server_profile_id) REFERENCES server_profiles(id),
    FOREIGN KEY(ssh_key_id) REFERENCES ssh_keys(id),
    FOREIGN KEY(created_by) REFERENCES users(id),
    UNIQUE(server_profile_id)
);
```

### Audit Logs
```sql
CREATE TABLE credential_audit_logs (
    id INTEGER PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER NOT NULL,
    user_id INTEGER,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
```

## Testing

See `TESTING-GUIDE.md` for comprehensive testing instructions.

## Future Enhancements

1. **Certificate Auto-Renewal**: Background job to renew expiring certificates
2. **SSH Key Rotation**: Automated key rotation with audit trail
3. **Secret Scanning**: Prevent accidental secret commits
4. **Credential Sharing**: Share credentials between users with access control
5. **Integration with Secret Managers**: AWS Secrets Manager, HashiCorp Vault
6. **Step-CA Integration**: Automated certificate management with step-ca

## Troubleshooting

### Encryption Key Issues
```bash
# Error: "ENCRYPTION_KEY environment variable not set"
# Solution: Generate and set encryption key in .env
python3 backend/generate_encryption_key.py
```

### Database Migration Issues
```bash
# Error: "Table already exists"
# Solution: Check if models are already migrated
# Unity uses SQLAlchemy models, tables created automatically
```

### Permission Errors
```bash
# Error: "401 Unauthorized"
# Solution: Ensure JWT token is included in Authorization header
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/api/credentials/stats
```

## Original KC-Booth Project

KC-Booth staging directory preserved at: `/home/matthew/projects/HI/unity/kc-booth-staging/`
Original project untouched at: `/home/matthew/projects/HI/kc-booth`

Integration completed as core Unity service (not plugin) due to infrastructure dependencies.
