# Integration Scope: KC-Booth vs BD-Store vs Uptainer

## KC-Booth Integration (COMPLETED - Phase 1 & 2)

**Complexity**: Medium
**Status**: ✅ 100% Complete

### Stats
- Models: 5 (SSHKey, Certificate, ServerCredential, StepCAConfig, CredentialAuditLog)
- Services: 5 files (encryption, ssh_keys, certificates, server_credentials, audit, distribution, cert_providers, metrics)
- Routers: 1 file, 37 endpoints
- Scheduler: 3 tasks (cert expiry, unused keys, audit archival)
- Lines added: ~3,300
- Commits: 30+

### Integration Approach
- Monolithic: All models merged into Unity's models.py
- Services under backend/app/services/credentials/
- Single router: backend/app/routers/credentials.py
- Hooks into Unity's APScheduler
- Uses Unity's PostgreSQL database
- Full CRUD + automation (SSH distribution, ACME renewal)

---

## BD-Store Integration (Phase 3 - NEXT)

**Complexity**: High
**Status**: 🔄 Not Started

### Stats (Estimated)
- Models: 4 (MonitoredServer, StorageDevice, StoragePool, DatabaseInstance)
- Reuse Unity models: Alert, AlertChannel (extend types)
- Services: ~8-10 files (server_monitor, storage_monitor, database_discovery, ssh_executor, smart_analyzer, zfs_manager, raid_manager, collector_scheduler, alert_manager)
- Routers: 1 file "infrastructure.py", ~50 endpoints
- Scheduler: 1 collector task (5min default, per-server configurable)
- Lines to add: ~4,500-5,000

### Integration Approach
- Monolithic: Merge models into Unity's models.py
- Services under backend/app/services/infrastructure/
- Single router: backend/app/routers/infrastructure.py
- Replace bd-store's encrypted SSH credentials with references to KC-Booth ServerCredential/SSHKey
- Reuse Unity's Alert system (add "server_offline", "storage_warning", "database_unreachable" types)
- Use Unity's existing SSH service + add infrastructure-specific SSH wrappers
- Consolidate scheduling into Unity's APScheduler

### Key Dependencies
- Requires: KC-Booth (for SSH/credentials)
- Provides: Server inventory for Uptainer

### Conflicts/Overlaps
- BD-Store Alert ↔ Unity Alert: **Merge into Unity Alert** (add severity, alert_type fields if missing)
- BD-Store Server ↔ Unity ServerProfile: **Rename to MonitoredServer**, distinct from ServerProfile (profiles are templates, MonitoredServers are actual infrastructure)
- BD-Store health endpoints ↔ Unity system endpoints: **Keep separate** (BD-Store health checks infrastructure, Unity checks app health)

---

## Uptainer Integration (Phase 4 - FINAL)

**Complexity**: Very High
**Status**: ⏸️ Waiting for Phase 3

### Stats (Estimated)
- Models: 12+ (ContainerHost, Container, UpdateHistory, UpdatePolicy, MaintenanceWindow, VulnerabilityScan, ContainerVulnerability, UpdateNotification, ContainerBackup, AIRecommendation, RegistryCredential, RuntimeProvider)
- Services: 15+ files (runtime providers: docker_provider, podman_provider, k8s_provider; update_executor, update_checker, policy_engine, ai_analyzer, registry_client, container_monitor, backup_service, health_validator, notification_service, security_scanner, version_control)
- Routers: 1 file "containers.py", ~60 endpoints
- Scheduler: 5+ tasks (discovery 15m, update_check 1h, scheduled_updates cron-based, vulnerability_scan daily, backup per-policy)
- Lines to add: ~7,000-8,000

### Integration Approach
- Monolithic: Merge models into Unity's models.py
- Services under backend/app/services/containers/
- Single router: backend/app/routers/containers.py
- Link ContainerHost → MonitoredServer (from BD-Store Phase 3)
- Merge Uptainer's AI into Unity's existing ai_provider service (add container-specific prompts/flows)
- Reuse Unity NotificationLog + add container notification types
- Feature flags: ENABLE_K8S=false, ENABLE_TRIVY=false (optional features)
- Runtime abstraction: docker is default, podman/k8s opt-in

### Key Dependencies
- Requires: KC-Booth (credentials for Docker/Podman/K8s), BD-Store (server inventory)
- Provides: Complete homelab automation

### Conflicts/Overlaps
- Uptainer AI ↔ Unity AI: **Merge** (uptainer adds container update analysis; unity has general AI)
- Uptainer NotificationService ↔ Unity notification_service: **Extend Unity's** (add container event types)
- Uptainer ContainerHost ↔ BD-Store MonitoredServer: **Link via FK** (container host references monitored server)

---

## Integration Pattern Summary

All three follow the same monolithic integration pattern established by KC-Booth:

1. Copy staging version of source project
2. Merge models into Unity's models.py (rename conflicts, add FKs to link features)
3. Create service modules under backend/app/services/{feature}/
4. Create single router file under backend/app/routers/{feature}.py
5. Wire scheduler tasks into Unity's APScheduler (backend/app/schedulers/{feature}_tasks.py)
6. Consolidate into Unity's single PostgreSQL database
7. Generate Alembic migration per feature
8. Test with Docker Compose
9. Push to feature branch
10. Merge to main after validation

## Total Unity Platform Size (Post-Integration)

- Models: ~35-40 models (User, Plugin, Alert, Credential suite, Infrastructure suite, Container suite)
- Services: ~35-40 service files across 4 domains (core, credentials, infrastructure, containers)
- Routers: ~12-15 routers (~200+ total endpoints)
- Scheduler: ~15-20 background tasks
- Total codebase: ~18,000-20,000 lines (backend only, excluding frontend)
- Database: Single PostgreSQL with ~40 tables
