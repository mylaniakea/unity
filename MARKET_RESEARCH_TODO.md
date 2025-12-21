# Unity Market Research: Advanced Features & Plugin Expansion

**Research Date:** December 21, 2024  
**Status:** Complete - Ready for Implementation Planning

---

## 🔐 AUTHENTICATION & ACCESS CONTROL

### Industry Leaders Analyzed
- **Keycloak** - Full-featured SSO/IAM platform (enterprise-grade)
- **Authelia** - Lightweight SSO for reverse proxies
- **Authentik** - GUI-based SSO with OIDC/OAuth/LDAP (current user choice!)
- **Tinyauth** - Minimal SSO with Google OAuth integration

### Authentication Features to Implement

#### 1. Single Sign-On (SSO) - PRIMARY FOCUS
- [ ] **OIDC (OpenID Connect) provider**
  - Act as identity provider for other services
  - JWT token generation and validation
  - User info endpoint
  - Well-known discovery endpoint

- [ ] **OAuth2 Social Providers**
  - [ ] GitHub OAuth (most popular for developers)
  - [ ] Google OAuth (gmail accounts)
  - [ ] GitLab OAuth
  - [ ] Generic OAuth2 provider support
  - Configuration per provider (client ID, secret, scopes)

- [ ] **SAML Support** (future - enterprise integration)
  - SAML 2.0 IdP
  - Metadata endpoints
  - Attribute mapping

#### 2. Multi-Factor Authentication (2FA)
- [ ] **TOTP (Time-based One-Time Password)**
  - QR code generation for authenticator apps
  - Backup codes generation
  - Remember device option

- [ ] **WebAuthn/FIDO2** (future)
  - Hardware security keys (YubiKey, etc.)
  - Biometric authentication

- [ ] **Mobile Push Notifications** (advanced)
  - Integration with push services
  - Approve/deny workflow

- [ ] **Email/SMS Verification Codes** (backup method)
  - One-time codes via email
  - SMS via Twilio integration

#### 3. User Management
- [ ] **Local User Database**
  - Username/password authentication
  - Password hashing (bcrypt/argon2)
  - User CRUD operations

- [ ] **LDAP/Active Directory Integration**
  - LDAP bind authentication
  - Group membership sync
  - User attribute mapping

- [ ] **Role-Based Access Control (RBAC)**
  - Predefined roles: Admin, Editor, Viewer
  - Custom role creation
  - Permission granularity (read/write/delete per resource)
  - Group-based permissions

- [ ] **API Key Management**
  - Per-user API keys
  - Key expiration
  - Scoped permissions (limit what API key can do)
  - Usage tracking

- [ ] **Session Management**
  - Redis/Valkey backend for session storage
  - Configurable session timeout
  - "Remember me" functionality
  - Active session viewing and revocation

#### 4. Security Features
- [ ] **Password Policies**
  - Minimum length requirements
  - Complexity rules (uppercase, numbers, symbols)
  - Password history (prevent reuse)
  - Expiration policies

- [ ] **Brute Force Protection**
  - Rate limiting per IP/username
  - Account lockout after N failed attempts
  - CAPTCHA integration
  - Failed login notifications

- [ ] **IP Whitelisting/Blacklisting**
  - Allow/deny by IP range
  - Geo-IP blocking
  - Trusted network zones

- [ ] **Audit Logs**
  - Login/logout events
  - Permission changes
  - Configuration modifications
  - Export audit logs (compliance)

- [ ] **Header-Based Authentication**
  - X-Forwarded-User header support
  - For reverse proxy integration (Traefik, Caddy, nginx)
  - Header validation and security

### Implementation Priority

**Phase 2A: Basic Auth (2-3 weeks)**
1. Local user authentication (username/password)
2. API key authentication
3. Basic RBAC (admin/viewer roles)
4. Session management with Redis

**Phase 2B: OAuth2/SSO (3-4 weeks)**
1. GitHub OAuth provider
2. Google OAuth provider
3. Generic OAuth2 provider support
4. User account linking (OAuth + local)

**Phase 2C: Enhanced Security (2-3 weeks)**
1. TOTP 2FA implementation
2. Brute force protection
3. Audit logging
4. Password policies

**Phase 3: Advanced Auth (future)**
1. OIDC provider capabilities
2. LDAP/AD integration
3. SAML support
4. WebAuthn/FIDO2

---

## 🚨 ALERTING & NOTIFICATIONS

### Best-in-Class Examples
- **Uptime Kuma** - 95+ notification channels via Apprise integration
- **Grafana** - Sophisticated alerting with notification policies
- **Prometheus + Alertmanager** - Enterprise-grade alert routing
- **Netdata** - Distributed alerting with ML anomaly detection

### Alert Features to Implement

