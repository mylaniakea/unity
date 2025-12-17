# Integration Quick Reference

## At a Glance

### Current Status
```
✅ Phase 1-2: KC-Booth (Complete) - Credential management
🔄 Phase 3: BD-Store (Next) - Infrastructure monitoring  
⏸️  Phase 4: Uptainer (Waiting) - Container automation
```

### Integration Size Estimates
```
KC-Booth:  3,300 LOC | 5 models | 37 endpoints | Medium complexity
BD-Store:  4,500 LOC | 4 models | 50 endpoints | High complexity
Uptainer:  7,500 LOC | 12 models | 60 endpoints | Very high complexity
═══════════════════════════════════════════════════════════════════
Total:    15,300 LOC | 21 models | 147 endpoints
```

### Dependency Chain
```
KC-Booth → BD-Store → Uptainer
(creds)    (servers)   (containers)
```

## Integration Recipe (7 Steps)

### 1️⃣  Branch & Stage
```bash
git checkout -b feature/{project}-integration
cp -r /path/to/{project} unity/{project}-staging/
```

### 2️⃣  Models → `backend/app/models.py`
- Copy model classes
- Rename conflicts (Server → MonitoredServer)
- Add FKs to link Unity models
- Reuse Unity models (Alert, User)

### 3️⃣  Services → `backend/app/services/{feature}/`
```
backend/app/services/
└─ {feature}/
   ├─ {domain1}.py
   ├─ {domain2}.py
   └─ ...
```

### 4️⃣  Router → `backend/app/routers/{feature}.py`
- Single router file per feature
- Apply Unity auth middleware
- Use Unity response formats

### 5️⃣  Scheduler → `backend/app/schedulers/{feature}_tasks.py`
- Hook into Unity's APScheduler
- Define task functions
- Set cron schedules

### 6️⃣  Database
```bash
# Generate migration
alembic revision --autogenerate -m "Add {feature} models"

# Test migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### 7️⃣  Test & Deploy
```bash
# Test with Docker Compose
docker-compose up -d

# Verify endpoints
curl http://localhost:8000/api/v1/{feature}/...

# Push
git add .
git commit -m "Integrate {feature}"
git push origin feature/{feature}-integration
```

## Key Files to Modify

### Always Modified
- `backend/app/models.py` - Add models
- `backend/app/main.py` - Register router

### Always Created
- `backend/app/services/{feature}/` - Service directory
- `backend/app/routers/{feature}.py` - Router file
- `backend/app/schedulers/{feature}_tasks.py` - Scheduler tasks

### Sometimes Extended
- `backend/app/services/ai_provider.py` - Add AI prompts (Uptainer)
- `backend/app/services/notification_service.py` - Add event types
- `backend/app/config.py` - Add feature flags

## Decision Matrix

### When to Reuse Unity Models
- ✅ Use Unity Alert (don't create {Feature}Alert)
- ✅ Use Unity User (don't create {Feature}User)
- ✅ Use Unity NotificationLog (extend types)
- ❌ Don't reuse ServerProfile (it's templates, not actual servers)

### When to Extend Unity Services
- ✅ Extend ai_provider with domain-specific prompts
- ✅ Extend notification_service with domain event types
- ✅ Use ssh.py service directly
- ❌ Don't extend if feature needs isolated logic (create new service)

### When to Add Feature Flags
- ✅ Complex optional features (ENABLE_K8S, ENABLE_TRIVY)
- ✅ External dependencies (Trivy, Kubernetes client)
- ❌ Core features (always enabled)

## Phase 3: BD-Store Checklist

- [ ] Branch: `feature/bd-store-integration`
- [ ] Stage: `unity/bd-store-staging/`
- [ ] Models: MonitoredServer, StorageDevice, StoragePool, DatabaseInstance
- [ ] Alert extension: Add `alert_type` field, map BD-Store alerts
- [ ] Services: 10 files under `services/infrastructure/`
- [ ] Router: `routers/infrastructure.py` (~50 endpoints)
- [ ] Scheduler: `schedulers/infrastructure_tasks.py`
- [ ] Migration: `alembic revision --autogenerate -m "Add infrastructure models"`
- [ ] Test: Docker Compose + endpoint verification
- [ ] Push & merge

## Phase 4: Uptainer Checklist

- [ ] Branch: `feature/uptainer-integration`
- [ ] Stage: `unity/uptainer-staging/`
- [ ] Models: 12+ (ContainerHost, Container, UpdateHistory, etc.)
- [ ] Link: ContainerHost.monitored_server_id → MonitoredServer
- [ ] AI: Extend `ai_provider` with container analysis
- [ ] Notifications: Extend with container event types
- [ ] Services: 15+ files under `services/containers/`
- [ ] Router: `routers/containers.py` (~60 endpoints)
- [ ] Scheduler: `schedulers/container_tasks.py`
- [ ] Feature flags: ENABLE_K8S, ENABLE_TRIVY
- [ ] Migration: `alembic revision --autogenerate -m "Add container models"`
- [ ] Test: Docker Compose + endpoint verification
- [ ] Push & merge

## Common Pitfalls & Solutions

### ❌ Pitfall: Duplicate Alert models
✅ Solution: Extend Unity Alert with `alert_type` field

### ❌ Pitfall: Encrypted credentials in multiple places
✅ Solution: Use FK to KC-Booth SSHKey/ServerCredential

### ❌ Pitfall: Multiple schedulers
✅ Solution: Consolidate into Unity's APScheduler

### ❌ Pitfall: Inconsistent API patterns
✅ Solution: Follow Unity's auth/response patterns

### ❌ Pitfall: Model name conflicts
✅ Solution: Rename (Server → MonitoredServer)

## File Count Breakdown

### Phase 1-2: KC-Booth ✅
```
Models:     5 classes in models.py
Services:   8 files in services/credentials/
Routers:    1 file (credentials.py)
Scheduler:  1 file (credential_tasks.py)
```

### Phase 3: BD-Store 🔄
```
Models:     4 classes in models.py
Services:   10 files in services/infrastructure/
Routers:    1 file (infrastructure.py)
Scheduler:  1 file (infrastructure_tasks.py)
```

### Phase 4: Uptainer ⏸️
```
Models:     12 classes in models.py
Services:   15 files in services/containers/
Routers:    1 file (containers.py)
Scheduler:  1 file (container_tasks.py)
```

## Helpful Commands

### Check current models
```bash
grep "^class [A-Z]" backend/app/models.py
```

### Count endpoints
```bash
grep -E "@router\.(get|post|put|delete|patch)" backend/app/routers/*.py | wc -l
```

### List services
```bash
find backend/app/services -name "*.py" -type f | wc -l
```

### Check scheduler tasks
```bash
ls backend/app/schedulers/*.py
```

### Database status
```bash
alembic current
alembic history
```

---

**Tip**: Keep this reference open while implementing integration phases!
