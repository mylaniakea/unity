# Semantic AI Orchestration System

Unity's semantic AI orchestration system enables users to deploy applications by simply specifying the app name. The system automatically figures out dependencies, configurations, networking, storage, and wiring.

## Architecture

### Components

1. **Blueprint Loader** (`blueprint_loader.py`)
   - Loads application blueprints from YAML files or database
   - Validates blueprint structure
   - Supports searching and filtering blueprints

2. **Manifest Generator** (`manifest_generator.py`)
   - Generates Kubernetes manifests (Deployments, Services, Ingress, etc.)
   - Generates Docker Compose files
   - Template variable substitution using Jinja2
   - Platform selection (Kubernetes vs Docker)

3. **Auto-Wiring Engine** (`auto_wiring.py`)
   - Automatically infers configuration variables
   - Generates secrets (passwords, JWT keys, encryption keys)
   - Creates ConfigMaps for non-sensitive config
   - Sets up networking (Services, Ingress)
   - Provisions storage (PVCs)
   - Wires service dependencies

## Usage

### Deploy an Application

```bash
POST /api/orchestration/deploy
Content-Type: application/json

{
  "app_name": "my-webapp",
  "environment": "production"
}
```

That's it! The system will:
1. Select appropriate blueprint (webapp)
2. Infer database connection strings
3. Generate secure passwords
4. Set up PostgreSQL and Redis
5. Configure networking and ingress
6. Generate all Kubernetes manifests

### Optional Parameters

```json
{
  "app_name": "my-webapp",
  "blueprint": "webapp",
  "platform": "kubernetes",
  "namespace": "production",
  "environment": "production",
  "domain": "myapp.example.com",
  "image": "ghcr.io/myorg/myapp:v1.0.0",
  "variables": {
    "replicas": 3,
    "cpu_limit": "1000m"
  }
}
```

### Dry Run

Generate deployment plan without actually deploying:

```bash
POST /api/orchestration/deploy?dry_run=true
```

### List Blueprints

```bash
GET /api/orchestration/blueprints
GET /api/orchestration/blueprints?category=web
```

### Get Blueprint Details

```bash
GET /api/orchestration/blueprints/webapp
```

## Blueprints

### Available Blueprints

1. **webapp** - Full-stack web application
   - PostgreSQL database
   - Redis cache
   - Authentication & encryption
   - Ingress with TLS

2. **simple-service** - Stateless microservice
   - No dependencies
   - Minimal resources
   - Quick deployment

3. **database** - PostgreSQL database
   - StatefulSet with persistent storage
   - Optimized resources

### Blueprint Structure

```yaml
metadata:
  name: webapp
  display_name: "Generic Web Application"
  description: "Web application with database and cache"
  version: "1.0.0"
  category: "web"
  tags: ["web", "fullstack"]
  preferred_platform: kubernetes

requirements:
  port: 8080
  database:
    type: postgresql
    version: "16"
  cache:
    type: redis
  storage:
    volumes:
      - name: data
        size: 10Gi
  resources:
    cpu:
      request: "100m"
      limit: "500m"
    memory:
      request: "128Mi"
      limit: "512Mi"
  ingress:
    enabled: true

defaults:
  namespace: default
  replicas: 1

templates:
  kubernetes:
    deployment:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{ app_name }}"
      # ... rest of template
```

## Auto-Wiring Examples

### Database Connection

**Input:**
```yaml
requirements:
  database:
    type: postgresql
```

**Auto-generated:**
- `DATABASE_HOST=my-webapp-postgres`
- `DATABASE_PORT=5432`
- `DATABASE_NAME=my-webapp`
- `DATABASE_USER=my-webapp`
- `DATABASE_PASSWORD=<generated secure password>`
- `DATABASE_URL=postgresql://my-webapp:<password>@my-webapp-postgres:5432/my-webapp`

### Redis Connection

**Input:**
```yaml
requirements:
  cache:
    type: redis
```

**Auto-generated:**
- `REDIS_HOST=my-webapp-redis`
- `REDIS_PORT=6379`
- `REDIS_PASSWORD=<generated secure password>`
- `REDIS_URL=redis://:<password>@my-webapp-redis:6379/0`