#### Alert Trigger Types
- [ ] **Threshold-Based Alerts**
  - CPU usage > X%
  - Memory usage > X%
  - Disk space < X%
  - Response time > X ms
  - Error rate > X per minute

- [ ] **Status Change Alerts**
  - Service up → down
  - Service down → up (auto-resolve)
  - Health check failures
  - Plugin execution failures

- [ ] **Time-Based Rules**
  - Sustained conditions ("high for 5+ minutes")
  - Time windows ("only alert during business hours")
  - Rate of change ("increased by 50% in 10 minutes")

- [ ] **Composite Conditions** (advanced)
  - Multiple metrics ("CPU high AND memory high")
  - Cross-service conditions ("API slow AND DB slow")
  - Logical operators (AND, OR, NOT)

- [ ] **Anomaly Detection** (future ML integration)
  - ML-powered baseline learning
  - Pattern recognition
  - Automatic threshold adjustment

#### Notification Channels

**Immediate Priority (Phase 2):**
- [ ] **Email (SMTP)**
  - Configurable SMTP server
  - Template support (HTML/text)
  - Attachment support (graphs, logs)

- [ ] **Webhooks**
  - Generic HTTP POST
  - Custom headers
  - Payload templating (JSON)
  - Retry logic

- [ ] **Slack**
  - Incoming webhooks
  - Rich formatting (blocks)
  - Thread replies for updates
  - Channel routing

- [ ] **Discord**
  - Webhook integration
  - Embed messages
  - Mention/ping support

**High Priority (Phase 3) - Apprise Integration:**
- [ ] **Integrate Apprise Library**
  - One integration = 78+ services!
  - **Messaging:** Telegram, Matrix, Microsoft Teams, Mattermost
  - **Incident Management:** PagerDuty, Opsgenie, VictorOps, Zenduty
  - **Phone:** Twilio (SMS/Voice), Phone calls
  - **Mobile:** Pushover, Pushbullet, Gotify, ntfy
  - **And 60+ more...**

#### Advanced Alerting Features

- [ ] **Alert Routing & Policies**
  - Label-based routing ("team=ops" → Slack, "severity=critical" → PagerDuty)
  - Hierarchical policies with inheritance
  - Multiple destinations per alert
  - Time-based routing (business hours vs. after-hours)
  - Contact points (groups of notification channels)

- [ ] **Alert Management**
  - **Grouping:** Combine related alerts into one notification
  - **Deduplication:** Prevent duplicate notifications
  - **Silences:** Scheduled maintenance windows (disable alerts)
  - **Mute timings:** Quiet hours configuration
  - **Auto-resolve notifications:** Alert when condition clears
  - **Acknowledgment:** Mark alert as "seen" to prevent re-notification

- [ ] **Alert Escalation**
  - Multi-level escalation chains
  - Time-based escalation ("notify team → wait 10min → page on-call")
  - Escalation policies per alert type

- [ ] **Alert Context & Enrichment**
  - **Custom templates:** Variable substitution (host, metric, value, time)
  - **Runbook links:** Attach remediation procedures
  - **Dashboard links:** Direct link to relevant dashboards
  - **Graph snapshots:** Embed metric graphs in notifications
  - **Historical context:** "This has happened X times in past week"
  - **Related metrics:** Show correlated data

- [ ] **Smart Features**
  - **Alert fatigue prevention:**
    - Rate limiting (max N alerts per hour)
    - Grouping windows ("wait 5min for more alerts before sending")
    - Priority levels (critical, warning, info)
  - **Alert dependencies:** "Don't alert if parent service is down"
  - **Flapping detection:** Suppress alerts that toggle rapidly
  - **Heartbeat monitoring:** Alert if no data received

#### Alert History & Analytics
- [ ] Alert timeline view
- [ ] Alert statistics (MTTA, MTTR)
- [ ] Most frequent alerts
- [ ] Alert heatmap (time of day, day of week)
- [ ] Export alert history

### Implementation Priority

**Phase 2A: Basic Alerting (2-3 weeks)**
1. Alert rules engine (threshold-based)
2. Email notifications (SMTP)
3. Webhook notifications
4. Alert history storage
5. Manual alert acknowledgment

**Phase 2B: Popular Channels (1-2 weeks)**
1. Slack integration
2. Discord integration
3. Alert templates
4. Auto-resolve notifications

**Phase 2C: Apprise Integration (1 week) - QUICK WIN!**
1. Integrate Apprise library
2. Configuration UI for 78+ services
3. Test with top 5-10 services

**Phase 3A: Advanced Routing (2-3 weeks)**
1. Alert routing policies
2. Label-based routing
3. Contact points/groups
4. Time-based routing

**Phase 3B: Alert Management (2-3 weeks)**
1. Alert grouping
2. Silences and mute timings
3. Escalation chains
4. Alert dependencies

