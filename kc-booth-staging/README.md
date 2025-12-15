# kc-booth

kc-booth is a homelab application for managing SSH keys, servers, and certificates with built-in authentication and encryption.

## Features

- 🔐 **API Key Authentication** - Secure API access with user management
- 🔒 **Encryption** - Fernet symmetric encryption for passwords and SSH private keys
- 🔑 **SSH Key Management** - Store and manage SSH keys securely
- 🖥️ **Server Management** - Track servers with encrypted credentials
- 📜 **Certificate Management** - Integration with step-ca for certificate lifecycle
- 🔄 **Automated Rotation** - Certificate rotation before expiration
- 📊 **Audit Trail** - Track API key usage and access

## Security

- **At-rest encryption**: Passwords and private keys encrypted with Fernet (AES 128-bit)
- **API authentication**: API key-based authentication with bcrypt hashing
- **Secure key generation**: Cryptographically secure API keys (256 bits entropy)
- **Access control**: Users can only manage their own resources
- **Audit logging**: Track API key usage with timestamps

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.8+ (for setup scripts)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mylaniakea/kc-booth.git
   cd kc-booth
   ```

2. **Generate encryption key**:
   ```bash
   python3 generate_encryption_key.py
   ```
   Copy the `ENCRYPTION_KEY` value.

3. **Set environment variables**:
   ```bash
   export ENCRYPTION_KEY="your-generated-key-here"
   export DATABASE_URL="postgresql://user:password@postgres/kc-booth-db"
   export STEP_PROVISIONER_PASSWORD="password"
   ```

4. **Build and start services**:
   ```bash
   docker compose up --build -d
   ```

5. **Create admin user** (in a new terminal):
   ```bash
   export ENCRYPTION_KEY="your-key"
   export DATABASE_URL="postgresql://user:password@localhost:5432/kc-booth-db"
   export STEP_PROVISIONER_PASSWORD="password"
   python3 create_admin_user.py
   ```
   
   **Save the API key** displayed - you'll need it for all API requests!

6. **Test the API**:
   ```bash
   curl -H "X-API-Key: your-api-key" http://localhost:8001/health
   ```

The API will be available at `http://localhost:8001`.  
The API documentation is at `http://localhost:8001/docs`.

### Development Mode

To disable authentication for local development:

```bash
export DISABLE_AUTH=true
docker compose up
```

⚠️ **WARNING**: Never use `DISABLE_AUTH=true` in production!

## API Usage

### Authentication

All API endpoints (except `/health` and `/auth/login`) require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8001/ssh-keys/
```

### Login

Get an API key by logging in with username/password:

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'
```

### Manage API Keys

```bash
# Create a new API key
curl -X POST http://localhost:8001/auth/api-keys/ \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production Key"}'

# List your API keys
curl -H "X-API-Key: your-api-key" \
  http://localhost:8001/auth/api-keys/

# Revoke an API key
curl -X DELETE http://localhost:8001/auth/api-keys/1 \
  -H "X-API-Key: your-api-key"
```

### SSH Keys

```bash
# Create SSH key
curl -X POST http://localhost:8001/ssh-keys/ \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-key",
    "public_key": "ssh-rsa AAAA...",
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----..."
  }'

# List SSH keys
curl -H "X-API-Key: your-api-key" \
  http://localhost:8001/ssh-keys/
```

### Servers

```bash
# Create server
curl -X POST http://localhost:8001/servers/ \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "server1.local",
    "ip_address": "192.168.1.100",
    "username": "admin",
    "password": "password123"
  }'

# List servers
curl -H "X-API-Key: your-api-key" \
  http://localhost:8001/servers/
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `ENCRYPTION_KEY` | Yes | - | Fernet encryption key (generate with script) |
| `STEP_PROVISIONER_PASSWORD` | Yes | - | Step-CA provisioner password |
| `STEP_CA_URL` | No | `http://step-ca:9000` | Step-CA server URL |
| `ALLOW_ORIGINS` | No | `*` | CORS allowed origins |
| `DISABLE_AUTH` | No | `false` | Disable authentication (dev only!) |

## Running Tests

```bash
export ENCRYPTION_KEY="your-key"
docker compose run --rm test
```

## Security Considerations

### Encryption
- Encryption key must be kept secure - anyone with this key can decrypt stored credentials
- Use a secrets manager (Vault, AWS Secrets Manager, etc.) in production
- Key rotation requires decrypting and re-encrypting all data

### Authentication
- API keys have 256 bits of entropy (cryptographically secure)
- Keys are hashed with bcrypt before storage
- API keys are only shown once at creation - save them immediately
- Revoke compromised keys immediately

### Network Security
- Always use HTTPS/TLS in production
- Keep docker-compose passwords out of version control
- Use Docker secrets for production deployments

## Documentation

- [Encryption Implementation](ENCRYPTION_IMPLEMENTATION.md)
- [Environment Variable Validation](ENV_VALIDATION_IMPLEMENTATION.md)
- [Authentication Implementation](AUTHENTICATION_IMPLEMENTATION.md)
- [API Documentation](http://localhost:8001/docs) (when running)

## Architecture

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **CA**: step-ca
- **Encryption**: Fernet (AES 128-bit)
- **Authentication**: API keys with bcrypt
- **Scheduler**: APScheduler for certificate rotation

## License

See [LICENSE](LICENSE) file for details.
