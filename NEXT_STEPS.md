# Unity Multi-Tenancy: Next Steps

**Current State:** Database schema migration complete ✅
**Branch:** clean-k8s-deploy
**Commit:** 03b51a9

---

## What We Accomplished Today (2026-01-05)

### ✅ Foundation Complete
1. **Alembic Migrations** - Database under version control
   - Baseline migration: `e1d0454ae532`
   - Tenant support: `tenant_support_001`
2. **Database Schema** - Multi-tenant ready
   - 25 tables with tenant_id column + indexes
   - tenants table (with 'default' tenant)
   - user_tenant_memberships table
3. **Backup/Restore** - Production-ready disaster recovery
   - Automated backups with retention
   - Tested restore process
4. **Documentation** - Complete strategy
   - `docs/CONTROL_PLANE_DESIGN.md` - Full architecture
   - `docs/database/MULTI_TENANCY_STRATEGY.md` - Implementation plan
5. **Helm Chart** - K8s deployment ready
   - `helm/unity/` - Production-ready templates

### ✅ Verification
- Backend API: Working ✓
- Database: 25/25 tables with tenant_id ✓
- Existing data: Migrated to 'default' tenant ✓
- Backups: 3 successful backups created ✓

---

## Phase 2: Application Logic (Week 1-2)

### Step 1: Tenant Context Middleware
**File:** `backend/app/middleware/tenant_context.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import jwt

class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract tenant_id from JWT or API key
        tenant_id = "default"  # TODO: extract from token
        
        # For now, always use default tenant
        request.state.tenant_id = tenant_id
        
        response = await call_next(request)
        return response
```

**Action:** Create this file and register in `backend/app/main.py`

### Step 2: Update SQLAlchemy Models
**File:** `backend/app/models.py`

Add tenant_id to all model classes (already in database, need ORM definitions):
```python
class User(Base):
    # ... existing fields ...
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False, default='default')
    
class Plugin(Base):
    # ... existing fields ...
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False, default='default')
    
# Repeat for all 25 models
```

### Step 3: Add Tenant Filtering Dependency
**File:** `backend/app/core/dependencies.py`

```python
from fastapi import Depends, Request

def get_tenant_id(request: Request) -> str:
    """Extract tenant_id from request context"""
    return request.state.tenant_id

# Use in routes like:
# def get_clusters(tenant_id: str = Depends(get_tenant_id)):
#     return db.query(Cluster).filter(Cluster.tenant_id == tenant_id).all()
```

### Step 4: Update All Query Operations
**Files:** All files in `backend/app/routers/`, `backend/app/services/`

For EVERY database query, add tenant filtering:
```python
# Before:
clusters = db.query(KubernetesCluster).all()

# After:
clusters = db.query(KubernetesCluster).filter(
    KubernetesCluster.tenant_id == tenant_id
).all()

# Before:
new_plugin = Plugin(name="example", ...)

# After:
new_plugin = Plugin(
    name="example",
    tenant_id=tenant_id,  # Add this
    ...
)
```

**Estimated:** ~250 query locations need updating

### Step 5: Create Tenant Model
**File:** `backend/app/models.py`

```python
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    schema_name = Column(String(63))
    plan = Column(String(50), default='free')
    status = Column(String(20), default='active')
    resource_quota = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)
    metadata = Column(JSONB)
    
class UserTenantMembership(Base):
    __tablename__ = "user_tenant_memberships"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False)
    role = Column(String(50), nullable=False)  # admin, member, viewer
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Step 6: Tenant Management API
**File:** `backend/app/routers/tenants.py` (new)

```python
from fastapi import APIRouter, Depends
from app.models import Tenant

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])

@router.post("/")
async def create_tenant(tenant: TenantCreate):
    """Create new tenant (system admin only)"""
    pass

@router.get("/")
async def list_tenants():
    """List all tenants (system admin only)"""
    pass

