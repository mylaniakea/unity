# Phase 3 & 4 Detailed Integration Plans

## Overview

This document provides links to the detailed, step-by-step integration plans for the final two phases of Unity platform integration.

## Phase 3: BD-Store Infrastructure Monitoring

**Status**: Ready for implementation
**Plan ID**: `014755a6-2a00-4049-88e8-5d3a22ba9098`

### Summary
- **Scope**: ~4,500-5,000 LOC
- **Models**: 4 (MonitoredServer, StorageDevice, StoragePool, DatabaseInstance)
- **Services**: 10 files under `backend/app/services/infrastructure/`
- **Router**: 1 file with ~50 endpoints
- **Scheduler**: 1 collector task (5min intervals)
- **Timeline**: ~11-15 hours focused development
- **Complexity**: High

### Key Integration Points
1. Rename bd-store's `Server` → `MonitoredServer` (avoids conflict with Unity's ServerProfile)
2. Link to KC-Booth credentials via foreign keys (ssh_key_id, credential_id)
3. Extend Unity's Alert model with infrastructure alert types
4. Reuse Unity's SSH service for command execution
5. Consolidate into Unity's APScheduler

### Branch Strategy
- Source: `feature/kc-booth-integration`
- Target: `feature/bd-store-integration`
- Merge back to: `feature/kc-booth-integration`

## Phase 4: Uptainer Container Automation

**Status**: Ready for implementation (after Phase 3)
**Plan ID**: `a1a386b4-26b4-47c7-90de-9dbeddffb4a7`

### Summary
- **Scope**: ~7,000-8,000 LOC
- **Models**: 12+ (ContainerHost, Container, UpdateHistory, UpdatePolicy, MaintenanceWindow, VulnerabilityScan, ContainerVulnerability, UpdateNotification, ContainerBackup, AIRecommendation, RegistryCredential)
- **Services**: 15+ files under `backend/app/services/containers/`
- **Router**: 1 file with ~60 endpoints
- **Scheduler**: 5+ tasks (discovery, updates, scans, backups)
- **Timeline**: ~22-30 hours focused development
- **Complexity**: Very High

### Key Integration Points
1. Link ContainerHost to BD-Store's MonitoredServer via `monitored_server_id` FK
2. Extend Unity's `ai_provider` service with container update analysis
3. Extend Unity's `notification_service` with container event types
4. Runtime abstraction: Docker (default), Podman, K8s (feature-flagged)
5. Feature flags: ENABLE_K8S, ENABLE_TRIVY, ENABLE_CONTAINER_AI

### Branch Strategy
- Source: `feature/bd-store-integration` (after Phase 3 merge)
- Target: `feature/uptainer-integration`
- Merge back to: `feature/kc-booth-integration`
- Final merge: All phases → `main`

## Accessing the Plans

The detailed plans are stored in the Warp plan system and can be accessed via:
- **Phase 3 Plan**: Use Warp's plan viewer to view plan ID `014755a6-2a00-4049-88e8-5d3a22ba9098`
- **Phase 4 Plan**: Use Warp's plan viewer to view plan ID `a1a386b4-26b4-47c7-90de-9dbeddffb4a7`

Each plan contains:
- Step-by-step instructions with bash commands
- Complete model definitions with relationships
- Service implementation patterns and examples
- API router structure and endpoint patterns
- Scheduler task definitions
- Database migration steps
- Testing procedures
- Commit message templates
- Success criteria checklist
- Timeline estimates

## Integration Workflow

### Step 1: Review Plans
Read through Phase 3 and Phase 4 plans to understand scope and approach

### Step 2: Execute Phase 3
1. Create `feature/bd-store-integration` branch
2. Copy bd-store to staging: `unity/bd-store-staging/`
3. Follow Phase 3 plan step-by-step
4. Commit with detailed message (template in plan)
5. Test thoroughly
6. Merge back to `feature/kc-booth-integration`

### Step 3: Execute Phase 4
1. Create `feature/uptainer-integration` branch from updated `feature/kc-booth-integration`
2. Copy uptainer to staging: `unity/uptainer-staging/`
3. Follow Phase 4 plan step-by-step
4. Commit with detailed message (template in plan)
5. Test thoroughly
6. Merge back to `feature/kc-booth-integration`

### Step 4: Final Validation
1. Full integration testing on `feature/kc-booth-integration`
2. Verify all 4 phases work together
3. Run complete test suite
4. Check Docker Compose deployment
5. Validate all ~200+ API endpoints

### Step 5: Production Merge
1. Create PR: `feature/kc-booth-integration` → `main`
2. Code review
3. Final testing
4. Merge to main
5. Tag release: `v1.0.0-complete-integration`

## Post-Integration Platform Stats

After completing all 4 phases:

- **Total Models**: ~35-40 across 4 domains
- **Total Services**: ~35-40 service files
- **Total API Endpoints**: ~200+ endpoints in 12-15 routers
- **Total Scheduler Tasks**: ~15-20 background jobs
- **Total Codebase**: ~18,000-20,000 lines (backend)
- **Database Tables**: ~40 in single PostgreSQL
- **Docker Services**: 3 (postgres, backend, frontend)

## Feature Domains

1. **Core Platform**: Auth, users, plugins, metrics, alerts, notifications
2. **Credentials (KC-Booth)**: SSH keys, certificates, server credentials, ACME renewal, distribution
3. **Infrastructure (BD-Store)**: Server monitoring, storage (SMART/ZFS/RAID), database discovery
4. **Containers (Uptainer)**: Multi-runtime updates, AI recommendations, security scanning, backup

## Support Documentation

See also:
- `INTEGRATION-REVIEW.md` - Executive summary and integration order
- `INTEGRATION-SCOPE-COMPARISON.md` - Detailed scope comparison of all phases
- `INTEGRATION-ARCHITECTURE.md` - System architecture diagrams
- `INTEGRATION-SUMMARY.md` - Integration playbook and patterns
- `INTEGRATION-QUICK-REFERENCE.md` - Developer cheat sheet

## Notes

- Keep staging directories (`bd-store-staging/`, `uptainer-staging/`) for reference
- Do NOT modify original projects in `/home/matthew/projects/HI/bd-store` or `/home/matthew/projects/HI/uptainer`
- Follow KC-Booth integration patterns consistently
- Test each phase independently before moving to next
- Document any deviations from plans in commit messages
- Update this document if plans change

---

**Created**: December 15, 2024
**Last Updated**: December 15, 2024
**Status**: Phase 3 & 4 plans complete and ready for execution
