# BD-Store & Uptainer Integration Review

## Executive Summary

After successfully completing KC-Booth credential management integration (100% feature parity, 3,300+ lines, 37 endpoints), we now have two remaining projects to integrate:

1. BD-Store - Infrastructure monitoring backend (servers, storage, databases)
2. Uptainer - Automated container update management

## Proposed Integration Order

Phase 3: BD-Store → Phase 4: Uptainer

Rationale: KC-Booth → BD-Store → Uptainer dependency chain. BD-Store provides server inventory and SSH connectivity that Uptainer builds on.

## BD-Store Integration Summary

- Models to add: MonitoredServer (renamed), StorageDevice, StoragePool, DatabaseInstance
- Reuse Unity Alert/AlertChannel; map BD-Store alerts to Unity Alert types
- Services: server monitoring, storage monitoring (SMART/ZFS/RAID), database discovery, data collector, alert manager, SSH executor
- Routers: /api/v1/infrastructure/servers, /storage, /databases, /alerts, /scheduler, /health
- Scheduler: 5-min server collection; configurable per server
- Credentials: reference KC-Booth SSHKey/ServerCredential instead of storing encrypted creds

## Uptainer Integration Summary

- Models to add: ContainerHost, Container, UpdateHistory, UpdatePolicy, MaintenanceWindow, VulnerabilityScan, ContainerVulnerability, UpdateNotification, ContainerBackup, AIRecommendation, RegistryCredential (+runtime provider mapping)
- Link: ContainerHost.monitored_server_id → MonitoredServer.id
- Services: runtime providers (docker/podman/k8s), update executor/checker, policy engine, AI analyzer, registry client, container monitor, backup, security (Trivy)
- Routers: /api/v1/containers (hosts, containers, updates, policies, schedules, security, ai, notifications, settings, backups)
- Scheduler: discovery (15m), update checks (1h), scheduled updates (cron), scans (daily), backups (configurable)
- AI: use Unity ai_provider; add uptainer-specific prompts and flows

## Design Decisions

1) Consolidate alerts under Unity's Alert model; add types for infrastructure/container events
2) Use single Postgres DB and Alembic history; generate migrations per feature module
3) Centralize scheduling in Unity's APScheduler
4) Feature-flag vulnerability scanning (Trivy) and Kubernetes support
5) Keep runtime provider abstraction for future extensibility

## Open Questions

- Extend Alert vs subtype? (recommend extend)
- Merge AI providers vs keep separate? (recommend merge)
- API versioning: keep under /api/v1 for now
- Frontend scope for dashboards and controls?

## Next Steps

- Approve this outline
- I’ll produce two detailed integration plans (Phase 3 BD-Store, Phase 4 Uptainer)
- Then implement Phase 3 first, followed by Phase 4
