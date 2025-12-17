# Unity Architecture Documentation

**Version**: 2.0 (Post-Refactoring)  
**Last Updated**: December 16, 2025  
**Status**: Production Ready

## Overview

Unity is a FastAPI-based homelab intelligence hub for monitoring and managing infrastructure, containers, and services. The architecture follows a clean, modular design with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│                  Modern UI Components                    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  Routers   │  │  Services   │  │   Core Config   │  │
│  │  (API)     │──│  (Logic)    │──│   Database      │  │
│  └────────────┘  └─────────────┘  └─────────────────┘  │
│         │                │                   │           │
│  ┌──────┴────────┬───────┴────────┬─────────┴────────┐  │
│  │   Schemas     │    Models      │     Utils        │  │
│  │  (Pydantic)   │  (SQLAlchemy)  │   (Helpers)      │  │
│  └───────────────┴────────────────┴──────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│              PostgreSQL Database                         │
│         (Servers, Metrics, Alerts, Plugins)             │
└─────────────────────────────────────────────────────────┘
```

## Module Architecture

### Core Layer (`app/core/`)
**Purpose**: Fundamental application configuration and database management

- `config.py` - Centralized settings using pydantic-settings (30+ config options)
- `database.py` - SQLAlchemy engine, session management, Base model

**Design Decision**: Centralized configuration eliminates scattered settings and provides type-safe config access.

### Models Layer (`app/models/`)
**Purpose**: SQLAlchemy ORM models representing database schema

**Organization**:
- `core.py` - Core entities (ServerProfile, KnowledgeBase)
- `users.py` - User authentication and authorization
- `monitoring.py` - Alerts, thresholds, notifications
- `infrastructure.py` - Servers, storage, networks, databases
- `containers.py` - Docker/Kubernetes container management
- `credentials.py` - Secure credential storage
- `plugins.py` - Plugin system models
- `alert_rules.py` - Alert rule definitions
- `error_tracking.py` - Error logging and tracking

**Design Decision**: Domain-driven organization makes models easy to locate and maintain.

### Schemas Layer (`app/schemas/`)
**Purpose**: Pydantic models for request/response validation

**Organization** (9 modules):
- `core.py` - Core schemas (profiles, snapshots)
- `users.py` - User schemas
- `alerts.py` - Alert and threshold schemas
- `credentials.py` - Credential schemas
- `knowledge.py` - Knowledge base schemas
- `notifications.py` - Notification schemas
- `plugins.py` - Plugin schemas
- `reports.py` - Report schemas

**Design Decision**: Mirrors model organization for consistency and discoverability.

### Services Layer (`app/services/`)
**Purpose**: Business logic and external integrations

**Organization** (7 modules):

1. **`auth/`** - Authentication & JWT
   - `auth_service.py` - JWT token management, password hashing

2. **`monitoring/`** - Monitoring & alerting
   - `threshold_monitor.py` - Threshold evaluation
   - `alert_channels.py` - Alert delivery (email, slack, webhooks)
   - `notification_service.py` - Notification management
   - `push_notifications.py` - Web push notifications

3. **`plugins/`** - Plugin system
   - `plugin_manager.py` - Plugin lifecycle management
   - `plugin_registry.py` - Plugin discovery and registration
   - `plugin_security.py` - API key authentication, rate limiting

4. **`core/`** - Core services
   - `snapshot_service.py` - System snapshot management
   - `system_info.py` - System information collection
   - `report_generation.py` - Report generation
   - `ssh.py` - SSH connection management
   - `encryption.py` - Data encryption utilities

5. **`ai/`** - AI integration
   - `ai.py` - AI service orchestration
   - `ai_provider.py` - Multiple AI provider support (OpenAI, Anthropic, etc.)

6. **`containers/`** - Container management (Docker, K8s)
   - Multiple runtime providers
   - Security scanning (Trivy)
   - Update management
   - Health monitoring

7. **`credentials/`** - Credential management
   - Certificate providers (Let's Encrypt, ZeroSSL)
   - SSH key management
   - Secure storage and distribution

8. **`infrastructure/`** - Infrastructure monitoring
   - Server discovery
   - Storage monitoring (mdadm, ZFS, LVM)
   - Database monitoring (PostgreSQL, MySQL)
   - Network monitoring

**Design Decision**: Service layer isolates business logic from API layer, enabling reuse and easier testing.

### Routers Layer (`app/routers/`)
**Purpose**: FastAPI route definitions and request handling

**Organization**:

**Modular Routers** (2 directories):
- `plugins/` - Plugin-related endpoints
  - `legacy.py` - v1 plugin API
  - `v2.py` - v2 plugin architecture
  - `v2_secure.py` - Production v2 API with security
  - `keys.py` - API key management

- `monitoring/` - Monitoring endpoints
  - `alerts.py` - Alert management
  - `thresholds.py` - Threshold configuration
  - `push.py` - Push notification subscriptions

**Flat Routers** (12 files):
- `auth.py`, `users.py` - Authentication
- `profiles.py` - Server profiles
- `system.py` - System endpoints
- `ai.py` - AI integration
- `settings.py` - Application settings
- `reports.py` - Report generation
- `knowledge.py` - Knowledge base
- `terminal.py` - Terminal access
- `containers.py` - Container management
- `credentials.py` - Credential management
- `infrastructure.py` - Infrastructure monitoring

**Design Decision**: Hybrid organization - group fragmented routers (plugins), keep single-purpose routers flat.

### Utils Layer (`app/utils/`)
**Purpose**: Reusable utility functions

- `parsers.py` - System command parsers (lsblk, smartctl, nvme, zpool, lvm)

**Design Decision**: Minimal utility layer - domain-specific helpers stay in services.

## Data Flow

### Typical Request Flow

```
1. Client Request
   │
   ↓
