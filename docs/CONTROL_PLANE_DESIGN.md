# Unity: Multi-Tenant SaaS Control Plane - Architecture Design

**Vision:** Transform Unity from single-tenant homelab manager into a production-grade, multi-tenant Kubernetes control plane with API-first reliability.

**Strategy:** Keep all existing features, add tenant isolation layer, enhance for production scale.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TENANT BOUNDARY LAYER                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Tenant A │  │ Tenant B │  │ Tenant C │  │ Tenant N │               │
│  │ (Demo)   │  │ (Prod)   │  │ (Dev)    │  │ (...)    │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │             │             │             │                        │
│       └─────────────┴─────────────┴─────────────┘                        │
│                          │                                               │
└──────────────────────────┼───────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Authentication & Authorization                                    │   │
│  │  - JWT with tenant_id claim                                      │   │
│  │  - API Key with tenant scope                                     │   │
│  │  - RBAC: tenant-admin, tenant-member, tenant-viewer              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Rate Limiting & Quotas                                           │   │
│  │  - Per-tenant API rate limits                                    │   │
│  │  - Resource quota enforcement                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Tenant Context Middleware                                        │   │
│  │  - Extract tenant_id from token                                  │   │
│  │  - Inject into request.state                                     │   │
│  │  - Audit logging                                                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      UNITY CORE SERVICES                                 │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   K8s API    │  │ Orchestration│  │  Monitoring  │                  │
│  │              │  │              │  │              │                  │
│  │ • Clusters   │  │ • Blueprints │  │ • Plugins    │                  │
│  │ • Resources  │  │ • Intents    │  │ • Metrics    │                  │
│  │ • Reconcile  │  │ • Deploy     │  │ • Alerts     │                  │
│  │ • Health     │  │ • Auto-wire  │  │ • Thresholds │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Credentials  │  │     AI       │  │   Reports    │                  │
│  │              │  │              │  │              │                  │
│  │ • SSH Keys   │  │ • Insights   │  │ • Generation │                  │
│  │ • Certs      │  │ • Chat       │  │ • Snapshots  │                  │
│  │ • Secrets    │  │ • Summary    │  │ • History    │                  │
│  │ • Audit      │  │ • Knowledge  │  │ • Analytics  │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Terminal   │  │ Notifications│  │   Settings   │                  │
│  │              │  │              │  │              │                  │
│  │ • SSH        │  │ • Channels   │  │ • Profiles   │                  │
│  │ • WebSocket  │  │ • Push       │  │ • Config     │                  │
│  │ • Multi-Host │  │ • Email/Slack│  │ • Preferences│                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
│  ALL SERVICES FILTER BY: WHERE tenant_id = request.state.tenant_id      │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       DATA PERSISTENCE LAYER                             │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              PostgreSQL (Multi-Tenant Database)                  │    │
│  │                                                                  │    │
│  │  ┌───────────────────────────────────────────────────────┐      │    │
│  │  │ public schema                                         │      │    │
│  │  │  • tenants (id, name, plan, status, quotas)          │      │    │
│  │  │  • user_tenant_memberships (user_id, tenant_id, role)│      │    │
│  │  │  • alembic_version (migration tracking)              │      │    │
│  │  └───────────────────────────────────────────────────────┘      │    │
│  │                                                                  │    │
│  │  ┌───────────────────────────────────────────────────────┐      │    │
│  │  │ tenant-scoped tables (all 25 existing tables)        │      │    │
│  │  │  • users (tenant_id, ...)                            │      │    │
│  │  │  • kubernetes_clusters (tenant_id, ...)              │      │    │
│  │  │  • plugins (tenant_id, ...)                          │      │    │
│  │  │  • credentials (tenant_id, ...)                      │      │    │
│  │  │  • alerts (tenant_id, ...)                           │      │    │
│  │  │  • ... (22 more tables, all with tenant_id)          │      │    │
│  │  │                                                       │      │    │
│  │  │  INDEXES: idx_<table>_tenant ON (tenant_id)          │      │    │
│  │  │  RLS POLICIES: WHERE tenant_id = current_setting()   │      │    │
│  │  └───────────────────────────────────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES ORCHESTRATION LAYER                        │
│                                                                          │
│  ┌──────────────────────┐    ┌──────────────────────┐                  │
│  │  Tenant A Namespace  │    │  Tenant B Namespace  │                  │
│  │  (tenant-alpha)      │    │  (tenant-bravo)      │                  │
│  │                      │    │                      │                  │
│  │  • ResourceQuota     │    │  • ResourceQuota     │                  │
│  │  • NetworkPolicy     │    │  • NetworkPolicy     │                  │
│  │  • RoleBindings      │    │  • RoleBindings      │                  │
│  │  • Deployments       │    │  • Deployments       │                  │
│  │  • Services          │    │  • Services          │                  │
│  │  • Ingress           │    │  • Ingress           │                  │
│  │                      │    │                      │                  │
│  │  Labels:             │    │  Labels:             │                  │
│  │   tenant-id: alpha   │    │   tenant-id: bravo   │                  │
│  │   managed-by: unity  │    │   managed-by: unity  │                  │
│  └──────────────────────┘    └──────────────────────┘                  │
│                                                                          │
│  Unity manages tenant namespaces, enforces quotas, reconciles state     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tenant Isolation Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         TENANT ISOLATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  DATABASE LEVEL (Row-Level Security)                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Every query automatically filtered:                    │     │
│  │   SELECT * FROM clusters WHERE tenant_id = 'alpha'     │     │
│  │                                                         │     │
│  │ Enforced by:                                           │     │
│  │  1. Application middleware (request.state.tenant_id)   │     │
│  │  2. PostgreSQL RLS policies (defense in depth)         │     │
│  │  3. Index on tenant_id (performance)                   │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  KUBERNETES LEVEL (Namespace Isolation)                         │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Each tenant gets:                                      │     │
│  │  • Dedicated namespace: tenant-{tenant_id}             │     │
│  │  • ResourceQuota: CPU, memory, storage limits          │     │
│  │  • NetworkPolicy: No cross-tenant traffic              │     │
│  │  • RBAC: Unity ServiceAccount per namespace            │     │
│  │  • Label selector: tenant-id={tenant_id}               │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  API LEVEL (Authentication & Authorization)                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ JWT Token includes:                                    │     │
│  │  {                                                     │     │
│  │    "sub": "user@example.com",                         │     │
│  │    "tenant_id": "alpha",                              │     │
│  │    "role": "tenant-admin"                             │     │
│  │  }                                                     │     │
│  │                                                         │     │
│  │ API Key format:                                        │     │
│  │  uk_alpha_7x9k2m...  (tenant_id embedded)             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  CREDENTIALS LEVEL (Encryption + Scoping)                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ • SSH keys encrypted with tenant-specific KEK          │     │
│  │ • Certificates scoped to tenant_id                     │     │
│  │ • Audit log on every credential access                 │     │
│  │ • No cross-tenant credential sharing                   │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Request Flow (Multi-Tenant)

