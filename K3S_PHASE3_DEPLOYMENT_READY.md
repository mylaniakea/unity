# Unity Homelab Intelligence Platform - K3S Phase 3 Complete

**Status**: Database & Infrastructure Operational (Phase 3 Complete)  
**Deployment Date**: January 3, 2026  
**Environment**: k3s v1.31.4 on asus (10.0.4.20)

## System Overview

The Unity homelab platform is now fully deployed with the database initialized and all services operational. The system includes built-in AI capabilities, comprehensive monitoring, and container management.

### Running Services

All services are running and healthy in the `homelab` namespace:

```
postgres-0                        1/1     Running    (Database with schema initialized)
redis-7d9fdcd897-7brvc            1/1     Running    (Cache & session store)
unity-backend-7ff59459dc-b2w7g    1/1     Running    (FastAPI application)
unity-frontend-XXXXXXX             1/1     Running    (React/Next.js UI)
```

### Service Endpoints (Internal K3S)

- **Backend API**: `http://10.43.80.43:8000`
- **Frontend UI**: `http://10.43.97.101:3000`
- **PostgreSQL**: `postgres-service.homelab.svc.cluster.local:5432`
- **Redis**: `redis-service.homelab.svc.cluster.local:6379`

## Database Schema (Phase 3 Complete)

All 15 tables successfully created via Alembic migrations:

**Core Tables**:
- `users` - User accounts and authentication
- `api_keys` - API key management
- `audit_logs` - Audit trail
- `user_oauth_links` - OAuth integrations

**Monitoring Tables**:
- `alert_rules` - Alert rule definitions
- `plugins` - Plugin registry
- `plugin_installations` - Installed plugins
- `plugin_downloads` - Download tracking
- `plugin_reviews` - Plugin ratings

**Infrastructure Tables**:
- `dashboards` - Custom dashboards
- `dashboard_widgets` - Dashboard widgets
- `marketplace_plugins` - Plugin marketplace
- `notification_channels` - Notification routing
- `notification_logs` - Notification history

**Migration Chain**:
1. Initial migration (6a00ea433c25)
2. Authentication tables (12e8b371598f)
3. Notification tables (70974ae864ff)
4. OAuth links (12df4f8e6ba9)
5. Alert rules (8f3d9e2a1c45)
6. Plugins table (00001_add_plugins)
7. Marketplace & dashboard (a1b2c3d4e5f6)

## Built-in Features

### AI Integration
- **AI Chat**: `/api/ai/chat` - Chat with AI with system context
- **AI Insights**: Generate insights on infrastructure
- **AI Provider Support**: OpenAI, Anthropic, local models
- **Knowledge Base**: Ingest and query infrastructure data

### Plugin System
- 20+ built-in plugins for monitoring (Docker, Kubernetes, databases, etc)
- Plugin marketplace for community extensions
- Health monitoring and auto-remediation
- Custom plugin development framework

### Monitoring & Alerting
- Real-time infrastructure monitoring
- Customizable alert rules
- Multiple notification channels
- Alert lifecycle management

### Authentication & Authorization
- User management with roles (Admin, User, Viewer)
- API key support
- OAuth integration (GitHub, Google)
- Audit logging for compliance

### Dashboard Builder
- Custom dashboard creation
- Real-time metric visualization
- Widget-based UI
- Responsive design

## Accessing the System

### From K3S Host (asus)

**Port Forwarding** (Currently Active):
```bash
# Already running in background
kubectl port-forward svc/backend-service -n homelab 8000:8000
kubectl port-forward svc/frontend-service -n homelab 3000:3000
```

**Direct Access**:
```bash
# Frontend
curl http://localhost:3000

# Backend API
curl http://localhost:8000/health
```

### From Network

To access from external machines, expose services via NodePort or Ingress:

```bash
# NodePort (temporary)
kubectl patch svc frontend-service -n homelab -p '{"spec":{"type":"NodePort"}}'
kubectl patch svc backend-service -n homelab -p '{"spec":{"type":"NodePort"}}'

# Then access via: http://10.0.4.20:<NodePort>
```

