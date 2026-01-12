# Blueprint Mapping Guide

This document shows how parsed intents map to Kubernetes/Docker deployments.

## Intent to Kubernetes Manifest Flow

```
Natural Language → Intent Parser → Deployment Intent → Blueprint → K8s Manifest → Deployed
```

## Example Mappings

### 1. PostgreSQL Installation

**Natural Language Command:**
```
"install postgres with 10GB storage"
```

**Parsed Intent:**
```json
{
  "action": "install",
  "application": "postgresql",
  "confidence": 0.90,
  "parameters": {
    "storage": "10Gi",
    "version": "16",
    "replicas": 1
  },
  "dependencies": [],
  "suggested_platform": "kubernetes"
}
```

**Generated Kubernetes Manifests:**

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: databases
  labels:
    managed-by: unity
---
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: databases
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: local-path
---
# statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
  namespace: databases
  labels:
    app: postgresql
    managed-by: unity
spec:
  serviceName: postgresql
  replicas: 1
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      containers:
      - name: postgresql
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: password
        - name: POSTGRES_DB
          value: postgres
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
          subPath: postgres
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: postgres-data
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgresql
  namespace: databases
  labels:
    app: postgresql
spec:
  type: ClusterIP
  ports:
  - port: 5432
    targetPort: 5432
    protocol: TCP
    name: postgres
  selector:
    app: postgresql
---
# secret.yaml (auto-generated password)
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
  namespace: databases
type: Opaque
stringData:
  password: <AUTO_GENERATED_PASSWORD>
  username: postgres
```

---

### 2. Authentik with Dependencies

**Natural Language Command:**
```
"install authentik on auth.homelab.local"
```

**Parsed Intent:**
```json
{
  "action": "install",
  "application": "authentik",
  "confidence": 0.95,
  "parameters": {
    "domain": "auth.homelab.local",
    "storage": "5Gi",
    "replicas": 1
  },
  "dependencies": ["postgresql", "redis"],
  "suggested_platform": "kubernetes"
}
```

**Deployment Sequence:**

1. **Install PostgreSQL** (dependency)
   - Creates `databases` namespace
   - Deploys PostgreSQL StatefulSet with 10Gi storage
   - Creates database `authentik`

2. **Install Redis** (dependency)
   - Creates Redis Deployment in `databases` namespace
   - Configures 1Gi storage for persistence

3. **Install Authentik** (main application)

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: authentik
  labels:
    managed-by: unity
---
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: authentik-media
  namespace: authentik
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
# deployment-server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: authentik-server
  namespace: authentik
  labels:
    app: authentik
    component: server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: authentik
      component: server
  template:
    metadata:
      labels:
        app: authentik
        component: server
    spec:
      containers:
      - name: authentik
        image: ghcr.io/goauthentik/server:2024.2
        args:
        - server
        env:
        - name: AUTHENTIK_REDIS__HOST
          value: redis.databases.svc.cluster.local
        - name: AUTHENTIK_POSTGRESQL__HOST
          value: postgresql.databases.svc.cluster.local
        - name: AUTHENTIK_POSTGRESQL__NAME
          value: authentik
        - name: AUTHENTIK_POSTGRESQL__USER
          value: authentik
        - name: AUTHENTIK_POSTGRESQL__PASSWORD
          valueFrom:
            secretKeyRef:
              name: authentik-db-credentials
              key: password
        - name: AUTHENTIK_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: authentik-secrets
              key: secret-key
        ports:
        - containerPort: 9000
          name: http
        - containerPort: 9443
          name: https
        volumeMounts:
        - name: media
          mountPath: /media
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
      volumes:
      - name: media
        persistentVolumeClaim:
          claimName: authentik-media
---
# deployment-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: authentik-worker
  namespace: authentik
spec:
  replicas: 1
  selector:
    matchLabels:
      app: authentik
      component: worker
  template:
    metadata:
      labels:
        app: authentik
        component: worker
    spec:
      containers:
      - name: authentik
        image: ghcr.io/goauthentik/server:2024.2
        args:
        - worker
        env:
        - name: AUTHENTIK_REDIS__HOST
          value: redis.databases.svc.cluster.local
        - name: AUTHENTIK_POSTGRESQL__HOST
          value: postgresql.databases.svc.cluster.local
        - name: AUTHENTIK_POSTGRESQL__NAME
          value: authentik
        - name: AUTHENTIK_POSTGRESQL__USER
          value: authentik
        - name: AUTHENTIK_POSTGRESQL__PASSWORD
          valueFrom:
            secretKeyRef:
              name: authentik-db-credentials
              key: password
        volumeMounts:
        - name: media
          mountPath: /media
      volumes:
      - name: media
        persistentVolumeClaim:
          claimName: authentik-media
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: authentik
  namespace: authentik
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 9000
    protocol: TCP
    name: http
  - port: 443
    targetPort: 9443
    protocol: TCP
    name: https
  selector:
    app: authentik
    component: server
---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: authentik
  namespace: authentik
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  ingressClassName: traefik
  tls:
  - hosts:
    - auth.homelab.local
    secretName: authentik-tls
  rules:
  - host: auth.homelab.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: authentik
            port:
              number: 80
```

---

### 3. Nginx Scaling

**Natural Language Command:**
```
"scale nginx to 3 replicas"
```

**Parsed Intent:**
```json
{
  "action": "scale",
  "application": "nginx",
  "confidence": 1.0,
  "parameters": {
    "replicas": 3
  },
  "dependencies": [],
  "suggested_platform": "kubernetes"
}
```

