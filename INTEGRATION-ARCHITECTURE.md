# Unity Platform Integration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UNITY PLATFORM                                  │
│                  Unified Homelab Infrastructure Monitoring              │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │  KC-BOOTH    │      │  BD-STORE    │      │  UPTAINER    │
    │ Credentials  │──────│Infrastructure│──────│  Containers  │
    │   Phase 1-2  │      │   Phase 3    │      │   Phase 4    │
    │ ✅ COMPLETE  │      │ 🔄 NEXT      │      │ ⏸️  WAITING  │
    └──────────────┘      └──────────────┘      └──────────────┘
```

## Dependency Flow

```
KC-Booth (Credentials)
    │
    ├─ Provides: SSH Keys, Certificates, Server Credentials
    │
    ▼
BD-Store (Infrastructure)
    │
    ├─ Uses: SSH Keys for server access
    ├─ Provides: Server inventory, storage monitoring, database discovery
    │
    ▼
Uptainer (Containers)
    │
    ├─ Uses: Server inventory from BD-Store
    ├─ Uses: Credentials from KC-Booth for Docker/Podman/K8s
    └─ Provides: Container update automation
```

## Database Schema Integration

```
Unity Core Models:
├─ User
├─ Plugin / PluginMetric / PluginExecution / PluginAPIKey
├─ Alert / AlertChannel / NotificationLog
├─ ServerProfile (templates)
├─ Settings / Report / KnowledgeItem / ServerSnapshot / ThresholdRule
└─ PushSubscription

Phase 1-2: KC-Booth Models (✅ COMPLETE)
├─ SSHKey
├─ Certificate
├─ ServerCredential
├─ StepCAConfig
└─ CredentialAuditLog

Phase 3: BD-Store Models (🔄 NEXT)
├─ MonitoredServer ─────┐
│   ├─ FK: ssh_key_id (→ SSHKey)
│   └─ FK: credential_id (→ ServerCredential)
│
├─ StorageDevice
│   └─ FK: server_id (→ MonitoredServer)
│
├─ StoragePool
│   └─ FK: server_id (→ MonitoredServer)
│
└─ DatabaseInstance
    └─ FK: server_id (→ MonitoredServer)

Phase 4: Uptainer Models (⏸️ WAITING)
├─ ContainerHost ────────┐
│   ├─ FK: monitored_server_id (→ MonitoredServer)
│   └─ FK: credential_id (→ ServerCredential / RegistryCredential)
│
├─ Container
│   └─ FK: host_id (→ ContainerHost)
│
├─ UpdateHistory
│   └─ FK: container_id (→ Container)
│
├─ UpdatePolicy
├─ MaintenanceWindow
│   └─ FK: policy_id (→ UpdatePolicy)
│
├─ VulnerabilityScan
│   └─ FK: container_id (→ Container)
│
├─ ContainerVulnerability
│   └─ FK: scan_id (→ VulnerabilityScan)
│
├─ UpdateNotification
│   └─ FK: container_id (→ Container)
│
├─ ContainerBackup
│   └─ FK: container_id (→ Container)
│
├─ AIRecommendation
│   └─ FK: container_id (→ Container)
│
└─ RegistryCredential
```

## Service Layer Architecture

```
backend/app/services/
│
├─ Core Services (Original Unity)
│  ├─ auth.py
│  ├─ encryption.py
│  ├─ ai_provider.py ◄─── Extended by Uptainer
│  ├─ ai.py
│  ├─ alert_channels.py
│  ├─ notification_service.py ◄─── Extended by Uptainer
│  ├─ plugin_manager.py
│  ├─ plugin_registry.py
│  ├─ plugin_security.py
│  ├─ push_notifications.py
│  ├─ report_generation.py
│  ├─ snapshot_service.py
│  ├─ ssh.py ◄─── Used by BD-Store
│  ├─ system_info.py
│  └─ threshold_monitor.py
│
├─ credentials/ (Phase 1-2 ✅)
│  ├─ encryption.py
│  ├─ ssh_keys.py
│  ├─ certificates.py
│  ├─ server_credentials.py
│  ├─ audit.py
│  ├─ distribution.py
│  ├─ cert_providers.py
│  └─ metrics.py
│
├─ infrastructure/ (Phase 3 🔄)
│  ├─ server_monitor.py
│  ├─ storage_monitor.py
│  ├─ database_discovery.py
│  ├─ ssh_executor.py
│  ├─ smart_analyzer.py
│  ├─ zfs_manager.py
│  ├─ raid_manager.py
│  ├─ collector_scheduler.py
│  ├─ alert_manager.py
│  └─ metrics.py
│
└─ containers/ (Phase 4 ⏸️)
   ├─ runtime/
   │  ├─ base_provider.py
   │  ├─ docker_provider.py
   │  ├─ podman_provider.py
   │  └─ k8s_provider.py
   ├─ update_executor.py
   ├─ update_checker.py
   ├─ policy_engine.py
   ├─ ai_analyzer.py
   ├─ registry_client.py
   ├─ container_monitor.py
   ├─ backup_service.py
   ├─ health_validator.py
   ├─ notification_service.py
   ├─ security_scanner.py
   ├─ version_control.py
   └─ metrics.py