2. Router (FastAPI endpoint)
   │ - Request validation (Pydantic schema)
   │ - Authentication check
   │ - Authorization
   ↓
3. Service Layer
   │ - Business logic execution
   │ - External service calls
   │ - Data transformation
   ↓
4. Database Layer (via ORM)
   │ - Query execution
   │ - Transaction management
   ↓
5. Response
   │ - Data serialization (Pydantic)
   │ - HTTP response
   ↓
6. Client receives response
```

### Plugin System Flow

```
External Plugin
   │
   ↓ HTTP Request (API Key Auth)
Plugin Router (v2_secure)
   │
   ↓ Validate API Key
Plugin Security Service
   │
   ↓ Rate Limit Check
Plugin Manager
   │
   ↓ Store Metrics/Health
Database
   │
   ↓ Response
External Plugin
```

## Design Principles

### 1. Separation of Concerns
- **Routers**: Handle HTTP, validation, auth
- **Services**: Implement business logic
- **Models**: Define data structure
- **Schemas**: Validate input/output

### 2. Dependency Injection
- FastAPI's dependency system for database sessions
- Service dependencies injected via function parameters
- Easy to mock for testing

### 3. Configuration Management
- Single source of truth (`app.core.config.Settings`)
- Environment variable support
- Type-safe configuration access

### 4. Security
- JWT-based authentication
- API key authentication for external plugins
- Rate limiting on sensitive endpoints
- Input validation via Pydantic
- Secure credential storage

### 5. Modularity
- Clear module boundaries
- Minimal inter-module dependencies
- Easy to add new features without touching existing code

### 6. Testability
- In-memory database for tests
- Comprehensive fixtures
- Test markers for categorization
- 48 tests with good coverage

## Technology Stack

### Backend
- **Framework**: FastAPI 0.100+
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic 2.0
- **Database**: PostgreSQL (primary), SQLite (testing)
- **Auth**: JWT (python-jose)
- **Password Hashing**: bcrypt
- **Scheduling**: APScheduler
- **Testing**: pytest, httpx

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Python**: 3.11+
- **Package Management**: pip, uv

## Key Features

### 1. Server Monitoring
- System metrics collection
- Storage device monitoring (SMART)
- Network monitoring
- Database instance tracking

### 2. Container Management
- Multi-runtime support (Docker, Kubernetes, Podman)
- Security scanning
- Update management
- Health monitoring

### 3. Plugin System
- External plugin support
- Secure API key authentication
- Metrics and health reporting
- Plugin lifecycle management

### 4. Alert System
- Threshold-based alerting
- Multiple notification channels
- Alert rule management
- Cooldown and muting support

### 5. Credential Management
- Secure storage
- Multiple credential types (SSH, certs, API keys)
- Certificate automation (Let's Encrypt)

### 6. AI Integration
- Multiple provider support
- Natural language querying
- System analysis and recommendations

## Performance Considerations

### Database
- Connection pooling via SQLAlchemy
- Indexed queries for common operations
- Efficient ORM relationships

### Caching
- In-memory caching for plugin registry
- Configuration caching

### Async Operations
- FastAPI async support
- Background job scheduling with APScheduler
- Non-blocking I/O for external calls

## Security Architecture

### Authentication Layers
1. **User Authentication**: JWT tokens
2. **Plugin Authentication**: API keys
3. **Service-to-Service**: Internal auth

### Data Protection
- Passwords hashed with bcrypt
- Sensitive data encrypted at rest
- Secure credential storage
- API key hashing

### API Security
- Rate limiting on sensitive endpoints
- Input validation via Pydantic
- SQL injection prevention via ORM
- CORS configuration

## Scalability

### Current Scale
- Single instance deployment
- PostgreSQL backend
- Suitable for homelabs and small deployments

### Future Scaling Options
- Redis for distributed caching
- Message queue for async processing
- Load balancer for multiple instances
- Read replicas for database

## Development Workflow

### Adding New Features

1. **Define Models** (`app/models/`)
2. **Create Schemas** (`app/schemas/`)
3. **Implement Service** (`app/services/`)
4. **Add Router** (`app/routers/`)
5. **Write Tests** (`backend/tests/`)
6. **Update Documentation**

### Testing Strategy
- Unit tests for business logic
- Integration tests for workflows
- API tests for endpoints
- Database tests with in-memory SQLite

## Migration from Old Structure

See `MIGRATION_GUIDE.md` for detailed migration instructions.

## Future Architecture Considerations

### Phase 2: UI/UX Improvements
- Modern React frontend
- Real-time WebSocket updates
- Improved visualization

### Phase 3: Plugin Library
- Plugin marketplace
- Community plugins
- Plugin templates

### Advanced Features
- Multi-tenancy support
- Advanced RBAC
- Audit logging
- Metrics aggregation

## Conclusion

The refactored architecture provides a solid, maintainable foundation for Unity's continued development. Clear module boundaries, comprehensive testing, and detailed documentation enable rapid feature development while maintaining code quality.

For specific module documentation, see:
- `PROJECT-STRUCTURE.md` - Detailed file structure
- `MIGRATION_GUIDE.md` - Migration instructions
- `backend/tests/README.md` - Testing documentation
- `CONTRIBUTING.md` - Development guidelines