---

## 🚀 QUICK WINS (Immediate High Impact)

### Week 1 Quick Wins
1. **Apprise Integration** (1-2 days)
   - Install Apprise library: `pip install apprise`
   - Create notification endpoint
   - Configuration UI for Apprise URLs
   - **Result:** Instant access to 78+ notification channels!

2. **Status Badge Endpoints** (1 day)
   - Generate SVG badges (shields.io style)
   - Public URLs: `/badge/plugin/{id}`
   - Show: up/down, response time, uptime %
   - **Result:** Embed status in README, status pages

3. **Basic Auth Protection** (2 days)
   - Simple username/password login
   - Protect all dashboard routes
   - **Result:** Secure Unity from unauthorized access

### Week 2 Quick Wins
4. **HTTP Monitor Plugin** (3-4 days)
   - Most requested feature
   - Enables SSL cert monitoring
   - **Result:** Monitor all HTTP services + certs

5. **Email Alerts** (2-3 days)
   - SMTP configuration
   - Email templates
   - **Result:** Get notified of issues via email

---

## 🐳 NEXT FOCUS: DOCKER/PODMAN/KUBERNETES INTEGRATIONS

### Current State
✅ Basic Docker container stats (CPU, memory, network, I/O)
✅ Container listing

### Enhancement Opportunities

#### Docker/Podman Deep Monitoring
- [ ] **Container Lifecycle Events**
  - Start/stop/restart events
  - Container creation/deletion
  - Image pulls
  - Event timeline

- [ ] **Container Health Checks**
  - Built-in health check status
  - Custom health check scripts
  - Health history tracking

- [ ] **Container Logs**
  - Real-time log streaming
  - Log search and filtering
  - Log level extraction
  - Multi-container log aggregation

- [ ] **Image Management**
  - Image vulnerability scanning (Trivy integration)
  - Unused image detection
  - Image size tracking
  - Registry status

- [ ] **Network Monitoring**
  - Container network topology
  - Inter-container communication
  - Port mapping status
  - Network usage per container

- [ ] **Volume Monitoring**
  - Volume usage tracking
  - Orphaned volume detection
  - Volume backup status

- [ ] **Docker Compose Support**
  - Stack/service detection
  - Group containers by compose project
  - One-click restart entire stack
  - Compose file validation

- [ ] **Podman Specific**
  - Pod monitoring (group of containers)
  - Rootless container support
  - Systemd integration
  - Podman API v2 support

#### Kubernetes Integration

**Cluster-Level Monitoring:**
- [ ] **Cluster Health**
  - Node status (Ready/NotReady)
  - Control plane component health
  - API server responsiveness
  - etcd health

- [ ] **Node Monitoring**
  - Node resource usage (CPU, memory, disk)
  - Node conditions (disk pressure, memory pressure)
  - Kubelet status
  - Container runtime status

- [ ] **Namespace Monitoring**
  - Resource quotas usage
  - Limit ranges
  - Network policies
  - Pod count per namespace

**Workload Monitoring:**
- [ ] **Pod Monitoring**
  - Pod status (Running, Pending, Failed, CrashLoopBackOff)
  - Container status within pods
  - Pod resource usage
  - Pod events
  - Restart counts

- [ ] **Deployment Monitoring**
  - Deployment status
  - Replica count (desired vs. actual)
  - Rollout status
  - Deployment history

- [ ] **StatefulSet Monitoring**
  - Ordered pod status
  - Persistent volume claims
  - Headless service status

- [ ] **DaemonSet Monitoring**
  - DaemonSet coverage (nodes with pod)
  - Pod distribution
  - Update strategy

- [ ] **Job/CronJob Monitoring**
  - Job completion status
  - Failed jobs
  - CronJob schedule status
  - Last run time

**Service & Networking:**
- [ ] **Service Monitoring**
  - Service endpoints
  - Service type (ClusterIP, NodePort, LoadBalancer)
  - External IP status
  - Service selector matching

- [ ] **Ingress Monitoring**
  - Ingress rules
  - Backend service health
  - TLS certificate status
  - Ingress controller metrics

### Docker/K8s Integration Priority

**Phase 2A: Enhanced Docker Monitoring (1-2 weeks)**
1. Container lifecycle events
2. Container health checks
3. Container logs viewer
4. Docker Compose detection
5. Image vulnerability scanning (Trivy)

**Phase 2B: Podman Support (1 week)**
1. Podman API integration
2. Pod monitoring
3. Rootless container support

**Phase 3A: Basic K8s Monitoring (2-3 weeks)**
1. Cluster connection (kubeconfig)
2. Node status monitoring
3. Pod status monitoring
4. Deployment monitoring
5. Service monitoring

