# Integration Overview

Unity is built through a systematic integration of three specialized homelab management tools. This page explains the integration strategy, phases, and benefits.

## Integration Vision

Unity consolidates three mature, production-ready projects:
1. **KC-Booth** - Credential and certificate management
2. **BD-Store** - Infrastructure monitoring
3. **Uptainer** - Container automation

Rather than maintaining three separate tools, Unity provides a unified platform with shared authentication, database, and infrastructure.

## Integration Strategy: Monolithic Pattern

We use a **monolithic integration** approach where all features are merged into a single codebase, database, and deployment unit.

### Why Monolithic?
- ✅ **Single deployment** - One Docker Compose / K8s deployment
- ✅ **Unified auth** - One login for all features
- ✅ **Shared database** - Consistent data across features
- ✅ **Cross-feature functionality** - Features can reference each other
- ✅ **Simplified operations** - One service to monitor and maintain

### Integration Pattern (7 Steps)

1. **Branch & Stage** - Create feature branch, copy project to staging
2. **Models** - Merge database models into `models.py`, resolve conflicts
3. **Services** - Port business logic to `services/{feature}/`
4. **Router** - Create API router in `routers/{feature}.py`
5. **Scheduler** - Integrate background tasks into APScheduler
6. **Migration** - Generate Alembic migration
7. **Test & Deploy** - Validate with Docker Compose, commit, push

## Integration Phases

### Phase 1-2: KC-Booth (✅ Complete)

**Status**: 100% complete, production-ready

**Scope**:
- 5 models (SSHKey, Certificate, ServerCredential, StepCAConfig, CredentialAuditLog)
- 8 services (SSH key mgmt, certificate lifecycle, ACME renewal, distribution)
- 37 API endpoints
- 3 scheduler tasks (cert expiry, unused keys, audit archival)
- ~3,300 lines of code

