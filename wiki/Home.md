# Unity - Unified Homelab Infrastructure Monitoring

Welcome to the Unity platform documentation! Unity is a comprehensive homelab infrastructure monitoring and automation platform that brings together credential management, infrastructure monitoring, and container automation into a single, powerful solution.

## 🎉 Current Status: **PRODUCTION READY** (v1.0.0)

**All 4 phases successfully integrated!** ✅
- **Phase 1**: KC-Booth Credential Management - Complete
- **Phase 2**: User Management & RBAC - Complete
- **Phase 3**: BD-Store Infrastructure Monitoring - Complete
- **Phase 4**: Uptainer Container Automation - Complete

**Integration Status**: 100% Complete (December 16, 2025)

### Quick Stats
- **146 API Endpoints** across all phases
- **45+ Database Tables** properly migrated
- **3 Services** running (Backend, Database, Frontend)
- **4 Major Features** fully integrated

## 🎯 Project Vision

Unity consolidates three specialized homelab management tools into one unified platform:
- **KC-Booth**: Secure credential and certificate management
- **BD-Store**: Infrastructure monitoring (servers, storage, databases)
- **Uptainer**: Automated container updates with AI recommendations

## 🚀 Quick Start

### Access Points
- **Frontend UI**: http://localhost:80
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Default Credentials
- **Username**: admin
- **Password**: admin123
- ⚠️ **Change immediately after first login!**

### Getting Started
```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# Access the application
open http://localhost:80
```

See [[Quick Start Guide]] for detailed instructions.

## 📚 Documentation Index

### Getting Started
- [[Quick Start Guide]] - Start here!
- [[Installation]] - Deployment guide
- [[Configuration]] - Environment setup
- [[Architecture Overview]] - System design

### Features by Phase

#### Phase 1: Credential Management ✅
- [[Credential Management]] (KC-Booth Integration)
- SSH key management
- Certificate management with StepCA
- Server credential storage
- Audit logging
- **23 API Endpoints**

#### Phase 2: User Management & RBAC ✅
- [[Authentication]] - JWT-based auth
- Role-Based Access Control
- User management
- Password policies
- **9 API Endpoints**

#### Phase 3: Infrastructure Monitoring ✅
- [[Infrastructure Monitoring]] (BD-Store Integration)
- Server monitoring via SSH
- Storage monitoring (RAID, disks)
- Database metrics (MySQL, PostgreSQL)
- Alert rules and thresholds
- Data retention policies
- **23 API Endpoints**

#### Phase 4: Container Automation ✅
- [[Container Automation]] (Uptainer Integration)
- Multi-runtime support (Docker, Podman, K8s)
- Container lifecycle management
- Update policies and scheduling
- Security scanning integration
- Backup and restore
- AI-powered recommendations
- **26 API Endpoints**

### Core Features
- [[Plugin System]] - Extensible architecture
- [[Alert System]] - Threshold-based alerts
- [[AI Integration]] - LLM-powered insights
- [[Scheduler]] - Automated task execution

### Integration Documentation
- [[Integration Overview]] - Complete integration guide
- [[Phase 1-2: KC-Booth Integration]] - Credential & Auth phases
- [[Phase 3: BD-Store Integration]] - Infrastructure phase
- [[Phase 4: Uptainer Integration]] - Container phase
- [[Integration Patterns]] - Common patterns and practices

### API Documentation
- [[API Overview]] - REST API introduction
- [[Authentication]] - Auth endpoints and JWT
- [[Credentials API]] - Phase 1 endpoints
- [[Infrastructure API]] - Phase 3 endpoints
- [[Containers API]] - Phase 4 endpoints
- [[Core API]] - Users, profiles, system

### Development
- [[Development Setup]] - Local development
- [[Database Schema]] - Complete schema docs
- [[Service Layer Architecture]] - Backend structure
- [[Adding New Features]] - Contribution guide
- [[Testing Guide]] - Test infrastructure
- [[Contributing]] - How to contribute

## 🏗️ Architecture

Unity uses a modern, scalable architecture:

### Technology Stack
- **Backend**: FastAPI (Python 3.11) with SQLAlchemy ORM
- **Database**: PostgreSQL 16
- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS
- **Deployment**: Docker Compose
- **Scheduler**: APScheduler for background tasks

### Key Components
1. **API Layer**: RESTful API with OpenAPI documentation
2. **Service Layer**: Business logic and integrations
3. **Data Layer**: PostgreSQL with proper migrations
4. **Scheduler**: Background tasks for automation
5. **Plugin System**: Extensible plugin architecture

## 📊 System Capabilities

### Credential Management (Phase 1)
- Generate and manage SSH keys
- Certificate lifecycle with StepCA
- Secure credential storage with encryption
- Audit logging for compliance
- Server credential association

### User Management (Phase 2)
- JWT-based authentication
- Role-based access control (Admin, User, Viewer)
- User CRUD operations
- Password management and resets
- Session management

### Infrastructure Monitoring (Phase 3)
- SSH-based server monitoring
- Storage device tracking (HDD, SSD, RAID)
- Database instance monitoring
- Alert rules with threshold evaluation
- Automated data collection (5-minute intervals)
- Data retention and cleanup