**Phase 3B: Advanced K8s Features (2-3 weeks)**
1. Kubernetes events
2. Pod logs
3. Namespace resource quotas
4. Ingress monitoring
5. Job/CronJob monitoring

**Phase 4: K8s Polish (1-2 weeks)**
1. Multi-cluster support
2. Topology visualization
3. K8s-specific alerts
4. Resource optimization recommendations

---

## 🔌 PLUGIN EXPANSION ROADMAP

### Plugin Priority Matrix

#### 🔥 IMMEDIATE (Phase 2) - High Value, Easy Implementation

1. **HTTP/HTTPS Monitor Plugin** (1 week)
   - Check URL availability (GET/POST/HEAD requests)
   - Response time tracking
   - Status code validation
   - SSL certificate expiry checking
   - Content matching (regex search in response)
   - Custom headers and auth
   - **Use cases:** Monitor APIs, web apps, SSL certs

2. **TCP Port Monitor Plugin** (3 days)
   - Check if port is open
   - Connection time measurement
   - Banner grabbing (service identification)
   - **Use cases:** Database ports, SSH, custom services

3. **Ping Monitor Plugin** (2 days)
   - ICMP ping
   - Packet loss tracking
   - Latency measurement (min/avg/max)
   - **Use cases:** Network reachability, router health

4. **Speed Test Plugin** (1 week)
   - Integration with Speedtest.net API
   - LibreSpeed support (self-hosted)
   - Scheduled tests
   - Historical trend tracking
   - **Use cases:** ISP performance monitoring, bandwidth verification

5. **Generic Prometheus Scraper Plugin** (1 week) - GAME CHANGER!
   - Scrape any Prometheus exporter endpoint
   - Metric parsing and storage
   - Opens access to 100s of existing exporters!
   - **Use cases:** Any service with /metrics endpoint

#### 🎯 HIGH PRIORITY (Phase 3) - Popular Homelab Services

6. **Pi-hole/AdGuard Plugin** (5 days)
   - Queries blocked/allowed
   - Top blocked domains
   - Top clients
   - Gravity list status
   - DNS query performance

7. **Proxmox Plugin** (1-2 weeks)
   - VM/Container status and stats
   - Host resource usage
   - Cluster status
   - Storage pool health
   - Backup job status

8. **Plex/Jellyfin/Emby Plugin** (1 week)
   - Active streams count
   - Transcoding sessions
   - Library statistics
   - User activity
   - Server load

9. **TrueNAS/FreeNAS Plugin** (1 week)
   - Pool status and capacity
   - ZFS health (errors, scrub status)
   - Snapshot status
   - Replication jobs
   - SMART data

10. **Backup Monitor Plugin** (5 days)
    - Restic repository status
    - Borg backup completion
    - Last backup time
    - Backup size trends
    - Failure detection

---

## 📝 USER PREFERENCES & DECISIONS

### Confirmed User Preferences
- ✅ User has experience with **Authentik** for SSO
- ✅ Wants to support **GitHub** and **Gmail** as OAuth providers  
- ✅ Interested in all the research ideas
- ✅ Definitely wants to grow SSO support
- ✅ Next focus after SSO: **Docker/Podman/Kubernetes integrations**

### Technical Stack Decisions
- Use **Redis/Valkey** for session storage (stateless app servers)
- Integrate **Apprise** for notification channels (fastest path to 78+ services)
- Use **Docker Python SDK** for Docker monitoring
- Use **kubernetes Python client** for K8s monitoring
- Consider **Trivy** for vulnerability scanning

---

## 🎯 SUCCESS METRICS

### Phase 2 Goals
- [ ] OAuth2 authentication working (GitHub, Google)
- [ ] Basic alerting operational (email, Slack, webhooks)
- [ ] 5+ new plugins deployed (HTTP, ping, TCP, speed test, Prometheus)
- [ ] Apprise integration complete (78+ channels available)
- [ ] Enhanced Docker monitoring with logs and events

### Phase 3 Goals
- [ ] 10+ popular homelab plugins (Pi-hole, Proxmox, Plex, databases)
- [ ] Alert routing and policies functional
- [ ] Enhanced Docker monitoring with logs and events
- [ ] Basic Kubernetes monitoring operational
- [ ] Dashboard templates available

---

**Status:** Ready for implementation! 🚀  
**Next Steps:** Begin Phase 2A (Authentication Foundation) and Docker/Podman integration research.

---

# 🐳 DOCKER/PODMAN/KUBERNETES DEEP DIVE

## Docker Monitoring - Technical Details

### Docker API Access Methods

**1. Docker Remote API (HTTP REST API)**
- Endpoint: `unix:///var/run/docker.sock` (local) or `tcp://host:2375` (remote)
- API Version: Requires Docker API 1.25+ for full stats support
- Authentication: Root/privileged access required for socket
- Python library: `docker` (official Docker SDK for Python)