```
1. Client Request
   ┌────────────────────────────────────────────┐
   │ POST /api/k8s/clusters                     │
   │ Authorization: Bearer eyJ0eXAi...          │
   │                                            │
   │ {                                          │
   │   "name": "prod-cluster",                  │
   │   "kubeconfig": "..."                      │
   │ }                                          │
   └────────────────┬───────────────────────────┘
                    │
                    ▼
2. API Gateway
   ┌────────────────────────────────────────────┐
   │ • Verify JWT signature                     │
   │ • Extract tenant_id from token             │
   │   → tenant_id = "alpha"                    │
   │ • Check API rate limit for tenant          │
   │ • Inject tenant_id into request.state      │
   └────────────────┬───────────────────────────┘
                    │
                    ▼
3. Service Layer (k8s_router.py)
   ┌────────────────────────────────────────────┐
   │ async def create_cluster(                  │
   │     cluster: ClusterCreate,                │
   │     db: Session = Depends(get_db),         │
   │     tenant_id: str = Depends(get_tenant)   │
   │ ):                                         │
   │     # Create cluster scoped to tenant      │
   │     new_cluster = KubernetesCluster(       │
   │         tenant_id=tenant_id,  # INJECTED   │
   │         name=cluster.name,                 │
   │         ...                                │
   │     )                                      │
   │     db.add(new_cluster)                    │
   │     db.commit()                            │
   └────────────────┬───────────────────────────┘
                    │
                    ▼
4. Database Query (Auto-Filtered)
   ┌────────────────────────────────────────────┐
   │ INSERT INTO kubernetes_clusters            │
   │   (tenant_id, name, kubeconfig, ...)       │
   │ VALUES                                     │
   │   ('alpha', 'prod-cluster', '...', ...)    │
   │                                            │
   │ SELECT * FROM kubernetes_clusters          │
   │  WHERE tenant_id = 'alpha'                 │
   │    AND id = 123                            │
   └────────────────┬───────────────────────────┘
                    │
                    ▼
5. K8s Orchestration
   ┌────────────────────────────────────────────┐
   │ • Connect to cluster                       │
   │ • Create namespace: tenant-alpha           │
   │ • Apply ResourceQuota                      │
   │ • Apply NetworkPolicy                      │
   │ • Label all resources with tenant-id       │
   └────────────────┬───────────────────────────┘
                    │
                    ▼
6. Response
   ┌────────────────────────────────────────────┐
   │ {                                          │
   │   "id": 123,                               │
   │   "tenant_id": "alpha",                    │
   │   "name": "prod-cluster",                  │
   │   "status": "healthy",                     │
   │   "namespace": "tenant-alpha"              │
   │ }                                          │
   └────────────────────────────────────────────┘
```

