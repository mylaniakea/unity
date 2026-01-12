# Kubernetes Migration Checklist for Unity

## Pre-Migration Preparation

### ✅ Already Complete
- [x] Database migrations with Alembic
- [x] Helm charts created (`helm/unity/`)
- [x] K8s manifests ready (`k8s/deployments/`)
- [x] Multi-tenancy architecture
- [x] Backup/restore system
- [x] Health check endpoints
- [x] Resource limits defined

### 🔍 Pre-Flight Checks

#### 1. Environment Validation
```bash
# Verify K8s cluster is accessible
kubectl cluster-info
kubectl get nodes

# Check available resources
kubectl top nodes

# Verify namespaces
kubectl create namespace unity --dry-run=client -o yaml
```

#### 2. Secrets Preparation
```bash
# Create secrets (DO NOT commit these)
kubectl create secret generic unity-secrets \
  --from-literal=postgres-password=<CHANGE_ME> \
  --from-literal=redis-password=<CHANGE_ME> \
  --from-literal=jwt-secret-key=<CHANGE_ME> \
  --from-literal=encryption-key=<CHANGE_ME> \
  --namespace=unity \
  --dry-run=client -o yaml > /tmp/unity-secrets.yaml

# Review and apply
kubectl apply -f /tmp/unity-secrets.yaml
rm /tmp/unity-secrets.yaml
```

#### 3. Database Migration
```bash
# Backup current database
./scripts/backup-database.sh

# Verify backup
ls -lh backups/database/

# Test restore on dev cluster first
kubectl exec -it postgres-0 -n unity -- psql -U homelab_user -d homelab_db < backup.sql
```

#### 4. Image Registry
```bash
# Tag images for registry
docker tag unity-backend:latest <registry>/unity-backend:v1.0.0
docker tag unity-frontend:latest <registry>/unity-frontend:v1.0.0

# Push to registry
docker push <registry>/unity-backend:v1.0.0
docker push <registry>/unity-frontend:v1.0.0

# OR for local K3s/K8s
# Import images directly
k3s ctr images import unity-backend.tar
k3s ctr images import unity-frontend.tar
```

## Migration Steps

### Phase 1: Database Setup
```bash
# 1. Deploy PostgreSQL StatefulSet
kubectl apply -f k8s/base/postgres.yaml

# 2. Wait for DB to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n unity --timeout=300s

# 3. Run migrations
kubectl apply -f k8s/jobs/migrations.yaml

# 4. Verify migration
kubectl logs -f job/unity-migrations -n unity
```

### Phase 2: Backend Deployment
```bash
# 1. Deploy backend
kubectl apply -f k8s/deployments/backend.yaml

# 2. Verify deployment
kubectl get pods -n unity -l app=unity-backend
kubectl logs -f deployment/unity-backend -n unity

# 3. Check health
kubectl exec -it deployment/unity-backend -n unity -- curl http://localhost:8000/health
```

### Phase 3: Frontend Deployment
```bash
# 1. Deploy frontend
kubectl apply -f k8s/deployments/frontend.yaml

# 2. Verify deployment
kubectl get pods -n unity -l app=unity-frontend

# 3. Deploy ingress
kubectl apply -f k8s/deployments/ingress.yaml
```

### Phase 4: Validation
```bash
# 1. Check all pods are running
kubectl get pods -n unity

# 2. Check services
kubectl get svc -n unity

# 3. Test endpoints
INGRESS_IP=$(kubectl get ingress unity-ingress -n unity -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$INGRESS_IP/health
curl http://$INGRESS_IP/api/plugins/

# 4. Monitor logs
kubectl logs -f deployment/unity-backend -n unity --tail=50
```

## Rollback Plan

### If Migration Fails
```bash
# 1. Scale down K8s deployments
kubectl scale deployment unity-backend -n unity --replicas=0
kubectl scale deployment unity-frontend -n unity --replicas=0

# 2. Restore Docker Compose
cd /path/to/unity
docker compose up -d

# 3. Restore database if needed
./scripts/restore-database.sh backups/database/latest_backup.sql.gz

# 4. Verify Docker services
docker compose ps
curl http://localhost/api/plugins/
```

## Post-Migration

### 1. Monitoring Setup
```bash
# Deploy monitoring stack (if not already)
kubectl apply -f k8s/monitoring/

# Check metrics
kubectl top pods -n unity
```

### 2. Backup Configuration
```bash
# Set up automated backups in K8s
kubectl apply -f k8s/jobs/backup-cronjob.yaml

# Verify CronJob
kubectl get cronjobs -n unity
```

### 3. Multi-Tenant Configuration
```bash
# Enable multi-tenancy in Helm values
helm upgrade unity ./helm/unity \
  --set multiTenancy.enabled=true \
  --namespace unity
```

### 4. Plugin Deployment
```bash
# Verify all 36 plugins are discovered
kubectl exec -it deployment/unity-backend -n unity -- \
  python -c "from app.services.plugin_manager import PluginManager; from app.database import SessionLocal; db = SessionLocal(); mgr = PluginManager(db); print(f'Plugins: {len(mgr.list_plugins())}')"
```

## Troubleshooting

### Common Issues

**Pods stuck in Pending:**
```bash
kubectl describe pod <pod-name> -n unity
# Check events for resource or scheduling issues
```

**Database connection failures:**
```bash
# Check service DNS
kubectl run -it --rm debug --image=busybox --restart=Never -n unity -- nslookup postgres-service

# Test connection
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n unity -- \
  psql -h postgres-service -U homelab_user -d homelab_db
```

**Image pull errors:**
```bash
# Check image pull secrets
kubectl get secrets -n unity

# Verify image exists
kubectl describe pod <pod-name> -n unity | grep -A 5 "Failed"
```

## Success Criteria

- [ ] All pods in Running state
- [ ] Health checks passing
- [ ] Database migrations complete
- [ ] Frontend accessible via ingress
- [ ] All 36 plugins discovered
- [ ] API endpoints responding
- [ ] Monitoring active
- [ ] Backups configured
- [ ] Docker Compose services stopped

## Notes

- Keep Docker Compose setup for at least 1 week as fallback
- Monitor resource usage for first 24 hours
- Document any custom configurations
- Update DNS/load balancer to point to K8s ingress