**2. Docker Stats API** (`/containers/{id}/stats`)
- Real-time streaming endpoint (continuous JSON stream)
- Metrics included:
  - **CPU**: `cpu_stats`, `precpu_stats`, system CPU usage, per-core breakdown
  - **Memory**: usage, limit, cache, RSS, swap, OOM kill count
  - **Network**: RX/TX bytes, packets, errors, dropped packets (per interface)
  - **Block I/O**: Read/write bytes and operations per device
  - **PIDs**: Number of processes/threads in container
- Update frequency: ~1 second intervals
- Non-blocking: Use `stream=1` for continuous updates or `stream=0` for snapshot

**3. Docker Events API** (`/events`)
- Real-time event stream for lifecycle monitoring
- Event types:
  - **Container**: `create`, `start`, `stop`, `restart`, `kill`, `die`, `pause`, `unpause`, `destroy`
  - **Image**: `pull`, `push`, `tag`, `untag`, `delete`, `build`
  - **Volume**: `create`, `mount`, `unmount`, `destroy`
  - **Network**: `create`, `connect`, `disconnect`, `destroy`
  - **Plugin**: `enable`, `disable`, `install`, `remove`
  - **Daemon**: `reload` (config changes)
- Attributes: timestamp, action, actor (ID, name), labels
- Filtering: Can filter by container, image, event type, label

**4. Docker Logs API** (`/containers/{id}/logs`)
- Retrieve stdout/stderr logs from containers
- Parameters:
  - `stdout=1`, `stderr=1` - Which streams to include
  - `timestamps=1` - Add RFC3339 timestamps
  - `since=<unix_timestamp>` - Only logs since time
  - `until=<unix_timestamp>` - Only logs until time
  - `tail=<n>` - Only last N lines
  - `follow=1` - Stream logs in real-time
- Log formats: JSON logging driver provides structured logs

**5. Docker Inspect API** (`/containers/{id}/json`)
- Complete container configuration and state
- Useful data:
  - Container state (running, paused, restarting, exited)
  - Health check status and history
  - Restart count
  - Network settings (IP addresses, ports, aliases)
  - Mount points (volumes)
  - Environment variables
  - Labels and annotations
  - Image information

### Implementation Approach for Unity

```python
# Example: Docker Python SDK integration
import docker

client = docker.from_env()  # Uses DOCKER_HOST or socket

# Get container stats (streaming)
container = client.containers.get('my-container')
stats_stream = container.stats(decode=True, stream=True)
for stat in stats_stream:
    cpu_percent = calculate_cpu_percent(stat)
    memory_usage = stat['memory_stats']['usage']
    # Store in Unity database

# Listen to events
for event in client.events(decode=True):
    if event['Type'] == 'container':
        # Store event: container start/stop/die
        unity_db.store_event(event)

# Get logs (streaming)
for line in container.logs(stream=True, follow=True):
    # Parse and store log line
    unity_db.store_log(container.id, line)
```

### Advanced Docker Features to Implement

**1. Container Health Monitoring**
```python
# Health check status from Docker
inspect_data = container.attrs
health = inspect_data['State']['Health']
# health['Status'] = 'healthy', 'unhealthy', 'starting', 'none'
# health['FailingStreak'] = number of consecutive failures
# health['Log'] = list of recent health check results with timestamps
```

**2. Docker Compose Detection**
```python
# Detect compose projects via labels
container.labels.get('com.docker.compose.project')  # Project name
container.labels.get('com.docker.compose.service')  # Service name
container.labels.get('com.docker.compose.oneoff')   # One-off command?
```

**3. Container Dependency Tracking**
```python
# Get container links and networks
networks = inspect_data['NetworkSettings']['Networks']
for net_name, net_config in networks.items():
    # Track which containers share networks (can communicate)
    ipam = net_config['IPAddress']
```

**4. Image Vulnerability Scanning**
```bash
# Use Trivy for image scanning
trivy image --format json nginx:latest > vulns.json
# Parse JSON and store vulnerability count/severity in Unity
```

### Performance Considerations

- **Stats polling**: 1-5 second intervals (configurable)
- **Event streaming**: Keep persistent connection, reconnect on failure
- **Log streaming**: Optional feature (can be resource-intensive)
- **Batch updates**: Update database in batches vs. per-container
- **Connection pooling**: Reuse Docker client connection

---

## Podman Monitoring - Technical Details

### Key Differences from Docker

1. **Socket Location**: 
   - Rootful: `unix:///run/podman/podman.sock`
   - Rootless: `unix:///run/user/{UID}/podman/podman.sock`

2. **API Compatibility**:
   - Podman v2+ has Docker-compatible API
   - Can use same Docker Python SDK!
   - Set `DOCKER_HOST=unix:///run/podman/podman.sock`

