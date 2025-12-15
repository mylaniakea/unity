# Unity - Unified Homelab Infrastructure Monitoring

Welcome to the Unity platform documentation! Unity is a comprehensive homelab infrastructure monitoring and automation platform that brings together credential management, infrastructure monitoring, and container automation into a single, powerful solution.

## 🎯 Project Vision

Unity consolidates three specialized homelab management tools into one unified platform:
- **KC-Booth**: Secure credential and certificate management
- **BD-Store**: Infrastructure monitoring (servers, storage, databases)
- **Uptainer**: Automated container updates with AI recommendations

## 📚 Documentation Index

### Getting Started
- [[Quick Start Guide]]
- [[Installation]]
- [[Configuration]]
- [[Architecture Overview]]

### Features
- [[Credential Management]] (KC-Booth Integration)
- [[Infrastructure Monitoring]] (BD-Store Integration)
- [[Container Automation]] (Uptainer Integration)
- [[Plugin System]]
- [[Alert System]]
- [[AI Integration]]

### Integration
- [[Integration Overview]]
- [[Phase 1-2: KC-Booth Integration]]
- [[Phase 3: BD-Store Integration]]
- [[Phase 4: Uptainer Integration]]
- [[Integration Patterns]]

### API Documentation
- [[API Overview]]
- [[Authentication]]
- [[Credentials API]]
- [[Infrastructure API]]
- [[Containers API]]
- [[Core API]]

### Development
- [[Development Setup]]
- [[Database Schema]]
- [[Service Layer Architecture]]
- [[Adding New Features]]
- [[Testing Guide]]
- [[Contributing]]

### Operations
- [[Deployment Guide]]
- [[Docker Deployment]]
- [[Kubernetes Deployment]]
- [[Monitoring and Observability]]
- [[Backup and Recovery]]
- [[Troubleshooting]]

### Reference
- [[Configuration Reference]]
- [[Environment Variables]]
- [[Database Models]]
- [[Scheduler Tasks]]
- [[Security Best Practices]]

## 🚀 Current Status

### Completed Phases
- ✅ **Phase 1-2**: KC-Booth credential management integration (100% complete)
  - 5 models, 8 services, 37 endpoints
  - SSH key management, certificate lifecycle, ACME renewal
  - Automated distribution and metrics

### Planned Phases
- 🔄 **Phase 3**: BD-Store infrastructure monitoring (ready for implementation)
  - 4 models, 10 services, ~50 endpoints
  - Server monitoring, SMART data, ZFS/RAID, database discovery
  
- ⏸️ **Phase 4**: Uptainer container automation (ready for implementation)
  - 12+ models, 15+ services, ~60 endpoints
  - Multi-runtime support, AI recommendations, vulnerability scanning

## 📊 Platform Statistics

### Current (Phase 1-2 Complete)
- **Database Models**: 20 models
- **API Endpoints**: ~100 endpoints
- **Services**: 20+ service files
- **Codebase**: ~10,000 lines (backend)

### Post-Integration (All Phases)
- **Database Models**: ~35-40 models
- **API Endpoints**: ~200+ endpoints
- **Services**: ~35-40 service files
- **Codebase**: ~18,000-20,000 lines (backend)
- **Background Jobs**: ~15-20 scheduled tasks

## 🏗️ Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with Alembic migrations
- **Scheduler**: APScheduler
- **Frontend**: Next.js (React/TypeScript)
- **Containerization**: Docker & Docker Compose
- **Authentication**: JWT tokens
- **AI Integration**: Claude, OpenAI, Ollama, Gemini
- **Monitoring**: Prometheus metrics

## 🎨 Key Features

### Credential Management (KC-Booth)
- SSH key generation and distribution
- SSL/TLS certificate lifecycle management
- ACME protocol integration (Let's Encrypt, ZeroSSL)
- Step-CA support
- Automated certificate renewal
- Credential audit logging

### Infrastructure Monitoring (BD-Store)
- Server health monitoring via SSH
- SMART data collection and analysis
- ZFS and RAID pool monitoring
- Database instance discovery
- Automated metric collection
- Storage health alerts

### Container Automation (Uptainer)
- Multi-runtime support (Docker, Podman, Kubernetes)
- AI-powered update recommendations
- Vulnerability scanning with Trivy
- Automated rollback on failure
- Update policies and maintenance windows
- Container backup and restore

### Platform Core
- Plugin architecture for extensibility
- Unified alert and notification system
- Role-based access control
- RESTful API with OpenAPI documentation
- Real-time metrics and dashboards
- Comprehensive audit logging

## 🔗 Quick Links

- [GitHub Repository](https://github.com/mylaniakea/unity)
- [[API Documentation|API Overview]]
- [[Quick Start Guide]]
- [[Troubleshooting]]

## 💡 Philosophy

Unity follows these core principles:

1. **Consolidation**: One platform for all homelab management needs
2. **Automation**: Reduce manual intervention through intelligent automation
3. **Security**: Security-first design with encryption, audit logging, and RBAC
4. **Observability**: Comprehensive metrics and logging for all operations
5. **Extensibility**: Plugin architecture for custom functionality
6. **Reliability**: Automated rollback and health validation

## 📝 Recent Updates

- **Dec 15, 2024**: Phase 1-2 (KC-Booth) integration completed
- **Dec 15, 2024**: Phase 3-4 integration plans published
- **Dec 15, 2024**: Comprehensive documentation and wiki created

## 🤝 Contributing

We welcome contributions! Please see our [[Contributing]] guide for details on:
- Code style and conventions
- Development workflow
- Testing requirements
- Pull request process

## 📄 License

[Specify your license here]

## 🆘 Support

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/mylaniakea/unity/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/mylaniakea/unity/discussions)
- **Documentation**: Browse this wiki for detailed guides

---

**Last Updated**: December 15, 2024  
**Version**: 1.0.0 (Phase 1-2 Complete)