---

## Tenant Lifecycle Management

```
┌──────────────────────────────────────────────────────────────────┐
│                      TENANT PROVISIONING                          │
└──────────────────────────────────────────────────────────────────┘

1. Create Tenant (Platform Admin)
   POST /api/v1/tenants
   {
     "id": "acme-corp",
     "name": "Acme Corporation",
     "plan": "enterprise",
     "resource_quota": {
       "kubernetes_clusters": 10,
       "cpu_cores": 100,
       "memory_gb": 256,
       "storage_gb": 1000,
       "api_calls_per_hour": 100000
     }
   }
   
   ▼
   
   Database Operations:
   • INSERT INTO tenants (...)
   • INSERT default admin user
   • Generate initial API key
   
   ▼
   
   Kubernetes Operations:
   • Create namespace: tenant-acme-corp
   • Apply ResourceQuota
   • Apply NetworkPolicy (isolate from other tenants)
   • Create ServiceAccount: unity-acme-corp
   • Create RoleBinding (namespace-admin)

   ▼
   
   Response:
   {
     "tenant_id": "acme-corp",
     "status": "active",
     "api_key": "uk_acme_corp_...",
     "admin_email": "admin@acme-corp.com",
     "admin_password": "<generated>",
     "namespace": "tenant-acme-corp"
   }


2. Invite User to Tenant (Tenant Admin)
   POST /api/v1/tenants/acme-corp/members
   {
     "email": "engineer@acme-corp.com",
     "role": "member"
   }
   
   ▼
   
   • Send invitation email
   • User signs up / accepts
   • INSERT INTO user_tenant_memberships
   • User JWT now includes tenant_id: "acme-corp"


3. Suspend Tenant (Platform Admin)
   POST /api/v1/tenants/acme-corp/suspend
   
   ▼
   
   • UPDATE tenants SET status='suspended'
   • Block all API calls (middleware check)
   • Scale down K8s resources (optional)
   • Send notification


4. Delete Tenant (Platform Admin)
   DELETE /api/v1/tenants/acme-corp
   
   ▼
   
   Soft Delete (Recommended):
   • UPDATE tenants SET status='deleted', deleted_at=NOW()
   • Retain data for 30 days
   • Block all access
   
   Hard Delete (After grace period):
   • DELETE FROM all tables WHERE tenant_id='acme-corp'
   • kubectl delete namespace tenant-acme-corp
   • Delete backups
```

