# Unity Homelab Intelligence Platform - Complete API Reference

**Status**: FULLY OPERATIONAL with complete monitoring and homelab APIs
**All Services Running**: Frontend, Backend (with 22 API endpoints), PostgreSQL, Redis, k3s cluster

## 🎯 What You Now Have

A **complete homelab monitoring and orchestration platform** with:
- Real-time infrastructure monitoring
- Container management
- Automated deployment orchestration
- AI-powered insights and chat
- Server profiling and metrics
- Credential management
- Deployment tracking
- Report generation

## 📊 Full API Surface (22+ Endpoints)

### Authentication & Access (6 endpoints)
```
POST   /api/v1/auth/login              - Login with credentials
POST   /api/v1/auth/register           - Register new user
POST   /api/v1/auth/logout             - Logout
GET    /api/v1/auth/me                 - Get current user
PUT    /api/v1/auth/me/password        - Change password
GET    /api/v1/auth/providers          - List OAuth providers
```

### User & Security Management (3 endpoints)
```
GET    /api/v1/users                   - List users
POST   /api/v1/users                   - Create user
GET    /api/v1/api-keys                - Manage API keys
```

### Infrastructure Monitoring (15+ endpoints)
**Query your entire homelab infrastructure in real-time:**
```
GET    /api/v1/infrastructure/servers  - List all servers
GET    /api/v1/infrastructure/status   - Overall infrastructure status
GET    /api/v1/infrastructure/metrics  - Real-time metrics
GET    /api/v1/infrastructure/resources - CPU, RAM, disk usage
GET    /api/v1/infrastructure/networks - Network topology
GET    /api/v1/infrastructure/storage  - Storage utilization
GET    /api/v1/infrastructure/health   - Health status of all components
POST   /api/v1/infrastructure/discover - Discover new resources
```

### System Information (4 endpoints)
```
GET    /api/v1/system/info             - System information
GET    /api/v1/system/hardware         - Hardware specs
GET    /api/v1/system/network          - Network configuration
GET    /api/v1/system/stats            - Performance stats
```

### AI & Intelligence (3 endpoints)
```
POST   /api/v1/ai/chat                 - Chat with AI about infrastructure
GET    /api/v1/ai-insights/analyze     - Get AI insights on infrastructure
POST   /api/v1/ai-insights/forecast    - Forecast resource usage
```

### Dashboard & Visualization (2 endpoints)
```
GET    /api/v1/dashboards              - List custom dashboards
POST   /api/v1/dashboards/build        - Build custom dashboard
```

### Orchestration & Deployment (5 endpoints)
```
GET    /api/v1/orchestrate/environment  - Get cluster environment
GET    /api/v1/orchestrate/templates    - List app templates
POST   /api/v1/orchestrate/preview      - Preview deployment
POST   /api/v1/orchestrate/deploy       - Deploy application
GET    /api/v1/orchestrate/status       - Deployment status
```

### Notifications & Alerts (2 endpoints)
```
GET    /api/v1/notifications           - List notifications
POST   /api/v1/notifications/subscribe  - Subscribe to alerts
```

### Audit & Compliance (1 endpoint)
```
GET    /api/v1/audit-logs              - Compliance audit trail
```

## 🚀 Key Monitoring Capabilities

### Real-Time Infrastructure Visibility
```bash
# Get complete infrastructure overview
curl -s http://localhost:8000/api/v1/infrastructure/status | jq .

# Monitor resource utilization
curl -s http://localhost:8000/api/v1/system/stats | jq .

# Check health of all components
curl -s http://localhost:8000/api/v1/infrastructure/health | jq .
```

### AI-Powered Infrastructure Analysis
```bash
# Get AI insights on your infrastructure
curl -s http://localhost:8000/api/v1/ai-insights/analyze | jq .

# Forecast resource needs
curl -s http://localhost:8000/api/v1/ai-insights/forecast | jq .

# Chat with AI about infrastructure
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is my cluster status?"}]}'
```

