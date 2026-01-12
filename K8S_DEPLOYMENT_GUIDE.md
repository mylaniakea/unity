# Unity Kubernetes Deployment Guide

This guide covers deploying Unity to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (k3s, minikube, or full cluster)
- kubectl configured
- Docker images built and pushed to a registry (or use local registry)
- Persistent storage provisioner (local-path for k3s, or StorageClass)

## Quick Start

### 1. Build and Push Images

```bash
# Build images
docker compose build

# Tag for your registry
docker tag unity-backend:latest your-registry/unity-backend:latest
docker tag unity-frontend:latest your-registry/unity-frontend:latest

# Push to registry
docker push your-registry/unity-backend:latest
docker push your-registry/unity-frontend:latest
```

### 2. Update Image References

Edit the deployment files in `k8s/deployments/` to use your registry images.

### 3. Create Namespace

```bash
kubectl create namespace unity
```

### 4. Deploy Database and Redis

```bash
# PostgreSQL StatefulSet (you'll need to create this)
kubectl apply -f k8s/base/postgres.yaml -n unity

# Redis Deployment
kubectl apply -f k8s/base/redis.yaml -n unity
```

### 5. Run Database Migrations

```bash
kubectl apply -f k8s/jobs/init-database.yaml -n unity
kubectl wait --for=condition=complete job/init-database -n unity --timeout=300s
```

### 6. Deploy Backend

```bash
kubectl apply -f k8s/deployments/backend.yaml -n unity
kubectl wait --for=condition=available deployment/unity-backend -n unity --timeout=300s
```

### 7. Deploy Frontend

```bash
kubectl apply -f k8s/deployments/frontend.yaml -n unity
```

### 8. Setup Ingress (Optional)

```bash
kubectl apply -f k8s/deployments/ingress.yaml -n unity
```

## Configuration

### Environment Variables

The backend requires these environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ENCRYPTION_KEY`: Encryption key for credentials (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `ALLOW_ORIGINS`: CORS origins (use `*` for development)

### Secrets

Create a secret for sensitive values:

```bash
kubectl create secret generic unity-secrets \
  --from-literal=database-url='postgresql+psycopg2://user:pass@postgres:5432/unity' \
  --from-literal=encryption-key='your-key-here' \
  -n unity
```

## Persistent Storage

Unity requires persistent storage for:
- PostgreSQL data
- Backend data directory

Ensure your cluster has a StorageClass configured. For k3s, `local-path` is available by default.

## Health Checks

The backend exposes a `/health` endpoint that checks:
- Database connectivity
- Redis connectivity

The Kubernetes deployments use this for liveness and readiness probes.

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n unity
```

### View Logs

```bash
kubectl logs -f deployment/unity-backend -n unity
kubectl logs -f deployment/unity-frontend -n unity
```

### Check Database Migration

```bash
kubectl logs job/init-database -n unity
```

### Test Services

```bash
# Port forward backend
kubectl port-forward -n unity svc/unity-backend 8000:8000

# Test health endpoint
curl http://localhost:8000/health
```

## Cleanup

To remove Unity from your cluster:

```bash
kubectl delete namespace unity
```

Or delete individual resources:

```bash
kubectl delete -f k8s/deployments/ -n unity
kubectl delete -f k8s/jobs/ -n unity
```

## Current K8s Directory Structure

```
k8s/
├── base/
│   └── ghcr-secret-placeholder.yaml    # Template for registry secrets
├── deployments/
│   ├── backend.yaml                    # Backend deployment & service
│   ├── backend-with-migrations.yaml    # Backend with init container
│   ├── frontend.yaml                   # Frontend deployment & service
│   └── ingress.yaml                    # Ingress configuration
├── jobs/
│   ├── init-database.yaml              # Database initialization
│   ├── migrate-database.yaml           # Run migrations
│   ├── migrate-database-init.yaml      # Migration with init
│   └── stamp-database.yaml             # Alembic stamp
└── rbac/
    └── backend-rbac.yaml               # RBAC for backend
```

## Next Steps

1. Review and customize the manifests in `k8s/` for your environment
2. Set up a CI/CD pipeline to automate deployments
3. Configure monitoring and logging (Prometheus, Grafana, Loki)
4. Set up automatic backups for PostgreSQL data
5. Configure TLS certificates (cert-manager)

## Notes

- The current k8s configs were used with a k3s cluster and may need adjustments
- PostgreSQL and Redis manifests need to be created (currently missing from k8s/)
- Consider using Helm charts for easier configuration management
- For production, use a managed PostgreSQL service instead of in-cluster
