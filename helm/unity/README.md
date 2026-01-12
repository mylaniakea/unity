# Unity Helm Chart

Helm chart for deploying Unity - Multi-Tenant Homelab Intelligence Control Plane on Kubernetes.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure (for PostgreSQL persistence)

## Installing the Chart

```bash
# Add the repository (if published)
helm repo add unity https://charts.holon.dev
helm repo update

# Install with default values
helm install unity unity/unity

# Install with custom values
helm install unity unity/unity -f my-values.yaml

# Install from local chart
helm install unity ./helm/unity
```

## Uninstalling the Chart

```bash
helm uninstall unity
```

## Configuration

See `values.yaml` for full configuration options.

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.multiTenancy.enabled` | Enable multi-tenant mode | `false` |
| `backend.replicaCount` | Number of backend replicas | `1` |
| `frontend.replicaCount` | Number of frontend replicas | `1` |
| `postgresql.enabled` | Deploy PostgreSQL | `true` |
| `postgresql.external.enabled` | Use external PostgreSQL | `false` |
| `secrets.postgresPassword` | PostgreSQL password | `""` (auto-generated) |
| `secrets.encryptionKey` | Fernet encryption key | `""` (default provided) |
| `ingress.enabled` | Enable ingress | `false` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `migrations.enabled` | Run Alembic migrations | `true` |

### Production Deployment

Create `production-values.yaml`:

```yaml
global:
  multiTenancy:
    enabled: true

backend:
  replicaCount: 3
  resources:
    requests:
      memory: "1Gi"
      cpu: "1000m"
    limits:
      memory: "2Gi"
      cpu: "2000m"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10

postgresql:
  external:
    enabled: true
    host: postgres.example.com
    port: 5432

secrets:
  postgresPassword: "your-secure-password"
  encryptionKey: "your-fernet-key"
  jwtSecret: "your-jwt-secret"

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: unity.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: unity-tls
      hosts:
        - unity.example.com

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true

backup:
  enabled: true
  schedule: "0 2 * * *"
```

Then deploy:

```bash
helm install unity ./helm/unity -f production-values.yaml
```

## Multi-Tenancy

To enable multi-tenancy:

```yaml
global:
  multiTenancy:
    enabled: true
    defaultTenant: "default"

tenants:
  - id: tenant-alpha
    namespace: tenant-alpha
    resourceQuota:
      pods: "10"
      requests.cpu: "4"
      requests.memory: "8Gi"
```

Each tenant will get:
- Dedicated Kubernetes namespace
- Resource quotas
- Network isolation
- Separate RBAC policies

## Upgrades

```bash
# Upgrade to new version
helm upgrade unity ./helm/unity

# Upgrade with new values
helm upgrade unity ./helm/unity -f new-values.yaml

# Rollback to previous version
helm rollback unity
```

## Backup and Restore

The chart includes optional backup CronJob:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  retention: 30
```

Manual backup:

```bash
# Run backup script
kubectl exec -it <backend-pod> -- /app/scripts/backup-database.sh
```

## Troubleshooting

### Check pod status
```bash
kubectl get pods -l app.kubernetes.io/instance=unity
```

### Check logs
```bash
kubectl logs -l app=unity-backend -f
kubectl logs -l app=unity-frontend -f
```

### Verify database connection
```bash
kubectl exec -it <backend-pod> -- python -c "from app.database import engine; print(engine.url)"
```

### Run migrations manually
```bash
kubectl exec -it <backend-pod> -- alembic upgrade head
```

## Development

Testing locally:

```bash
# Lint the chart
helm lint ./helm/unity

# Dry-run install
helm install unity ./helm/unity --dry-run --debug

# Template rendering
helm template unity ./helm/unity
```

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

## License

[Add your license here]