---

## Resource Quota Enforcement

```
┌──────────────────────────────────────────────────────────────────┐
│                    PER-TENANT QUOTAS                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Quota Definition (stored in tenants.resource_quota JSONB):      │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ {                                                        │     │
│  │   "kubernetes_clusters": 10,      // Max K8s clusters   │     │
│  │   "plugins": 50,                  // Max plugins        │     │
│  │   "users": 100,                   // Max users          │     │
│  │   "api_calls_per_hour": 10000,    // Rate limit         │     │
│  │   "cpu_cores": 50,                // Total CPU          │     │
│  │   "memory_gb": 128,               // Total RAM          │     │
│  │   "storage_gb": 500,              // Total storage      │     │
│  │   "ssh_keys": 100,                // Max SSH keys       │     │
│  │   "certificates": 50              // Max certs          │     │
│  │ }                                                        │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                   │
│  Enforcement Points:                                              │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ 1. API Layer (before creating resource)                 │     │
│  │    if count(clusters, tenant_id) >= quota.clusters:     │     │
│  │        return 429 "Quota exceeded"                       │     │
│  │                                                          │     │
│  │ 2. Kubernetes (ResourceQuota in namespace)              │     │
│  │    apiVersion: v1                                       │     │
│  │    kind: ResourceQuota                                  │     │
│  │    spec:                                                │     │
│  │      hard:                                              │     │
│  │        requests.cpu: "50"                               │     │
│  │        requests.memory: 128Gi                           │     │
│  │        persistentvolumeclaims: "10"                     │     │
│  │                                                          │     │
│  │ 3. Rate Limiting (middleware)                            │     │
│  │    Redis: INCR tenant:alpha:api_calls:2026-01-05:12     │     │
│  │    if value > 10000/hour: return 429                    │     │
│  └─────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Migration Path (Keeping Everything)

```
PHASE 1: Add Tenant Infrastructure (Week 1-2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ COMPLETED (this session):
  • Alembic migrations baseline
  • Backup/restore scripts
  • Multi-tenancy strategy doc
  • Helm chart skeleton

🔨 TODO:
  1. Generate migration: add tenant_id to all 25 tables
  2. Create tenants table
  3. Create user_tenant_memberships table
  4. Apply migration
  5. Test with backup/restore


PHASE 2: Application Logic (Week 2-3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Tenant context middleware
     • Extract tenant_id from JWT/API key
     • Inject into request.state
     • Add to all log messages

  2. Update ALL queries (25 tables × ~10 queries each)
     • Add .filter(Model.tenant_id == tenant_id)
     • Update create operations to include tenant_id
     • Add audit logging

  3. Tenant management API
     • POST /api/v1/tenants (create)
     • GET /api/v1/tenants (list - admin only)
     • PATCH /api/v1/tenants/{id} (update)
     • POST /api/v1/tenants/{id}/suspend (suspend)
     • User invitation system


PHASE 3: Authentication Enhancement (Week 3-4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. JWT token updates
     • Include tenant_id claim
     • Include tenant role
     • Shorter expiry for multi-tenant

  2. API key system
     • Format: uk_{tenant_id}_{random}
     • Store tenant_id in API keys table
     • Rate limiting per key

  3. RBAC enhancement
     • System admin (cross-tenant)
     • Tenant admin (full tenant access)
     • Tenant member (limited access)
     • Tenant viewer (read-only)


PHASE 4: K8s Multi-Tenancy (Week 4-5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Namespace provisioning
     • Auto-create tenant-{id} namespace
     • Apply ResourceQuota
     • Apply NetworkPolicy
     • Create ServiceAccount

  2. Orchestration updates
     • Deploy to tenant namespace
     • Label all resources with tenant-id
     • Enforce resource limits

  3. Reconciliation
     • Reconcile tenant namespace state
     • Enforce quotas
     • Clean up on tenant deletion


PHASE 5: Production Hardening (Week 5-6)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Secrets management
     • Migrate to Vault/External Secrets
     • Tenant-specific encryption keys

  2. Monitoring & Observability
     • Per-tenant metrics
     • Resource usage tracking
     • Cost attribution

  3. Backup/DR
     • Per-tenant backup schedules
     • Tenant isolation in backups
     • Restore testing

  4. Security audit
     • Penetration testing
     • Cross-tenant access attempts
     • RLS policy verification
     • Audit log compliance


PHASE 6: Scale Testing (Week 6-7)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Load testing
     • 100+ tenants
     • 10,000 API calls/sec
     • Database performance

  2. Chaos engineering
     • Tenant isolation under failure
     • Database failover
     • Network partition handling

  3. Performance optimization
     • Query optimization
     • Caching strategy
     • Connection pooling
```

---

## What Stays (All Current Features)

```
✅ Kubernetes Management
   • Cluster registration
   • Resource management
   • Health monitoring
   • Reconciliation

✅ Orchestration System
   • Blueprint-based deployment
   • Auto-wiring
   • Manifest generation
   • Intent management

✅ Plugin System
   • Built-in plugins
   • External plugin support
   • Plugin marketplace (future)
   • Metrics collection

✅ Monitoring & Alerts
   • System metrics
   • Custom thresholds
   • Alert channels
   • Notification delivery

✅ Credential Management
   • SSH key storage
   • Certificate management
   • Audit logging
   • Encryption at rest

✅ AI Features
   • Chat interface
   • Insights generation
   • Knowledge base
   • Summarization

✅ Terminal Access
   • Web SSH
   • Multi-host support
   • Session management

✅ Reporting
   • Report generation
   • System snapshots
   • Historical data
   • Analytics

✅ Settings & Configuration
   • Server profiles
   • User preferences
   • System settings

✅ Frontend Dashboard (Optional)
   • React SPA
   • Real-time updates
   • Responsive design
   • Can be disabled per tenant
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  External Load Balancer                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    api.unity.com                          │   │
│  │              (TLS termination, DDoS protection)           │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  Ingress Controller (Nginx/Traefik)                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  • Rate limiting per tenant                              │   │
│  │  • Request logging                                       │   │
│  │  • Health checks                                         │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  Unity Backend (3+ replicas, autoscaling)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Pod 1          Pod 2          Pod 3          Pod N      │   │
│  │  (FastAPI)      (FastAPI)      (FastAPI)      (...)      │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│              ┌────────────┴────────────┐                         │
│              ▼                         ▼                         │
│  ┌───────────────────┐      ┌───────────────────┐               │
│  │   PostgreSQL      │      │      Redis        │               │
│  │   (Primary +      │      │   (Cache + Queue) │               │
│  │   Read Replicas)  │      │                   │               │
│  └───────────────────┘      └───────────────────┘               │
│                                                                  │
│  Unity Frontend (Optional, per tenant)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Static assets served from CDN                           │   │
│  │  SPA connects to api.unity.com                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Monitoring Stack                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Prometheus + Grafana + Loki + Alertmanager             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary

**Current State:**
- Single-tenant homelab manager
- All features working
- Docker stable with migrations

**Target State:**
- Multi-tenant SaaS control plane
- All features preserved
- API-first with optional dashboard
- Production-grade isolation
- Kubernetes orchestration
- Enterprise-ready

**Strategy:**
- Add tenant isolation layer
- Keep every existing feature
- Progressive enhancement
- Backward compatible
- "Peel away" old features later if needed

**Timeline:** 6-7 weeks to production-ready multi-tenant control plane

**Next Step:** Generate Alembic migration to add tenant_id to all tables (Phase 1)
