# Multi-Tenancy Migration Strategy

**Date:** 2026-01-05
**Status:** Design Phase
**Target:** Unity Control Plane v2.0

## Overview

This document outlines the strategy for migrating Unity from a single-tenant architecture to a multi-tenant control plane suitable for managing multiple isolated environments.

## Current State

- Single PostgreSQL database with 25 tables
- No tenant isolation at database level
- User authentication with RBAC, but no tenant scoping
- All resources (plugins, credentials, K8s clusters) globally shared
- Alembic migrations now in place (baseline: e1d0454ae532)

## Multi-Tenancy Model

### Option 1: Schema-per-Tenant (Recommended for Control Plane)
**Pros:**
- Complete isolation at PostgreSQL level
- Easier backup/restore per tenant
- Better performance (no RLS overhead)
- Simpler query patterns
- Natural fit for Kubernetes namespace mapping

**Cons:**
- More complex schema management
- Higher operational overhead
- Migrations must run per-schema

**Use Case:** When tenants need strong isolation (different customers, different compliance requirements)

### Option 2: Row-Level Security (RLS) with tenant_id
**Pros:**
- Single schema, easier to maintain
- Simpler migrations
- Cross-tenant analytics possible
- Lower resource usage

**Cons:**
- All tenants share same tables
- Risk of data leakage if RLS misconfigured
- Performance overhead on queries
- Harder to backup individual tenants

**Use Case:** When tenants are departments within same organization

### **Chosen Approach: Hybrid Model**

1. **Default tenant (tenant_id = 'default')** - For existing single-tenant deployments
2. **Schema-per-tenant** - For new multi-tenant deployments
3. **Tenant registry table** in public schema to track all tenants

This allows:
- Backward compatibility (single tenant mode)
- Future migration to full multi-tenancy
- Gradual adoption

## Implementation Plan

### Phase 1: Add Tenant Concept (Non-Breaking)

1. Create `tenants` table in public schema
2. Add `tenant_id` column to all 25 tables (nullable, default 'default')
3. Create migration to add columns without breaking existing data
4. Update application code to use tenant context from JWT/API key
5. Add tenant_id to all queries via middleware

**Tables to modify:**
```sql
-- All 25 tables get this column
ALTER TABLE <table_name> ADD COLUMN tenant_id VARCHAR(50) DEFAULT 'default';
CREATE INDEX idx_<table>_tenant ON <table_name>(tenant_id);
```

### Phase 2: Tenant Registry

```sql
CREATE TABLE tenants (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(63),  -- For schema-per-tenant mode
    plan VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, pro, enterprise
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, suspended, deleted
    resource_quota JSONB,  -- CPU, memory, storage limits
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB  -- Custom tenant properties
);

CREATE INDEX idx_tenants_status ON tenants(status);
```

### Phase 3: User-Tenant Mapping

```sql
-- Add tenant relationship to users table
ALTER TABLE users ADD COLUMN tenant_id VARCHAR(50) REFERENCES tenants(id);
ALTER TABLE users ADD COLUMN role_in_tenant VARCHAR(50) DEFAULT 'admin';

-- A user can belong to multiple tenants (junction table)
CREATE TABLE user_tenant_memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tenant_id VARCHAR(50) REFERENCES tenants(id),
    role VARCHAR(50) NOT NULL,  -- admin, member, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tenant_id)
);
```

### Phase 4: Tenant Context Middleware

Add middleware to FastAPI backend:

```python
# app/middleware/tenant_context.py
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.tenant import get_tenant_from_token

class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Extract tenant from JWT or API key
        tenant_id = await get_tenant_from_token(request)
        request.state.tenant_id = tenant_id or 'default'
        response = await call_next(request)
        return response
```

### Phase 5: Query Scoping

Update all database queries to include tenant_id:

```python
# Before
db.query(Plugin).all()

# After
db.query(Plugin).filter(Plugin.tenant_id == request.state.tenant_id).all()
```

Use SQLAlchemy query decorators or custom base query class.

### Phase 6: API Changes

Add tenant creation/management endpoints:

```
POST   /api/v1/tenants              # Create tenant
GET    /api/v1/tenants              # List tenants (system admin only)
GET    /api/v1/tenants/{id}         # Get tenant details
PATCH  /api/v1/tenants/{id}         # Update tenant
DELETE /api/v1/tenants/{id}         # Soft-delete tenant
POST   /api/v1/tenants/{id}/suspend # Suspend tenant
POST   /api/v1/tenants/{id}/activate # Re-activate tenant
```

### Phase 7: Kubernetes Integration

Map tenants to Kubernetes namespaces:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-<tenant-id>
  labels:
    unity.holon.dev/tenant-id: <tenant-id>
    unity.holon.dev/plan: pro
```

Each tenant gets:
- Dedicated namespace
- Resource quotas
- Network policies
- RBAC bindings

## Migration Script Template

```python
"""add tenant support

Revision ID: <auto>
Revises: e1d0454ae532
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        # ... other columns
    )
    
    # Add tenant_id to all tables
    tables = [
        'users', 'plugins', 'plugin_executions', 'plugin_metrics',
        'kubernetes_clusters', 'kubernetes_resources', 'deployment_intents',
        'application_blueprints', 'server_profiles', 'server_snapshots',
        'ssh_keys', 'certificates', 'server_credentials', 
        'credential_audit_logs', 'alerts', 'alert_channels',
        'threshold_rules', 'notification_logs', 'knowledge',
        'reports', 'settings', 'push_subscriptions', 'plugin_api_keys',
        'step_ca_config', 'resource_reconciliations'
    ]
    
    for table in tables:
        op.add_column(table, sa.Column('tenant_id', sa.String(50), 
                                       server_default='default', nullable=False))
        op.create_index(f'idx_{table}_tenant', table, ['tenant_id'])
    
    # Insert default tenant
    op.execute("""
        INSERT INTO tenants (id, name, status) 
        VALUES ('default', 'Default Tenant', 'active')
    """)

def downgrade():
    # Drop tenant_id from all tables
    # Drop tenants table
    pass
```

## Testing Strategy

1. **Unit Tests**: Test tenant isolation in queries
2. **Integration Tests**: 
   - Create multiple tenants
   - Verify data isolation
   - Test cross-tenant access denial
3. **Load Tests**: Performance with 100+ tenants
4. **Security Tests**: Attempt cross-tenant data access

## Rollout Plan

1. ✅ **Week 1**: Design and document (THIS DOCUMENT)
2. **Week 2**: Implement tenant registry and migrations
3. **Week 3**: Add middleware and query scoping
4. **Week 4**: Update frontend for tenant selection
5. **Week 5**: Testing and security audit
6. **Week 6**: Staged rollout with feature flag

## Backward Compatibility

- Existing deployments continue as 'default' tenant
- No breaking changes to API (tenant optional)
- Feature flag: `MULTI_TENANCY_ENABLED=false` for single-tenant mode

## Resource Quotas per Tenant

```python
resource_quota = {
    "kubernetes_clusters": 5,     # Max K8s clusters
    "plugins": 50,                 # Max plugins
    "users": 100,                  # Max users per tenant
    "storage_gb": 100,             # Max storage
    "api_calls_per_hour": 10000,  # Rate limiting
}
```

## Security Considerations

1. **JWT tokens** must include tenant_id claim
2. **API keys** must be tenant-scoped
3. **Audit logging** for all cross-tenant access attempts
4. **RLS policies** as defense-in-depth (even with tenant_id columns)
5. **Regular security audits** of tenant isolation

## Monitoring

Track per-tenant:
- API usage
- Resource consumption (CPU, memory, storage)
- Plugin executions
- K8s operations
- Alert frequency

## Next Steps

1. ✅ Create this strategy document
2. ⏳ Generate Alembic migration for tenant support
3. ⏳ Implement tenant service and middleware
4. ⏳ Update all database queries
5. ⏳ Add tenant management UI
6. ⏳ Write comprehensive tests

---
**Document Version:** 1.0
**Last Updated:** 2026-01-05
**Owner:** Unity Team