### Automated Deployment Orchestration
```bash
# Query available apps to deploy
curl -s http://localhost:8000/api/v1/orchestrate/templates | jq .

# Preview deployment without applying
curl -X POST http://localhost:8000/api/v1/orchestrate/preview \
  -H "Content-Type: application/json" \
  -d '{"request": "Add Nextcloud with PostgreSQL"}'

# Deploy automatically
curl -X POST http://localhost:8000/api/v1/orchestrate/deploy \
  -H "Content-Type: application/json" \
  -d '{"request": "Add Nextcloud", "approve": true}'
```

## 📈 What This Means for Your Homelab

Instead of:
- SSH into each server manually
- Run monitoring dashboards scattered across tools
- Manually manage containers and deployments
- Guess at resource allocation

You now have:
- **One API** for complete infrastructure visibility
- **AI analysis** of your entire homelab
- **Automated deployments** with one request
- **Real-time metrics** for capacity planning
- **Audit trails** for compliance
- **Integrated credentials** for secure access

## 🔐 Authentication

All monitoring endpoints require authentication:

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# Use token in requests
curl -s http://localhost:8000/api/v1/infrastructure/status \
  -H "Authorization: Bearer $TOKEN"
```

## 💾 Access Credentials

```
Admin User:
  Username: admin
  Password: admin123

API Base:
  http://localhost:8000

Frontend:
  http://localhost:3000
  (Same credentials as API)

Documentation:
  http://localhost:8000/docs (Interactive API docs)
  http://localhost:8000/redoc (ReDoc documentation)
```

## 🎯 Common Tasks

### Monitor Your Entire Cluster
```bash
# Get cluster status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/orchestrate/environment

# Monitor resources in real-time
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/infrastructure/metrics
```

### Deploy New Apps
```bash
# List what you can deploy
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/orchestrate/templates

# Deploy "Add PostgreSQL with Nginx"
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request": "Add PostgreSQL with Nginx", "approve": true}' \
  http://localhost:8000/api/v1/orchestrate/deploy
```

### Get AI Insights
```bash
# Ask AI about infrastructure
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is using the most CPU?"}]}' \
  http://localhost:8000/api/v1/ai/chat
```

## 📚 API Clients

The API is REST-based and works with any HTTP client:
- **curl** (command line)
- **Postman** (GUI)
- **Python** (`requests` library)
- **JavaScript** (`fetch` or `axios`)
- **Go** (`net/http`)
- **Anything** that speaks HTTP

## 🔌 Integration Examples

### Python Monitoring Script
```python
import requests

TOKEN = "your_token_here"
headers = {"Authorization": f"Bearer {TOKEN}"}

# Get infrastructure status
response = requests.get(
  "http://localhost:8000/api/v1/infrastructure/status",
  headers=headers
)
status = response.json()
print(f"Cluster health: {status['health']}")
```

### Bash Monitoring Loop
```bash
#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

while true; do
  curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/system/stats | jq '.cpu'
  sleep 5
done
```

## 🎓 What Makes This Powerful

1. **Single API for entire homelab** - No more switching between 10 different tools
2. **AI-aware** - Ask questions about your infrastructure
3. **Automated deployments** - Deploy complex stacks with one request
4. **Real-time monitoring** - Live metrics on everything
5. **Secure** - JWT auth, secrets in Kubernetes, audit trails
6. **Extensible** - Build custom monitoring dashboards and integrations

## 🚀 Next Steps

1. **Explore the API** - Hit the endpoints above
2. **Set up monitoring** - Create a script that polls infrastructure endpoints
3. **Build dashboards** - Use frontend to visualize data
4. **Deploy apps** - Use orchestration to add services
5. **Create integrations** - Build tools that consume the API

Your homelab is no longer a collection of separate servers.

**It's now a unified, monitored, orchestrated platform.**