3. **Pod Support** (Podman-specific):
   - Pods = group of containers sharing namespaces (like K8s pods)
   - API endpoint: `/libpod/pods` (Podman-specific API)
   - Pod operations: `create`, `start`, `stop`, `rm`, `stats`

4. **Systemd Integration**:
   - Containers can be managed as systemd services
   - `podman generate systemd` creates unit files
   - Monitor via systemd status in addition to Podman API

### Podman-Specific Implementation

```python
import docker

# Connect to Podman socket (rootless)
import os
uid = os.getuid()
client = docker.DockerClient(base_url=f'unix:///run/user/{uid}/podman/podman.sock')

# Works the same as Docker for containers!
containers = client.containers.list()

# For pods, use Podman-specific libpod API
import requests
pods = requests.get('http://localhost/libpod/pods/json',
                    unix_socket='/run/podman/podman.sock').json()
```

### Podman Features for Unity

- [ ] **Rootless container monitoring** (non-privileged users)
- [ ] **Pod grouping and monitoring**
  - Pod status (running, paused, stopped)
  - Containers per pod
  - Shared resources between pod containers
- [ ] **Systemd service integration**
  - Detect containers managed by systemd
  - Restart policies via systemd
- [ ] **Quadlet support** (Podman 4.4+)
  - Container units in /etc/containers/systemd/

---

## Kubernetes Monitoring - Technical Details

### Kubernetes API Access

**1. Connection Methods**
```python
from kubernetes import client, config

# In-cluster (when Unity runs as K8s pod)
config.load_incluster_config()

# Out-of-cluster (kubeconfig file)
config.load_kube_config()  # Default: ~/.kube/config

# Custom kubeconfig
config.load_kube_config(config_file='/path/to/kubeconfig')
```

**2. Core API Resources**
- **v1 API** (core resources):
  - Pods, Services, ConfigMaps, Secrets, PersistentVolumes, Nodes, Namespaces
- **apps/v1** (workloads):
  - Deployments, StatefulSets, DaemonSets, ReplicaSets
- **batch/v1** (jobs):
  - Jobs, CronJobs
- **networking.k8s.io/v1**:
  - Ingresses, NetworkPolicies

### Kubernetes Metrics Collection

**1. Node-Level Metrics**
```python
v1 = client.CoreV1Api()

# List all nodes
nodes = v1.list_node()
for node in nodes.items:
    # Node status
    conditions = node.status.conditions  # Ready, MemoryPressure, DiskPressure, etc.
    capacity = node.status.capacity      # cpu, memory, pods (max allocatable)
    allocatable = node.status.allocatable
    
    # Node info
    node_info = node.status.node_info
    # kubelet_version, os_image, kernel_version, container_runtime
```

**2. Pod-Level Metrics**
```python
# List pods (all namespaces)
pods = v1.list_pod_for_all_namespaces()

for pod in pods.items:
    # Pod status
    phase = pod.status.phase  # Pending, Running, Succeeded, Failed, Unknown
    conditions = pod.status.conditions  # PodScheduled, Ready, Initialized, ContainersReady
    
    # Container statuses
    for container_status in pod.status.container_statuses:
        ready = container_status.ready
        restart_count = container_status.restart_count
        state = container_status.state
        # state.running, state.waiting, state.terminated
        
    # Resource requests/limits
    for container in pod.spec.containers:
        requests = container.resources.requests  # cpu, memory
        limits = container.resources.limits
```

**3. Deployment Metrics**
```python
apps_v1 = client.AppsV1Api()

deployments = apps_v1.list_deployment_for_all_namespaces()
for deploy in deployments.items:
    replicas = deploy.status.replicas
    ready_replicas = deploy.status.ready_replicas
    updated_replicas = deploy.status.updated_replicas
    available_replicas = deploy.status.available_replicas
    
    # Rollout status
    conditions = deploy.status.conditions
    # Type: Progressing, Available, ReplicaFailure
```

**4. Service Monitoring**
```python
services = v1.list_service_for_all_namespaces()
for svc in services.items:
    svc_type = svc.spec.type  # ClusterIP, NodePort, LoadBalancer
    cluster_ip = svc.spec.cluster_ip
    ports = svc.spec.ports
    
    # For LoadBalancer, check external IP
    if svc_type == 'LoadBalancer':
        ingress = svc.status.load_balancer.ingress
```

**5. Resource Usage (Metrics Server required)**
```python
# Requires metrics-server installed in cluster
from kubernetes import client
custom_api = client.CustomObjectsApi()

# Node metrics
node_metrics = custom_api.list_cluster_custom_object(
    group="metrics.k8s.io",
    version="v1beta1",
    plural="nodes"
)

# Pod metrics
pod_metrics = custom_api.list_namespaced_custom_object(
    group="metrics.k8s.io",
    version="v1beta1",
    namespace="default",
    plural="pods"
)
```