```

## API Router Structure

```
backend/app/routers/
│
├─ Core Routers (Original Unity)
│  ├─ auth.py
│  ├─ users.py
│  ├─ plugins.py / plugins_v2.py / plugins_v2_secure.py
│  ├─ plugin_keys.py
│  ├─ profiles.py
│  ├─ reports.py
│  ├─ settings.py
│  ├─ system.py
│  ├─ terminal.py
│  ├─ thresholds.py
│  ├─ alerts.py ◄─── Extended with infrastructure/container alert types
│  ├─ ai.py ◄─── Extended with container analysis
│  ├─ knowledge.py
│  └─ push.py
│
├─ credentials.py (Phase 1-2 ✅)
│  └─ 37 endpoints: SSH keys, certs, server credentials, distribution, renewal, metrics
│
├─ infrastructure.py (Phase 3 🔄)
│  └─ ~50 endpoints: servers, storage, databases, health, scheduler, alerts
│
└─ containers.py (Phase 4 ⏸️)
   └─ ~60 endpoints: hosts, containers, updates, policies, schedules, security, AI, notifications, backups
```

## Scheduler Tasks

```
backend/app/schedulers/

Phase 1-2: credential_tasks.py (✅)
├─ check_certificate_expiry() - daily
├─ check_unused_ssh_keys() - weekly
└─ archive_old_audit_logs() - monthly

Phase 3: infrastructure_tasks.py (🔄)
└─ collect_server_metrics() - 5min default, per-server configurable
    ├─ Collect system metrics (CPU, RAM, disk)
    ├─ SMART data for storage devices
    ├─ ZFS/RAID pool status
    └─ Database health checks

Phase 4: container_tasks.py (⏸️)
├─ discover_containers() - 15min
├─ check_container_updates() - 1h
├─ execute_scheduled_updates() - cron-based per policy
├─ scan_vulnerabilities() - daily
└─ backup_containers() - per backup policy
```

## Integration Checklist Per Phase

### Phase 3: BD-Store
- [ ] Create `feature/bd-store-integration` branch
- [ ] Copy bd-store to staging: `unity/bd-store-staging/`
- [ ] Merge 4 models into `backend/app/models.py` (MonitoredServer, StorageDevice, StoragePool, DatabaseInstance)
- [ ] Extend Unity Alert model with infrastructure alert types
- [ ] Create 10 service files under `backend/app/services/infrastructure/`
- [ ] Create `backend/app/routers/infrastructure.py` (~50 endpoints)
- [ ] Create `backend/app/schedulers/infrastructure_tasks.py`
- [ ] Generate Alembic migration
- [ ] Test with Docker Compose
- [ ] Push to GitHub
- [ ] Merge to main

### Phase 4: Uptainer
- [ ] Create `feature/uptainer-integration` branch
- [ ] Copy uptainer to staging: `unity/uptainer-staging/`
- [ ] Merge 12+ models into `backend/app/models.py`
- [ ] Link ContainerHost.monitored_server_id → MonitoredServer
- [ ] Extend Unity ai_provider with container analysis prompts
- [ ] Extend Unity notification_service with container event types
- [ ] Create 15+ service files under `backend/app/services/containers/`
- [ ] Create `backend/app/routers/containers.py` (~60 endpoints)
- [ ] Create `backend/app/schedulers/container_tasks.py`
- [ ] Add feature flags: ENABLE_K8S, ENABLE_TRIVY
- [ ] Generate Alembic migration
- [ ] Test with Docker Compose
- [ ] Push to GitHub
- [ ] Merge to main

## Final Platform Stats

Post-Integration (All 4 Phases Complete):
- **Models**: ~35-40 tables
- **Services**: ~35-40 service files
- **API Endpoints**: ~200+ endpoints across 12-15 routers
- **Background Tasks**: ~15-20 scheduled tasks
- **Codebase Size**: ~18,000-20,000 lines (backend)
- **Database**: Single PostgreSQL with ~40 tables
- **Docker Services**: 3 (postgres, backend, frontend)