**Features**:
- SSH key generation (RSA, Ed25519, ECDSA)
- Certificate lifecycle management
- ACME integration (Let's Encrypt, ZeroSSL)
- Automated SSH key distribution
- Certificate auto-renewal
- Credential audit logging
- Prometheus metrics

**Integration Points**:
- Standalone feature, no dependencies
- Provides credentials for BD-Store and Uptainer

See: [[Phase 1-2: KC-Booth Integration]]

### Phase 3: BD-Store (🔄 Ready)

**Status**: Detailed plan ready, awaiting implementation

**Scope**:
- 4 models (MonitoredServer, StorageDevice, StoragePool, DatabaseInstance)
- 10 services (server monitoring, storage, database discovery)
- ~50 API endpoints
- 1 scheduler task (5-minute metric collection)
- ~4,500-5,000 lines of code

**Features**:
- Server health monitoring (CPU, RAM, disk, uptime)
- SMART data collection and analysis
- ZFS pool monitoring
- mdadm RAID monitoring
- Database instance discovery (PostgreSQL, MySQL, MongoDB, Redis, MinIO)
- Automated metric collection
- Infrastructure alerts

**Integration Points**:
- Uses KC-Booth credentials (SSHKey, ServerCredential via FK)
- Extends Unity Alert model with infrastructure types
- Provides MonitoredServer for Uptainer

**Key Decisions**:
- Rename `Server` → `MonitoredServer` (avoid conflict with ServerProfile)
- Replace encrypted credentials with KC-Booth FKs
- Reuse Unity's SSH service
- Consolidate alerts into Unity Alert model

See: [[Phase 3: BD-Store Integration]]

### Phase 4: Uptainer (⏸️ Ready)

**Status**: Detailed plan ready, awaiting Phase 3 completion

**Scope**:
- 12+ models (ContainerHost, Container, UpdateHistory, UpdatePolicy, etc.)
- 15+ services (runtime providers, update engine, AI, security)
- ~60 API endpoints
- 5+ scheduler tasks (discovery, updates, scans, backups)
- ~7,000-8,000 lines of code

**Features**:
- Multi-runtime support (Docker, Podman, Kubernetes)
- AI-powered update recommendations
- Vulnerability scanning (Trivy)
- Update policies and maintenance windows
- Automated rollback on failure
- Container backup and restore
- Health validation
- Security scoring

**Integration Points**:
- Uses KC-Booth credentials for Docker/Podman/K8s
- Links ContainerHost to BD-Store MonitoredServer
- Extends Unity AI provider with container analysis
- Extends Unity notification service with container events

**Key Decisions**:
- Feature flags: ENABLE_K8S, ENABLE_TRIVY (opt-in)
- Runtime provider abstraction (Docker default)
- AI analysis uses Unity's existing ai_provider
- Container notifications use Unity's notification_service

See: [[Phase 4: Uptainer Integration]]

## Dependency Chain

```
KC-Booth (Credentials)
    ↓ provides SSH keys, certificates
BD-Store (Infrastructure)
    ↓ provides server inventory
Uptainer (Containers)
```

This chain ensures each phase builds on the previous one's infrastructure.

## Design Principles

### 1. Reusability Over Duplication
- **Reuse Unity models** where possible (Alert, User, NotificationLog)
- **Extend existing services** rather than duplicating
- **Share infrastructure** (database, scheduler, auth)

### 2. Conflict Resolution
- **Rename conflicts** (Server → MonitoredServer)
- **Consolidate similar models** (Alert types instead of separate models)
- **Foreign keys** to link features (ssh_key_id, monitored_server_id)

### 3. Feature Independence
- **Each feature is self-contained** in its service directory
- **Single router per feature** for clean API organization
- **Feature flags** for optional functionality

### 4. Production Readiness
- **Alembic migrations** for all schema changes
- **Docker deployment** tested at each phase
- **Comprehensive testing** before merge
- **Documentation** updated continuously

## Integration Benefits

### For Users
- **Single login** for all homelab management
- **Cross-feature workflows** (e.g., use SSH keys from KC-Booth in BD-Store)
- **Unified dashboards** showing all infrastructure
- **One deployment** to manage

### For Developers
- **Consistent patterns** across all features
- **Shared services** reduce duplication
- **Single database** simplifies queries
- **Unified testing** and deployment

### For Operations
- **One service to deploy**
- **Centralized logging** and metrics
- **Simplified backup** (single database)
- **Unified monitoring** and alerts

## Post-Integration Platform

After all 4 phases are complete:

| Metric | Value |
|--------|-------|
| Database Models | ~35-40 models |
| API Endpoints | ~200+ endpoints |
| Service Files | ~35-40 services |
| Scheduler Tasks | ~15-20 tasks |
| Codebase Size | ~18,000-20,000 LOC |
| Database Tables | ~40 tables |

## Integration Timeline

| Phase | Estimated Time | Complexity |
|-------|----------------|------------|
| Phase 1-2 (KC-Booth) | ✅ Complete | Medium |
| Phase 3 (BD-Store) | 11-15 hours | High |
| Phase 4 (Uptainer) | 22-30 hours | Very High |
| **Total** | **33-45 hours** | - |

## Success Criteria

Each integration phase must meet these criteria:

- ✅ All models added and relationships configured
- ✅ All services ported and tested
- ✅ All API endpoints working with authentication
- ✅ Scheduler tasks registered and running
- ✅ Alembic migration applied successfully
- ✅ Docker Compose deployment working
- ✅ No conflicts with existing features
- ✅ Documentation updated
- ✅ Committed and pushed to GitHub

## Learn More

- [[Integration Patterns]] - Detailed integration patterns and examples
- [[Phase 1-2: KC-Booth Integration]] - KC-Booth integration details
- [[Phase 3: BD-Store Integration]] - BD-Store integration plan
- [[Phase 4: Uptainer Integration]] - Uptainer integration plan
- [[Architecture Overview]] - System architecture

---

**See Also**: [[Quick Start Guide]] | [[Development Setup]]