**Kubernetes Action:**
```bash
kubectl scale deployment nginx --replicas=3 -n default
```

Or via API:
```json
PATCH /apis/apps/v1/namespaces/default/deployments/nginx
{
  "spec": {
    "replicas": 3
  }
}
```

---

### 4. Traefik with TLS

**Natural Language Command:**
```
"deploy traefik with letsencrypt on *.homelab.local"
```

**Parsed Intent:**
```json
{
  "action": "install",
  "application": "traefik",
  "confidence": 0.92,
  "parameters": {
    "tls": true,
    "letsencrypt": true,
    "domain": "*.homelab.local",
    "email": "admin@homelab.local",
    "replicas": 2
  },
  "dependencies": ["cert-manager"],
  "suggested_platform": "kubernetes"
}
```

**Generated Manifests:**

```yaml
# 1. Install cert-manager (dependency)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# 2. ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@homelab.local
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik

# 3. Traefik deployment (full configuration would be extensive)
# Would use official Traefik Helm chart or custom manifests
```

---

## Blueprint Template System

### Template Structure

```
blueprints/
├── postgresql/
│   ├── manifest.yaml.j2         # Jinja2 template
│   ├── defaults.yaml            # Default values
│   └── README.md                # Documentation
├── redis/
├── nginx/
├── authentik/
│   ├── server.yaml.j2
│   ├── worker.yaml.j2
│   ├── ingress.yaml.j2
│   └── defaults.yaml
└── traefik/
```

### Template Variables (Jinja2)

```yaml
# postgresql/manifest.yaml.j2
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ app_name }}
  namespace: {{ namespace }}
spec:
  replicas: {{ replicas | default(1) }}
  template:
    spec:
      containers:
      - name: postgresql
        image: postgres:{{ version | default("16") }}-alpine
        env:
        - name: POSTGRES_DB
          value: {{ database_name | default("postgres") }}
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: {{ app_name }}-data
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ app_name }}-data
  namespace: {{ namespace }}
spec:
  resources:
    requests:
      storage: {{ storage | default("10Gi") }}
```

### Rendering Process

```python
from jinja2 import Environment, FileSystemLoader

def render_blueprint(app_name: str, intent: Dict[str, Any]) -> List[str]:
    """
    Render Kubernetes manifests from blueprint templates.

    Args:
        app_name: Application name (e.g., "postgresql")
        intent: Parsed deployment intent

    Returns:
        List of rendered YAML manifests
    """
    # Load template
    env = Environment(loader=FileSystemLoader("blueprints"))
    template = env.get_template(f"{app_name}/manifest.yaml.j2")

    # Prepare template variables from intent
    variables = {
        "app_name": app_name,
        "namespace": intent["parameters"].get("namespace", "default"),
        "replicas": intent["parameters"].get("replicas", 1),
        "storage": intent["parameters"].get("storage", "10Gi"),
        "version": intent["parameters"].get("version"),
        "domain": intent["parameters"].get("domain"),
        # ... more parameters
    }

    # Render template
    rendered = template.render(**variables)

    # Split into individual manifests
    manifests = rendered.split("---")

    return [m.strip() for m in manifests if m.strip()]
```

---

## Parameter Mapping Reference

### Storage Parameters

| Intent Parameter | Kubernetes Equivalent |
|-----------------|----------------------|
| `storage: "10GB"` | `resources.requests.storage: "10Gi"` |
| `storage: "1TB"` | `resources.requests.storage: "1Ti"` |

### Replica Parameters

| Intent Parameter | Kubernetes Equivalent |
|-----------------|----------------------|
| `replicas: 3` | `spec.replicas: 3` |

### Version Parameters

| Intent Parameter | Kubernetes Equivalent |
|-----------------|----------------------|
| `version: "16"` | `image: postgres:16-alpine` |
| `version: "latest"` | `image: postgres:latest` |

### Domain/Ingress Parameters

| Intent Parameter | Kubernetes Equivalent |
|-----------------|----------------------|
| `domain: "app.example.com"` | `spec.rules[0].host: "app.example.com"` |
| `tls: true` | Add `spec.tls` section |
| `letsencrypt: true` | Add cert-manager annotation |

### Resource Parameters

| Intent Parameter | Kubernetes Equivalent |
|-----------------|----------------------|
| `memory: "2Gi"` | `resources.limits.memory: "2Gi"` |
| `cpu: "1000m"` | `resources.limits.cpu: "1000m"` |

---

## Next Steps: Blueprint Loader

The next component to build would be:

```python
# app/services/orchestration/blueprint_loader.py

class BlueprintLoader:
    """Load and render application blueprints"""

    def __init__(self, blueprint_dir: str):
        self.blueprint_dir = blueprint_dir
        self.env = Environment(loader=FileSystemLoader(blueprint_dir))

    async def load_blueprint(self, app_name: str) -> Dict[str, Any]:
        """Load blueprint metadata and templates"""
        pass

    async def render_manifests(
        self,
        app_name: str,
        intent: Dict[str, Any]
    ) -> List[str]:
        """Render Kubernetes manifests from intent"""
        pass

    async def validate_manifests(self, manifests: List[str]) -> bool:
        """Validate rendered manifests"""
        pass
```

This would integrate with the Intent Parser to complete the flow:

```
Natural Language → Intent Parser → Blueprint Loader → K8s Client → Deployed
```