**6. Events Monitoring**
```python
# Get events (errors, warnings, normal events)
events = v1.list_event_for_all_namespaces()
for event in events.items:
    event_type = event.type  # Normal, Warning, Error
    reason = event.reason    # e.g., "FailedScheduling", "Pulled"
    message = event.message
    involved_object = event.involved_object  # What resource this event is about
    count = event.count      # How many times event occurred
    first_timestamp = event.first_timestamp
    last_timestamp = event.last_timestamp
```

### Kubernetes Watch API (Real-time Updates)

```python
from kubernetes import watch

w = watch.Watch()

# Watch pods in real-time
for event in w.stream(v1.list_pod_for_all_namespaces):
    event_type = event['type']  # ADDED, MODIFIED, DELETED, ERROR
    pod = event['object']
    # React to pod changes in real-time
```

### Implementation Priority for Unity

**Phase 1: Cluster & Node Health (Week 1)**
```python
# Unity plugin: k8s_cluster.py
- List clusters (from kubeconfig contexts)
- Monitor cluster connection status
- Node health and capacity
- Cluster component status (API server, scheduler, controller-manager)
```

**Phase 2: Workload Monitoring (Week 2)**
```python
# Unity plugin: k8s_workloads.py
- Pod status across all namespaces
- Deployment replica status
- StatefulSet status
- DaemonSet coverage
- Job/CronJob completion
- Container restart counts
```

**Phase 3: Service & Network (Week 3)**
```python
# Unity plugin: k8s_networking.py
- Service endpoints and external IPs
- Ingress rules and backend health
- NetworkPolicy rules
- DNS service availability
```

**Phase 4: Resource Usage (Week 4)**
```python
# Unity plugin: k8s_resources.py
- Node resource utilization (requires metrics-server)
- Pod resource usage
- Resource quota usage per namespace
- PVC (PersistentVolumeClaim) usage
```

### Kubernetes Alerting Examples

```python
# Alert scenarios for Unity
alerts = [
    # Pod alerts
    {"name": "PodCrashLooping", "condition": "restart_count > 5 in 10m"},
    {"name": "PodNotReady", "condition": "pod.status.phase != 'Running' for 5m"},
    {"name": "PodMemoryHigh", "condition": "memory_usage > 90% of limit"},
    
    # Node alerts
    {"name": "NodeNotReady", "condition": "node.status.condition.Ready != True"},
    {"name": "NodeMemoryPressure", "condition": "node.status.condition.MemoryPressure == True"},
    {"name": "NodeDiskPressure", "condition": "node.status.condition.DiskPressure == True"},
    
    # Deployment alerts
    {"name": "DeploymentReplicaMismatch", "condition": "ready_replicas < desired_replicas for 5m"},
    {"name": "DeploymentRolloutStuck", "condition": "rollout not progressing for 10m"},
    
    # Resource alerts
    {"name": "NamespaceQuotaExceeded", "condition": "resource_quota.used > 90% of hard limit"},
    {"name": "PVCNearFull", "condition": "pvc_used > 85% of capacity"},
]
```

### Multi-Cluster Support

```python
# Unity config: k8s_clusters.yaml
clusters:
  - name: production
    kubeconfig: /configs/prod-kubeconfig.yaml
    context: prod-cluster
    priority: critical
    
  - name: staging
    kubeconfig: /configs/staging-kubeconfig.yaml
    context: staging-cluster
    priority: warning
    
  - name: development
    kubeconfig: /configs/dev-kubeconfig.yaml
    context: dev-cluster
    priority: info

# Unity monitors all clusters simultaneously
# Alerts are tagged with cluster name
```

---

## Container Monitoring Best Practices

### 1. Efficient Polling Strategies
- **Stats**: Poll every 5-10 seconds (not every second - too expensive)
- **Events**: Keep streaming connection open (reconnect on failure)
- **Logs**: Optional feature, user-configurable
- **Health checks**: Every 30-60 seconds
- **Discovery**: Re-scan for new containers every 60 seconds

### 2. Data Storage Optimization
```python
# Store time-series data efficiently
# Option 1: Aggregated metrics (save space)
container_metrics_5min_avg = {
    "container_id": "abc123",
    "timestamp": "2024-12-21T12:00:00Z",
    "cpu_avg": 45.2,
    "cpu_max": 89.5,
    "mem_avg": 512MB,
    "mem_max": 890MB,
}

# Option 2: Raw metrics (full fidelity, more space)
# Store every sample point

# Option 3: Hybrid (raw recent, aggregated old)
# Last 24h: raw 10-second samples
# 1-7 days: 1-minute aggregates
# 7-30 days: 5-minute aggregates
# 30+ days: 1-hour aggregates
```

