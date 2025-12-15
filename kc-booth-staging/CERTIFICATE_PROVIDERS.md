# Certificate Providers

kc-booth supports multiple certificate authorities and providers, allowing you to choose the best solution for your infrastructure.

## Supported Providers

### 1. Step-CA (Default)
**Best for**: Production SSH certificate management

Smallstep's step-ca is a modern, secure CA for SSH and TLS certificates.

**Configuration**:
```bash
CERT_PROVIDER=step-ca
STEP_CA_URL=http://step-ca:9000
STEP_PROVISIONER_PASSWORD=your-password
```

**Pros**:
- Enterprise-grade security
- Automated certificate rotation
- ACME protocol support
- Excellent documentation

**Cons**:
- Requires separate step-ca service
- More complex initial setup

---

### 2. OpenSSH
**Best for**: Testing, simple deployments, small homelabs

Uses native `ssh-keygen` to create a CA and sign certificates.

**Configuration**:
```bash
CERT_PROVIDER=openssh
```

**Pros**:
- No external dependencies
- Simple setup
- Perfect for testing
- Works offline

**Cons**:
- Manual CA key management
- No automated features
- Less suitable for large deployments

---

### 3. HashiCorp Vault
**Best for**: Enterprises already using Vault

Integrates with Vault's SSH secrets engine for certificate signing.

**Configuration**:
```bash
CERT_PROVIDER=vault
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=your-token
VAULT_SSH_PATH=ssh/sign/default
```

**Setup Requirements**:
1. Enable SSH secrets engine in Vault
2. Configure SSH CA role
3. Generate/provide Vault token

**Pros**:
- Integrates with existing Vault infrastructure
- Centralized secrets management
- Audit logging built-in
- Dynamic credentials

**Cons**:
- Requires Vault server
- More complex configuration
- Vault CLI must be installed

---

### 4. Let's Encrypt
**Best for**: TLS/HTTPS certificates (not SSH)

Uses certbot to obtain TLS certificates via Let's Encrypt.

**Note**: This provider issues HTTPS/TLS certificates, not SSH certificates!

**Configuration**:
```bash
CERT_PROVIDER=letsencrypt
```

**Pros**:
- Free TLS certificates
- Widely trusted
- Automatic renewal

**Cons**:
- Requires domain ownership validation
- Not for SSH certificates
- Requires port 80/443 access

---

## Switching Providers

### Quick Switch
Just change `CERT_PROVIDER` in `.env`:

```bash
# From step-ca to openssh for testing
CERT_PROVIDER=openssh
```

Restart the application:
```bash
docker compose restart app
```

### Migration Between Providers
When switching providers, existing certificates remain valid but new certificates use the new provider:

1. Update `CERT_PROVIDER` in `.env`
2. Add any provider-specific configuration
3. Restart application
4. Rotate certificates to use new provider:
   ```bash
   curl -X POST -H "X-API-Key: your-key" \
     http://localhost:8001/certificates/{cert_id}/rotate/
   ```

## Provider Comparison

| Feature | Step-CA | OpenSSH | Vault | Let's Encrypt |
|---------|---------|---------|-------|---------------|
| Certificate Type | SSH | SSH | SSH | TLS/HTTPS |
| External Service | Yes | No | Yes | No |
| Automated Rotation | Yes | Manual | Yes | Yes |
| Production Ready | ✓ | Limited | ✓ | ✓ (TLS only) |
| Setup Complexity | Medium | Low | High | Medium |
| Homelab Friendly | ✓ | ✓✓ | ○ | ○ |

Legend: ✓✓ = Excellent, ✓ = Good, ○ = Possible but not ideal

## Recommendations

### For Homelabs
- **Just starting**: `openssh` - Simple, no dependencies
- **Growing setup**: `step-ca` - Better automation and security

### For Production
- **General use**: `step-ca` - Modern, secure, automated
- **Using Vault already**: `vault` - Integrates with existing infrastructure

### For TLS Certificates
- **Public domain**: `letsencrypt` - Free and trusted
- **Internal/private**: `step-ca` - Better for internal CAs

## Example Configurations

### OpenSSH Setup (Testing)
```bash
# .env
CERT_PROVIDER=openssh
DISABLE_AUTH=true  # Optional for local testing
```

### Step-CA Setup (Production)
```bash
# .env
CERT_PROVIDER=step-ca
STEP_CA_URL=https://ca.example.com
STEP_PROVISIONER_PASSWORD=<strong-password>
```

### Vault Setup (Enterprise)
```bash
# .env
CERT_PROVIDER=vault
VAULT_ADDR=https://vault.company.com
VAULT_TOKEN=hvs.CAESIxyzabc...
VAULT_SSH_PATH=ssh-homelab/sign/default
```

## Adding Custom Providers

To add a new provider, edit `src/cert_providers.py`:

```python
class MyCustomProvider(CertificateProvider):
    def get_name(self) -> str:
        return "mycustom"
    
    def issue_certificate(self, domain: str) -> tuple[str, str]:
        # Your implementation
        return cert, key

# Register provider
PROVIDERS["mycustom"] = MyCustomProvider
```

## Troubleshooting

### Provider Not Found
```
ValueError: Unknown provider 'xyz'
```
Check `CERT_PROVIDER` value matches available providers.

### Vault Connection Failed
Check `VAULT_ADDR` and ensure Vault is accessible:
```bash
curl $VAULT_ADDR/v1/sys/health
```

### OpenSSH Certificates Not Working
Ensure `ssh-keygen` is installed and in PATH:
```bash
which ssh-keygen
ssh-keygen -h
```

### Step-CA Connection Failed
Verify step-ca is running and accessible:
```bash
docker compose logs step-ca
curl http://step-ca:9000/health
```
