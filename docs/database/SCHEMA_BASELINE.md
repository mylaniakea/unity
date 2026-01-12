# Unity Database Schema Baseline
**Date:** $(date +%Y-%m-%d)
**Database:** PostgreSQL 16
**Purpose:** Multi-tenancy Control Plane

## Schema Overview

This document captures the current production schema state before implementing:
- Alembic migrations for version control
- Multi-tenancy with tenant_id columns
- Kubernetes orchestration enhancements

## Tables Summary (25 total)

### Authentication & Authorization
- **users** (80 kB) - User accounts with RBAC
- **plugin_api_keys** (40 kB) - API keys for plugin authentication

### Credential Management
- **ssh_keys** (32 kB) - SSH key storage with encryption
- **certificates** (32 kB) - TLS/SSL certificate management
- **server_credentials** (32 kB) - Server access credentials
- **credential_audit_logs** (48 kB) - Audit trail for credential access
- **step_ca_config** (16 kB) - Step CA configuration

### Kubernetes Orchestration
- **kubernetes_clusters** (48 kB) - K8s cluster registry
- **kubernetes_resources** (88 kB) - K8s resource definitions
- **deployment_intents** (64 kB) - Declarative deployment specifications
- **application_blueprints** (56 kB) - Application templates
- **resource_reconciliations** (48 kB) - Reconciliation tracking

### Server Management
- **server_profiles** (80 kB) - Server inventory and profiles
- **server_snapshots** (32 kB) - Point-in-time server state

### Plugin System
- **plugins** (32 kB) - Plugin registry
- **plugin_executions** (40 kB) - Plugin execution history
- **plugin_metrics** (0 bytes, PARTITIONED) - Time-series metrics data

### Monitoring & Alerts
- **alerts** (56 kB) - Alert definitions and state
- **alert_channels** (40 kB) - Notification channel configuration
- **threshold_rules** (48 kB) - Metric threshold definitions
- **notification_logs** (40 kB) - Notification delivery tracking

### Knowledge & Reporting
- **knowledge** (40 kB) - Knowledge base articles
- **reports** (56 kB) - Generated reports
- **push_subscriptions** (32 kB) - Web push notification subscriptions

### Configuration
- **settings** (48 kB) - Application configuration

## Key Schema Features

### Partitioning
- `plugin_metrics` table uses PostgreSQL partitioning for time-series data

### Encryption at Rest
- SSH keys encrypted via ENCRYPTION_KEY environment variable
- Credential fields use cryptography library

### JSONB Usage
- Several tables use JSONB for flexible metadata storage
- Plugin configurations and metrics stored as JSONB

## Multi-Tenancy Gaps (Pre-Implementation)

⚠️ **Current Limitations:**
- No tenant_id column on any table
- No row-level security (RLS) policies
- Single database schema for all users
- No tenant-scoped resource isolation
- Credentials not tenant-isolated

## Next Steps

1. ✅ Schema baseline captured
2. ⏳ Generate Alembic migration for current state
3. ⏳ Design tenant_id migration strategy
4. ⏳ Implement multi-tenancy isolation
5. ⏳ Add RLS policies
6. ⏳ Update application logic for tenant context

---
Generated: $(date)
Schema file: schema_baseline_$(date +%Y%m%d).sql