### Container Management (Phase 4)
- Docker, Podman, and Kubernetes support
- Container discovery and monitoring
- Update checking and management
- Policy-based automated updates
- Security vulnerability scanning
- Container backup and restore
- AI-powered update recommendations

## 🔧 Configuration

See [[Configuration]] for complete environment variable reference.

### Essential Environment Variables
```bash
# Database
DATABASE_URL=postgresql://homelab:password@db:5432/homelab_intelligence

# Security
SECRET_KEY=your-secret-key-here

# AI Providers (Optional)
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key

# Container Features
ENABLE_CONTAINERS=true
ENABLE_TRIVY=false
ENABLE_CONTAINER_AI=false
```

## 📝 Recent Updates

### December 16, 2025 - Phase 4 Integration Complete ✅
- Merged Uptainer container automation
- 26 new container management endpoints
- 12 new database models
- Comprehensive testing suite
- Full integration with Phases 1-3
- Production-ready deployment

### Key Achievements
- **Zero breaking changes** across integration
- **Backward compatible** with all phases
- **Clean merge** with no conflicts
- **Comprehensive documentation**
- **Production-ready** architecture

## 🎯 Production Readiness

### Status Dashboard
```
Phase 1 (KC-Booth):       ████████████████████ 100%
Phase 2 (RBAC):           ████████████████████ 100%
Phase 3 (Infrastructure): ████████████████████ 100%
Phase 4 (Containers):     ████████████████████ 100%
Integration:              ████████████████████ 100%
Documentation:            ████████████████████ 100%
Testing:                  ████████████░░░░░░░░  70%
Production Ready:         ████████████████░░░░  85%
```

### What's Working
- ✅ All API endpoints functional
- ✅ Database properly migrated
- ✅ Authentication and RBAC enforced
- ✅ Frontend accessible
- ✅ All services running
- ✅ OpenAPI documentation complete

### Next Steps
1. Change default admin password
2. Configure infrastructure servers
3. Add container hosts
4. Set up alert channels
5. Configure AI providers (optional)

## 🤝 Contributing

We welcome contributions! See [[Contributing]] for guidelines.

### Ways to Contribute
- Report bugs and issues
- Suggest new features
- Improve documentation
- Submit pull requests
- Share your use cases

## 📖 Additional Resources

### Documentation Files
- `README.md` - Project overview
- `START_HERE.md` - Quick start guide
- `INTEGRATION-COMPLETE.md` - Phase 1-4 integration summary
- `PHASE-4-FINAL-SUMMARY.md` - Complete Phase 4 details

### Moonshot Ideas 🚀
- `MOONSHOT.md` - Ambitious ideas and future possibilities
- `ROADMAP.md` - Development roadmap and phases

### API Documentation
Visit http://localhost:8000/docs for interactive API documentation (Swagger UI)

### Support
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share ideas
- Wiki: Comprehensive documentation (you are here!)

## 📄 License

See LICENSE file for details.

---

**Project**: Unity - Unified Homelab Intelligence  
**Version**: 1.0.0-phase-4-complete  
**Status**: ✅ Production Ready  
**Last Updated**: December 16, 2025

Welcome aboard! 🚀

---

## 🔄 Current Development: Codebase Refactoring

**Status**: ✅ Complete (100%)  
**Branch**: `feature/kc-booth-integration`  
**Goal**: Improve code organization, maintainability, and developer experience

### Refactoring Progress

**Completed Phases**:
- ✅ **Phase 1**: Schema Organization (2.5 hours) - 9 organized schema modules
- ✅ **Phase 2**: Core Configuration (2 hours) - Centralized config with 30+ settings
- ✅ **Phase 3**: Service Layer Organization (3 hours) - 57 services into 7 modules
- ✅ **Phase 4**: Router Organization (2 hours) - Organized plugins/ and monitoring/ modules
- ✅ **Phase 5**: Utility Organization (<1 hour) - Enhanced utils module with better imports
- ✅ **Phase 6**: Testing Infrastructure (2-3 hours) - 48 tests, pytest config
- ✅ **Phase 7**: Final Cleanup & Validation (2 hours) - Code validation
- ✅ **Phase 8**: Comprehensive Documentation (3 hours) - Architecture, structure, migration guides

**Upcoming Phases**:
- ✅ **All 8 phases complete!**



### Refactoring Benefits

The refactoring effort provides:
- **Better Code Organization**: Clear module structure with separation of concerns
- **Improved Discoverability**: Easy to find and navigate code
- **Type Safety**: Comprehensive type hints and pydantic validation
- **Centralized Configuration**: Single source of truth for all settings
- **Zero Breaking Changes**: Maintained backward compatibility throughout
- **Reduced Technical Debt**: Removed 11,650+ lines of code

### Development Documentation

For detailed refactoring status and developer guides:
- `REFACTORING_PROGRESS.md` - Detailed progress tracking
- `SESSION_SUMMARY.md` - Latest session work
- `PROJECT-STRUCTURE.md` - Codebase navigation guide
- `CONTRIBUTING.md` - Development guidelines

---
