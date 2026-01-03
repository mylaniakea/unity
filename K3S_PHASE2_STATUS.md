# Unity k3s Deployment - Phase 2 Status

**Date:** January 3, 2026  
**Phase:** 2 - Application Deployment (In Progress)
**Environment:** asus (10.0.4.20), k3s v1.31.4

---

## Deployed Components

### ✅ Foundation Layer (Completed Phase 1)
- [x] 3 Namespaces (homelab, holon, biz)
- [x] Secrets & ConfigMaps (per namespace)
- [x] PostgreSQL StatefulSet (1/1 Running)
- [x] Redis Deployment (1/1 Running)

### 🔄 Application Layer (In Progress)
- [x] Backend Deployment manifest created
- [x] Frontend Deployment manifest created
- [x] Ingress manifest created
- 🟠 Backend pod: installing dependencies (not yet ready)
- 🟠 Frontend pod: CrashLoopBackOff

---

## Current Status

### Services Available
```
backend-service     ClusterIP  10.43.80.43   8000/TCP
frontend-service    ClusterIP  10.43.97.101  3000/TCP
postgres-service    ClusterIP  None          5432/TCP
redis-service       ClusterIP  10.43.37.215  6379/TCP
```

### Pods Status
```
✅ postgres-0                  1/1 Running
✅ redis-7d9fdcd897-7brvc     1/1 Running
🟠 unity-backend-*             0/1 Running (installing deps)
🟠 unity-frontend-*            0/1 CrashLoopBackOff
```

---

## What Happened

### Backend Issue Resolution
The Unity backend has a `DeploymentManager` that tries to connect to Docker at startup. We temporarily disabled the deployment router by:
1. Removed `deployments` from the routers import in `app/main.py` (line 102)
2. Commented out the router registration (line 113)

This allows the backend to start without Docker access, which is expected in a Kubernetes environment.

### Frontend Issue
The frontend is crashing due to missing build artifacts. The Node-based build/serve approach is slow in k3s with hostPath mounts because:
- Each pod restart rebuilds from source
- npm install downloads all dependencies each time
- Network latency with hostPath mounting to local filesystem

---

## Recommended Next Steps

### Option 1: Pre-Built Docker Images (Recommended)
1. **Build Docker images locally:**
   ```bash
   docker build -t unity-backend:latest backend/
   docker build -t unity-frontend:latest frontend/
   ```

2. **Push to registry** (e.g., Docker Hub, or k3s local registry):
   ```bash
   docker push myregistry/unity-backend:latest
   docker push myregistry/unity-frontend:latest
   ```

3. **Update deployments to use pre-built images:**
   - Replace `image: python:3.11-slim` with `image: unity-backend:latest`
   - Replace `image: node:20-alpine` with `image: unity-frontend:latest`

### Option 2: Hybrid Approach (Faster for Dev)
1. **Run Unity locally on asus** using docker-compose (from `/home/holon/Projects/unity`):
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

2. **Keep k3s for:**
   - Database (PostgreSQL)
   - Cache (Redis)
   - Future monitoring/alerting stack

3. **Access backend** via k3s services or localhost

### Option 3: Fix Deployment Manager
Modify `backend/app/services/deployment_manager.py` to:
- Make Docker client initialization lazy (only when needed)
- Provide graceful fallback when Docker is unavailable
- Use environment variable to skip deployment features

---

## Directory Manifest

```
/home/holon/Projects/unity/k8s/
├── namespaces/          (✅ Deployed)
│   ├── homelab.yaml
│   ├── holon.yaml
│   └── biz.yaml
├── base/               (✅ Deployed)
│   ├── secrets.yaml
│   └── configmap.yaml
├── services/           (✅ Deployed)
│   ├── postgresql.yaml
│   └── redis.yaml
└── deployments/        (🟠 Partial)
    ├── backend.yaml    (created, needs fix)
    ├── frontend.yaml   (created, needs fix)
    └── ingress.yaml    (created)
```

---

## Key Learnings

1. **k3s with hostPath + dynamic builds** = slow and resource-intensive
2. **Docker in k3s requires DinD or socket mounting** which adds complexity
3. **Pre-built images are essential** for production deployments
4. **Database/cache in k3s works well** - stateful services are fine with local-path storage

---

## Quick Commands

```bash
# Check deployment status
kubectl get deployment,pods -n homelab

# View backend logs
kubectl logs -l app=unity-backend -n homelab -f

# Port forward for testing
kubectl port-forward -n homelab svc/backend-service 8000:8000
kubectl port-forward -n homelab svc/frontend-service 3000:3000

# Check database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -n homelab -- \
  psql -h postgres-service -U homelab_user -d homelab_db

# Check Redis connectivity
kubectl run -it --rm debug --image=redis:7 --restart=Never -n homelab -- \
  redis-cli -h redis-service ping
```

---

## Next Session Tasks

1. **Build pre-built Docker images** for backend and frontend
2. **Push to registry** (local k3s or Docker Hub)
3. **Update deployment manifests** to use pre-built images
4. **Deploy and test** end-to-end
5. **Run database migrations** on PostgreSQL
6. **Create Ingress entries** in /etc/hosts for DNS resolution

---

**Total Manifests Created:** 10 files
**Services Running:** 4/4 (100%)
**Deployments Ready:** 0/2 (0%)
**Overall Progress:** 60% (foundation complete, app deployment in progress)