### Secrets

Auto-generated secrets:
- Database passwords (32 chars, alphanumeric)
- Redis passwords (32 chars, alphanumeric)
- JWT secret keys (64 bytes hex)
- Fernet encryption keys (base64-encoded)

### Networking

**Service:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-webapp
spec:
  selector:
    app: my-webapp
  ports:
    - port: 8080
  type: ClusterIP
```

**Ingress (if enabled):**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-webapp
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: traefik
  tls:
    - hosts: [myapp.example.com]
      secretName: my-webapp-tls
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: my-webapp
                port:
                  number: 8080
```

## Platform Selection

The system automatically selects the best platform:

### Kubernetes
Used for:
- High availability requirements
- Scaling requirements
- Production workloads
- Stateful applications

### Docker Compose
Used for:
- Simple single-instance services
- Development environments
- Quick deployments
- Lightweight services

## Creating Custom Blueprints

1. Create YAML file in `/app/blueprints/`
2. Define metadata, requirements, defaults, and templates
3. Blueprint is automatically discovered

Example minimal blueprint:

```yaml
metadata:
  name: my-service
  version: "1.0.0"

requirements:
  port: 8080

templates:
  kubernetes:
    deployment:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{ app_name }}"
      spec:
        replicas: 1
        selector:
          matchLabels:
            app: "{{ app_name }}"
        template:
          metadata:
            labels:
              app: "{{ app_name }}"
          spec:
            containers:
              - name: "{{ app_name }}"
                image: "{{ image }}"
                ports:
                  - containerPort: {{ port }}
```

## API Reference

### Deploy Application

**Endpoint:** `POST /api/orchestration/deploy`

**Request Body:**
```typescript
{
  app_name: string;          // Required
  blueprint?: string;        // Optional (auto-detected)
  platform?: string;         // Optional (kubernetes/docker)
  namespace?: string;        // Default: "default"
  environment?: string;      // Default: "production"
  domain?: string;          // Optional (for ingress)
  image?: string;           // Optional (uses registry/org/app_name)
  variables?: object;       // Optional custom variables
}
```

**Response:**
```typescript
{
  success: boolean;
  message: string;
  plan?: {
    app_name: string;
    blueprint: string;
    platform: string;
    namespace: string;
    manifests: object[];      // K8s manifests
    files: object;            // filename -> YAML content
    secrets: object;          // secret key -> value
    inferred_variables: object;
    dependencies: string[];
    validation_warnings: string[];
  };
  deployment_id?: number;
  errors?: string[];
}
```

### List Blueprints

**Endpoint:** `GET /api/orchestration/blueprints`

**Query Parameters:**
- `category` - Filter by category (web, database, microservice, etc.)

**Response:**
```typescript
[
  {
    name: string;
    display_name: string;
    description: string;
    version: string;
    category: string;
    tags: string[];
  }
]
```

### Get Blueprint

**Endpoint:** `GET /api/orchestration/blueprints/{blueprint_name}`

**Response:** Full blueprint object

### Search Blueprints

**Endpoint:** `POST /api/orchestration/blueprints/search`

**Request Body:**
```typescript
{
  query?: string;     // Search in name and description
  category?: string;  // Filter by category
  tags?: string[];    // Filter by tags
}
```

## Testing

```bash
# Test blueprint loading
curl http://localhost:8000/api/orchestration/blueprints

# Test deployment (dry run)
curl -X POST http://localhost:8000/api/orchestration/deploy?dry_run=true \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"app_name": "test-app"}'
```

## Future Enhancements

- [ ] Actual deployment to Kubernetes (kubectl apply)
- [ ] Docker Compose deployment (docker-compose up)
- [ ] Multi-cluster support
- [ ] Rollback capabilities
- [ ] Health monitoring integration
- [ ] Cost estimation
- [ ] Blueprint marketplace
- [ ] AI-powered blueprint recommendations
- [ ] Automatic dependency resolution
- [ ] GitOps integration