@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant details"""
    pass

@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: str, updates: TenantUpdate):
    """Update tenant"""
    pass

@router.post("/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str):
    """Suspend tenant"""
    pass
```

---

## Phase 3: Authentication Enhancement (Week 2-3)

### Step 1: Update JWT Token
**File:** `backend/app/core/security.py`

Add tenant_id to JWT claims:
```python
def create_access_token(user_id: int, tenant_id: str) -> str:
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,  # Add this
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

### Step 2: Update API Key System
**File:** `backend/app/models.py`

API keys already have tenant_id from migration. Update creation:
```python
# New API key format: uk_{tenant_id}_{random}
api_key = f"uk_{tenant_id}_{secrets.token_urlsafe(32)}"
```

### Step 3: Add System Admin Role
**File:** `backend/app/models.py`

```python
class User(Base):
    # ... existing fields ...
    is_system_admin = Column(Boolean, default=False)  # Cross-tenant access
```

---

## Phase 4: K8s Multi-Tenancy (Week 3-4)

### Step 1: Namespace Provisioning
**File:** `backend/app/services/k8s_tenant_manager.py` (new)

```python
async def provision_tenant_namespace(tenant_id: str, resource_quota: dict):
    """
    Create tenant namespace with:
    - Namespace: tenant-{tenant_id}
    - ResourceQuota
    - NetworkPolicy
    - ServiceAccount
    """
    pass
```

### Step 2: Update Orchestration
**File:** `backend/app/services/orchestration/deployment_orchestrator.py`

Deploy to tenant-specific namespace:
```python
namespace = f"tenant-{tenant_id}"
```

### Step 3: Label Resources
All K8s resources get labels:
```yaml
labels:
  tenant-id: {tenant_id}
  managed-by: unity
```

---

## Phase 5: Testing & Validation (Week 4-5)

### Test Cases
1. **Tenant Isolation**
   - Create 2 tenants
   - Verify data isolation
   - Attempt cross-tenant access (should fail)

2. **Multi-user Tenancy**
   - Add users to tenant
   - Verify roles work
   - Test user removal

3. **Resource Quotas**
   - Set quota limits
   - Attempt to exceed
   - Verify enforcement

4. **K8s Namespace**
   - Deploy to tenant namespace
   - Verify isolation
   - Test cleanup on tenant deletion

---

## Quick Reference

### Key Files Created Today
```
backend/alembic/                       # Database migrations
├── env.py                             # Alembic config
├── script.py.mako                     # Migration template
└── versions/
    ├── e1d0454ae532_initial_...py     # Baseline
    └── 20260105_073107_add_...py      # Tenant support

scripts/
├── backup-database.sh                 # Automated backups
├── restore-database.sh                # Safe restore
├── apply-tenant-migration.sh          # Manual migration
└── test-dashboard.sh                  # Connectivity tests

docs/
├── CONTROL_PLANE_DESIGN.md            # Full architecture
└── database/
    ├── MULTI_TENANCY_STRATEGY.md      # Implementation plan
    └── SCHEMA_BASELINE.md             # Schema documentation

helm/unity/                            # K8s deployment
├── Chart.yaml
├── values.yaml
├── README.md
└── templates/
    ├── _helpers.tpl
    ├── secret.yaml
    └── NOTES.txt
```

### Useful Commands
```bash
# Backup database
./scripts/backup-database.sh

# Check migration status
docker exec -e DATABASE_URL="postgresql+psycopg2://homelab_user:homelab_password@db:5432/homelab_db" \
  homelab-backend alembic current

# Verify tenant support
docker exec homelab-db psql -U homelab_user -d homelab_db -c "SELECT * FROM tenants;"

# Test connectivity
./scripts/test-dashboard.sh

# Deploy to K8s (when ready)
helm install unity ./helm/unity
```

---

## Timeline Estimate

- **Phase 2:** 1-2 weeks (application logic)
- **Phase 3:** 1 week (authentication)
- **Phase 4:** 1-2 weeks (K8s integration)
- **Phase 5:** 1 week (testing)

**Total:** 4-6 weeks to production-ready multi-tenant control plane

---

## Notes

- All existing features remain functional
- 'default' tenant preserves current single-tenant behavior
- Backward compatible - can run in single-tenant mode indefinitely
- Database can be restored from backups at any time
- super coming online will enable ZFS storage isolation layer

---

*Last Updated: 2026-01-05*
*Status: Phase 1 Complete ✅*
