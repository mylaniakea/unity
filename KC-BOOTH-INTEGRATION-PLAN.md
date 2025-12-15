# KC-Booth Integration Plan

**Branch:** `feature/kc-booth-integration`  
**Started:** December 15, 2025  
**Status:** Phase 2 - In Progress

---

## Overview

Integrating KC-Booth credential management into Unity as a core service. KC-Booth provides secure SSH key and certificate management with encryption, audit logging, and rate limiting.

## Integration Strategy

### Option Chosen: Merge as Core Service

KC-Booth will be integrated directly into Unity's backend as a core credential management service, not as a plugin. This is because:
- Credentials are infrastructure dependencies for other plugins
- Centralized credential management improves security
- Reduces operational complexity
- Enables Unity plugins to use managed credentials

---

## Phase 2.1: Code Analysis & Planning

### KC-Booth Components to Integrate:

**Core Services:**
- `src/models.py` - SSH keys, certificates, server credentials models
- `src/crud.py` - CRUD operations for credentials
- `src/encryption.py` - Fernet encryption for secrets
- `src/auth.py` - Authentication (JWT already in Unity)
- `src/audit.py` - Audit logging for credential operations
- `src/cert_providers.py` - Certificate provider integrations
- `src/step_ca.py` - Step-CA integration