### 3. Label-Based Organization
```python
# Use container labels for grouping
labels = container.labels
project = labels.get('com.docker.compose.project')
service = labels.get('com.docker.compose.service')
environment = labels.get('env')  # prod, staging, dev
team = labels.get('team')

# Enable filtering/grouping in Unity UI
# "Show all production containers"
# "Show containers for project X"
```

### 4. Resource Usage Baselines
```python
# Learn "normal" behavior per container
# Alert on deviations from baseline
baseline = {
    "container": "nginx-web",
    "normal_cpu": "5-15%",
    "normal_memory": "100-150MB",
    "normal_network": "1-5 MB/s",
}

# Alert if container exceeds 2x normal CPU for 5+ minutes
```

---

## Docker/K8s Integration Roadmap

### Phase 2A: Enhanced Docker Monitoring (2 weeks)

**Week 1: Events & Logs**
- [ ] Docker events streaming and storage
- [ ] Container lifecycle event alerts
- [ ] Container log viewer (real-time)
- [ ] Log search and filtering
- [ ] Docker Compose project detection

**Week 2: Health & Images**
- [ ] Container health check monitoring
- [ ] Health history tracking
- [ ] Image vulnerability scanning (Trivy)
- [ ] Unused image detection
- [ ] Volume usage monitoring

### Phase 2B: Podman Support (1 week)
- [ ] Podman socket detection and connection
- [ ] Rootless container support
- [ ] Pod monitoring (Podman-specific)
- [ ] Systemd-managed container detection
- [ ] Quadlet support

### Phase 3A: Basic Kubernetes (2 weeks)

**Week 1: Cluster & Workload Basics**
- [ ] Kubeconfig parsing and cluster connection
- [ ] Node status monitoring
- [ ] Pod status across all namespaces
- [ ] Deployment replica monitoring
- [ ] Kubernetes events

**Week 2: Services & Resources**
- [ ] Service endpoint monitoring
- [ ] Ingress status
- [ ] StatefulSet/DaemonSet support
- [ ] Job/CronJob monitoring
- [ ] Basic resource usage (if metrics-server available)

### Phase 3B: Advanced Kubernetes (2 weeks)

**Week 1: Advanced Features**
- [ ] Multi-cluster support
- [ ] Namespace resource quota monitoring
- [ ] PVC usage tracking
- [ ] ConfigMap/Secret monitoring
- [ ] Custom Resource Definitions (CRD) support

**Week 2: Visualization & Alerts**
- [ ] K8s-specific dashboards
- [ ] Topology view (nodes, pods, services)
- [ ] K8s-specific alert templates
- [ ] Resource optimization recommendations
- [ ] Cost estimation (resource usage x pricing)

---

## Technical Stack for Container Monitoring

### Required Python Libraries
```bash
# Docker/Podman
pip install docker>=7.0.0

# Kubernetes
pip install kubernetes>=29.0.0

# Image scanning
pip install python-trivy  # If available, or shell out to trivy CLI

# WebSocket for real-time updates
pip install websockets>=12.0  # Already in Unity

# Async support (optional, for better performance)
pip install asyncio
pip install aiohttp
```

### Database Schema Additions

```sql
-- Container stats (time-series)
CREATE TABLE container_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL,
    memory_usage INTEGER,
    memory_limit INTEGER,
    network_rx INTEGER,
    network_tx INTEGER,
    block_read INTEGER,
    block_write INTEGER,
    pids INTEGER
);

-- Container events
CREATE TABLE container_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- start, stop, die, kill, etc.
    event_action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    attributes JSON  -- Store event metadata
);

-- Kubernetes resources
CREATE TABLE k8s_pods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    pod_name TEXT NOT NULL,
    pod_phase TEXT,  -- Running, Pending, Failed, etc.
    ready_conditions JSON,
    restart_count INTEGER,
    node_name TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cluster_name, namespace, pod_name)
);
```

### API Endpoints to Add

```python
# New Unity API endpoints
GET /api/containers                    # List all containers
GET /api/containers/{id}/stats         # Container stats history
GET /api/containers/{id}/logs          # Container logs
GET /api/containers/{id}/events        # Container events

GET /api/docker/compose/projects       # List Compose projects
GET /api/docker/images                 # List images
GET /api/docker/images/{id}/vulnerabilities  # Image vulns

GET /api/k8s/clusters                  # List K8s clusters
GET /api/k8s/{cluster}/nodes           # Cluster nodes
GET /api/k8s/{cluster}/pods            # All pods
GET /api/k8s/{cluster}/deployments     # Deployments
GET /api/k8s/{cluster}/events          # K8s events
```

---

**Docker/K8s Integration Status:** Ready for implementation!  
**Next Steps:** Begin Phase 2A (Enhanced Docker Monitoring) after authentication work begins.

