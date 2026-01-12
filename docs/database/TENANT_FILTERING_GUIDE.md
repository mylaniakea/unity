# Tenant Filtering Implementation Guide

## Overview
Unity's multi-tenant architecture requires all database queries to be scoped by `tenant_id`. This guide provides patterns and tools for implementing tenant filtering across the codebase.

## Audit Results
- **Total queries**: 256
- **Router files**: 20 files
- **Service files**: 16 files
- **Models requiring filtering**: 25 models

### Top Priority Files (by query count)
1. `routers/k8s_clusters.py` - 22 queries (✅ 1 done)
2. `routers/k8s_resources.py` - 20 queries  
3. `services/plugin_manager.py` - 20 queries
4. `routers/alerts.py` - 18 queries
5. `services/credentials/*` - 38 queries across 4 files

## Implementation Patterns

### Pattern 1: Router GET Endpoints (List/Detail)
```python
from app.core.dependencies import get_tenant_id

@router.get("", response_model=ListResponse)
async def list_resources(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)  # ADD THIS
):
    # OLD: query = select(Model)
    # NEW:
    query = select(Model).where(Model.tenant_id == tenant_id)
    
    # Additional filters can chain
    if some_filter:
        query = query.where(Model.field == value)
```

### Pattern 2: Router POST Endpoints (Create)
```python
@router.post("", response_model=DetailResponse)
async def create_resource(
    data: CreateSchema,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)  # ADD THIS
):
    resource = Model(
        **data.dict(),
        tenant_id=tenant_id  # ADD THIS
    )
    db.add(resource)
    db.commit()
```

### Pattern 3: Router PUT/DELETE Endpoints (Update/Delete)
```python
@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)  # ADD THIS
):
    # Always filter by BOTH id AND tenant_id for security
    resource = db.execute(
        select(Model).where(
            Model.id == resource_id,
            Model.tenant_id == tenant_id  # ADD THIS
        )
    ).scalar_one_or_none()
    
    if not resource:
        raise HTTPException(404, "Not found")
```

### Pattern 4: Service Layer Methods
```python
class SomeService:
    def get_resources(self, db: Session, tenant_id: str):  # ADD tenant_id param
        return db.execute(
            select(Model).where(Model.tenant_id == tenant_id)
        ).scalars().all()
    
    def create_resource(self, db: Session, tenant_id: str, data: dict):
        resource = Model(**data, tenant_id=tenant_id)  # ADD tenant_id
        db.add(resource)
        db.commit()
        return resource
```

### Pattern 5: Background Jobs/Schedulers
```python
# For scheduled tasks that operate on all tenants
def scheduled_task():
    db = next(get_db())
    tenants = db.execute(select(Tenant)).scalars().all()
    
    for tenant in tenants:
        # Process each tenant separately
        process_tenant_data(db, tenant.id)

def process_tenant_data(db: Session, tenant_id: str):
    resources = db.execute(
        select(Model).where(Model.tenant_id == tenant_id)
    ).scalars().all()
    # ... process resources
```

## Model-Specific Notes

### Settings Model
- Singleton pattern per tenant
- Query: `select(Settings).where(Settings.tenant_id == tenant_id).first()`
- Always create with `tenant_id` if not exists

### User Model  
- Users can belong to multiple tenants via `UserTenantMembership`
- Authentication returns user + tenant context
- Query user's resources: `User.tenant_id == tenant_id`

### Plugin Models
- Plugins themselves may be global, but executions/metrics are tenant-scoped
- `Plugin`: May need special handling for shared vs tenant-specific plugins
- `PluginExecution`, `PluginMetric`: Always tenant-scoped

## Migration Checklist

### Router Files (20 files)
- [ ] `routers/k8s_clusters.py` (22 queries) - ✅ 1/22 done
- [ ] `routers/k8s_resources.py` (20 queries)
- [ ] `routers/alerts.py` (18 queries)
- [ ] `routers/profiles.py`
- [ ] `routers/plugins.py`
- [ ] `routers/plugins_v2.py`
- [ ] `routers/plugins_v2_secure.py`
- [ ] `routers/plugin_keys.py`
- [ ] `routers/reports.py`
- [ ] `routers/credentials.py`
- [ ] `routers/users.py` - ✅ import added
- [ ] `routers/ai.py`
- [ ] `routers/knowledge.py`
- [ ] `routers/settings.py`
- [ ] `routers/push.py`
- [ ] `routers/thresholds.py`
- [ ] `routers/auth.py` (special handling)
- [ ] `routers/terminal.py`
- [ ] `routers/system.py` (may not need filtering)
- [ ] `routers/orchestration/deploy.py`

### Service Files (16 files)
- [ ] `services/plugin_manager.py` (20 queries)
- [ ] `services/credentials/server_credentials.py` (14 queries)
- [ ] `services/credentials/distribution.py` (12 queries)
- [ ] `services/credentials/certificates.py` (12 queries)
- [ ] `services/credentials/ssh_keys.py` (10 queries)
- [ ] `services/credentials/audit.py` (10 queries)
- [ ] `services/orchestration/deployment_orchestrator.py` (10 queries)
- [ ] `services/threshold_monitor.py`
- [ ] `services/k8s_reconciler.py`
- [ ] `services/report_generation.py`
- [ ] `services/auth.py` (special handling)
- [ ] `services/ai.py`
- [ ] `services/deployment_manager.py`
- [ ] `services/plugin_security.py`
- [ ] `services/orchestration/blueprint_loader.py`
- [ ] `services/credentials/metrics.py`

## Testing Strategy

### Unit Tests
```python
def test_tenant_isolation():
    # Create two tenants
    tenant1 = create_tenant("tenant1")
    tenant2 = create_tenant("tenant2")
    
    # Create resources for each
    resource1 = create_resource(tenant_id="tenant1")
    resource2 = create_resource(tenant_id="tenant2")
    
    # Verify isolation
    tenant1_resources = get_resources(tenant_id="tenant1")
    assert resource1 in tenant1_resources
    assert resource2 not in tenant1_resources
```

### Integration Tests
- Test all CRUD operations with different tenants
- Verify no cross-tenant data leaks
- Test middleware correctly extracts tenant from JWT/API key

## Validation Tool

Run the validation script to check coverage:
```bash
python3 scripts/validate_tenant_filtering.py
```

This will report:
- Queries missing tenant filtering
- Routes without tenant_id parameter
- Service methods needing updates

## Timeline Estimate
- **Phase 3.1**: High-priority routers (5 files) - 4-6 hours
- **Phase 3.2**: Remaining routers (15 files) - 8-10 hours  
- **Phase 3.3**: Service layer (16 files) - 10-12 hours
- **Phase 3.4**: Testing & validation - 4-6 hours

**Total**: 26-34 hours of focused development

## Notes
- Middleware is already in place (disabled with `multi_tenancy_enabled=False`)
- Database schema is complete with tenant_id on all 25 models
- Enable multi-tenancy by setting flag to `True` in `main.py` after Phase 3 complete