**Supporting:**
- `src/database.py` - Database setup (merge with Unity's)
- `src/schemas.py` - Pydantic schemas
- `src/config.py` - Configuration (merge with Unity's)
- `src/rate_limit.py` - Rate limiting (Unity already has this)
- `src/metrics.py` - Metrics (integrate with Unity's)
- `src/scheduler.py` - Scheduled tasks (integrate with Unity's APScheduler)

**Exclude:**
- `src/main.py` - Standalone app (Unity has its own main.py)
- `frontend/` - UI (not needed for now)
- Docker files - Use Unity's deployment

---

## Phase 2.2: File Structure

### New Unity Structure:

```
unity/backend/app/
├── services/
│   ├── credentials/          # NEW: KC-Booth services
│   │   ├── __init__.py
│   │   ├── encryption.py     # From KC-Booth
│   │   ├── ssh_keys.py       # From KC-Booth crud.py
│   │   ├── certificates.py   # From KC-Booth crud.py
│   │   ├── providers.py      # From KC-Booth cert_providers.py
│   │   ├── step_ca.py        # From KC-Booth
│   │   └── audit.py          # From KC-Booth (merge with plugin audit)
│   ├── plugin_manager.py     # Existing
│   └── ...
├── models.py                  # Add KC-Booth models
├── routers/
│   ├── credentials.py        # NEW: Credential management API
│   └── ...
└── schemas_credentials.py    # NEW: From KC-Booth schemas.py
```

---

## Phase 2.3: Database Schema

### New Tables (from KC-Booth):

1. **ssh_keys** - SSH key pairs with encryption
2. **certificates** - SSL/TLS certificates
3. **server_credentials** - Server connection credentials
4. **step_ca_config** - Step-CA configuration (if used)
5. **audit_logs** - Credential operation audit trail

### Integration with Existing:

- Link to Unity's `User` table for ownership
- Use Unity's `ServerProfile` for credential associations

---

## Phase 2.4: Configuration Merge

### Environment Variables to Add:

```bash
# Encryption
ENCRYPTION_KEY=<generated-key>  # For credential encryption

# Step-CA (optional)
STEP_CA_URL=
STEP_CA_FINGERPRINT=
STEP_CA_PROVISIONER=
STEP_CA_PASSWORD=

# Certificate Providers (optional)
CERT_PROVIDER=none  # none, step-ca, lets-encrypt, etc.
```

### Validation:

- Ensure ENCRYPTION_KEY is set
- Validate certificate provider config if enabled

---

## Phase 2.5: API Integration

### New Endpoints:

**SSH Keys:**
- `POST /api/credentials/ssh-keys` - Create SSH key pair
- `GET /api/credentials/ssh-keys` - List keys
- `GET /api/credentials/ssh-keys/{id}` - Get key details
- `DELETE /api/credentials/ssh-keys/{id}` - Delete key

**Certificates:**
- `POST /api/credentials/certificates` - Create/import certificate
- `GET /api/credentials/certificates` - List certificates
- `GET /api/credentials/certificates/{id}` - Get certificate
- `POST /api/credentials/certificates/{id}/renew` - Renew certificate
- `DELETE /api/credentials/certificates/{id}` - Delete certificate

**Server Credentials:**
- `POST /api/credentials/servers` - Store server credentials
- `GET /api/credentials/servers` - List credentials
- `GET /api/credentials/servers/{id}` - Get credentials (decrypted)
- `PUT /api/credentials/servers/{id}` - Update credentials
- `DELETE /api/credentials/servers/{id}` - Delete credentials

---

## Phase 2.6: Security Considerations

### From KC-Booth (Already Implemented):

✅ Fernet encryption for secrets at rest  
✅ Rate limiting on credential operations  
✅ Audit logging for all operations  
✅ JWT authentication  
✅ Input validation  

### Unity Integration:

- Use Unity's existing JWT auth system
- Merge KC-Booth audit logs with Unity's plugin audit logs
- Use Unity's rate limiter (already implemented)
- Ensure encryption key is NOT committed to repo

---

## Phase 2.7: Testing Plan

### Unit Tests:
- Encryption/decryption
- CRUD operations
- Certificate validation
- Provider integrations

### Integration Tests:
- End-to-end credential lifecycle
- Plugin access to credentials
- Audit trail verification

### Security Tests:
- Encryption key validation
- Access control
- Rate limiting
- Audit completeness

---

## Implementation Steps

### Step 1: Copy and Organize Files ✅
- [x] Copy kc-booth to staging directory
- [x] Remove kc-booth git history
- [x] Create integration plan

### Step 2: Database Models
- [ ] Copy KC-Booth models to Unity's models.py
- [ ] Update foreign keys to reference Unity tables
- [ ] Create database migration script

### Step 3: Services Integration
- [ ] Create backend/app/services/credentials/ directory
- [ ] Copy and adapt encryption.py
- [ ] Copy and adapt credential CRUD operations
- [ ] Copy certificate providers
- [ ] Merge audit logging with Unity's

### Step 4: API Routes
- [ ] Create backend/app/routers/credentials.py
- [ ] Implement all credential endpoints
- [ ] Add authentication/authorization
- [ ] Add rate limiting

### Step 5: Configuration
- [ ] Update .env.example with credential variables
- [ ] Add encryption key generation script
- [ ] Update Unity's config validation

### Step 6: Testing
- [ ] Create test database
- [ ] Test encryption/decryption
- [ ] Test API endpoints
- [ ] Test plugin integration (plugins using credentials)

### Step 7: Documentation
- [ ] Update README with credential management
- [ ] Document API endpoints
- [ ] Add security best practices
- [ ] Update TESTING-GUIDE.md

---

## Timeline

- **Phase 2.1-2.2:** Code analysis and planning - ✅ COMPLETE
- **Phase 2.3:** Database schema (2-3 hours)
- **Phase 2.4:** Services integration (4-6 hours)
- **Phase 2.5:** API routes (2-3 hours)
- **Phase 2.6:** Configuration (1 hour)
- **Phase 2.7:** Testing (2-3 hours)
- **Total:** ~12-18 hours

---

## Success Criteria

- [ ] All KC-Booth models integrated into Unity database
- [ ] Credential CRUD operations working
- [ ] Encryption/decryption functional
- [ ] API endpoints secure and tested
- [ ] Audit logging operational
- [ ] Plugins can access managed credentials
- [ ] No secrets in git repository
- [ ] Full test coverage

---

## Notes

- Original kc-booth preserved at `/home/matthew/projects/HI/kc-booth`
- Staging copy at `/home/matthew/projects/HI/unity/kc-booth-staging`
- Integration branch: `feature/kc-booth-integration`
- KC-Booth was built with security as priority - maintain that!

---

**Next:** Start with database models integration