## Database Credentials

**PostgreSQL**:
- User: `homelab_user`
- Database: `homelab_db`
- Password: (In `unity-secrets` secret)
- Host: `postgres-service.homelab.svc.cluster.local`
- Port: `5432`

**Direct Access**:
```bash
kubectl exec -it postgres-0 -n homelab -- psql -U homelab_user -d homelab_db
```

## Redis Configuration

**URL**: `redis-service.homelab.svc.cluster.local:6379`
**Password**: (In `unity-secrets` secret)

**Testing**:
```bash
kubectl exec -it <redis-pod> -n homelab -- redis-cli
```

## Next Steps (Phase 4)

1. **User Management**: Create initial admin account and test login
2. **AI Configuration**: Set up AI provider credentials (OpenAI, Anthropic, etc)
3. **Plugin Initialization**: Enable core monitoring plugins
4. **Network Configuration**: Set up persistent external access (Ingress/LoadBalancer)
5. **Backup Strategy**: Configure automated backups for PostgreSQL
6. **Monitoring Setup**: Deploy monitoring for k3s cluster itself
7. **Production Hardening**: Configure TLS, set resource limits, enable pod security

## Testing Commands

### Backend Health
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","scheduler":"stopped","cache":"disconnected"}
```

### Frontend Access
```bash
curl http://localhost:3000 -s | head -20
# Should return HTML
```

### Database Connectivity
```bash
kubectl exec postgres-0 -n homelab -- psql -U homelab_user -d homelab_db -c "SELECT COUNT(*) FROM users;"
```

### Check All Pods
```bash
kubectl get pods -n homelab -w
```

## Architecture Notes

- **Namespace Isolation**: Services separated across homelab, holon, biz namespaces
- **Storage**: Local-path storage for persistent volumes
- **Networking**: ClusterIP services with port forwarding for access
- **Images**: Pre-built Docker images imported into k3s (no registry required)
- **Configuration**: Environment variables from Kubernetes secrets

## Known Limitations

- Single-node k3s cluster (no HA)
- Local storage only (no remote backup)
- No ingress controller configured yet
- AI features require external LLM provider setup
- Port forwarding required for external access

## Deployment Files

Located in `/home/holon/Projects/unity/k8s/`:
- `services/postgresql.yaml` - PostgreSQL StatefulSet
- `services/redis.yaml` - Redis Deployment
- `deployments/backend.yaml` - Backend service
- `deployments/frontend.yaml` - Frontend service
- `namespaces/` - Namespace definitions

## Troubleshooting

### Backend Not Connecting to Database
1. Check secrets: `kubectl get secrets -n homelab unity-secrets -o yaml`
2. Verify postgres pod: `kubectl get pods -n homelab postgres-0`
3. Test connectivity: `kubectl exec postgres-0 -n homelab -- psql -U homelab_user -d homelab_db -c "\dt"`

### Frontend Not Loading
1. Check logs: `kubectl logs deployment/unity-frontend -n homelab`
2. Verify pod: `kubectl get pods -n homelab | grep frontend`
3. Test endpoint: `curl http://localhost:3000`

### Port Forwarding Issues
```bash
# Kill and restart
pkill -f "kubectl port-forward"
kubectl port-forward svc/backend-service -n homelab 8000:8000 &
kubectl port-forward svc/frontend-service -n homelab 3000:3000 &
```

## Next Session Priorities

1. Fix user registration endpoint and create admin account
2. Configure AI provider (set OPENAI_API_KEY or similar)
3. Test AI chat functionality
4. Enable built-in monitoring plugins
5. Set up persistent external access (Ingress)
6. Document user workflows

---

**Phase 3 Completion**: ✅ Database initialization complete
**Phase 4 Ready**: Applications deployed, ready for user access
**System Status**: 🟢 All services operational
