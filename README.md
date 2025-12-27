# Unity - Homelab Intelligence Platform

**Version**: 1.0.0  
**Status**: ✅ Production Ready

Unity is a comprehensive homelab monitoring and automation platform built with FastAPI, React, and PostgreSQL.

---

## 🚀 Quick Start

### Docker Compose (Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your values

# 2. Start services
docker-compose up -d

# 3. Run migrations
docker-compose exec backend alembic upgrade head

# 4. Access
# - Frontend: http://localhost:80
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Manual Setup

See [docs/guides/START_HERE_PRODUCTION.md](docs/guides/START_HERE_PRODUCTION.md) for detailed setup instructions.

---

## ✨ Features

### Core Features

- ✅ **Real-Time Dashboard** - Live metrics with WebSocket updates
- ✅ **39 Builtin Plugins** - System, network, database, container monitoring
- ✅ **Alert System** - Threshold-based alerting with notifications
- ✅ **User Management** - RBAC (Admin, User, Viewer roles)
- ✅ **Authentication** - JWT + OAuth2 (GitHub, Google)

### Advanced Features

- ✅ **Plugin Marketplace** - Browse and install community plugins
- ✅ **Custom Dashboard Builder** - Create custom dashboards
- ✅ **AI-Powered Insights** - Anomaly detection and forecasting
- ✅ **Advanced Alerting** - Multi-condition rules and correlation
- ✅ **Performance Optimization** - Caching, code splitting, query optimization

---

## 📁 Project Structure

```
unity/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── docs/             # Documentation (organized)
├── stacks/           # Docker stack definitions
├── docker-compose.yml    # Production Docker stack
├── docker-compose.demo.yml  # Demo configuration
├── .env.example      # Environment template
└── .env.demo        # Demo environment
```

---

## 📚 Documentation

All documentation is organized in the `docs/` directory:

- **Production**: `docs/production/` - Deployment guides, assessments
- **Development**: `docs/development/` - Progress, enhancements
- **Guides**: `docs/guides/` - Quick starts, getting started
- **Technical**: `docs/` - Architecture, API, plugins

See [docs/README.md](docs/README.md) for the complete documentation index.

---

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db
JWT_SECRET_KEY=<generate: openssl rand -hex 32>
ENCRYPTION_KEY=<generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
DEBUG=false

# Optional
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
```

See `.env.example` for all available options.

---

## 🐳 Docker Stack

### Services

- **PostgreSQL** (port 5432) - Database
- **Redis** (port 6379) - Caching
- **Backend** (port 8000) - FastAPI API
- **Frontend** (port 80) - React UI

### Demo Files

- `docker-compose.demo.yml` - Example configuration with values
- `.env.demo` - Example environment file

Use these as reference, but use the fresh templates (`docker-compose.yml` and `.env.example`) for new deployments.

---

## 🔒 Security

- ✅ JWT authentication
- ✅ Password hashing (bcrypt)
- ✅ Input validation
- ✅ SQL injection protection
- ✅ CORS configuration
- ✅ Credential encryption

**Important**: Change default passwords and generate new secrets before production use!

See [SECURITY.md](SECURITY.md) for security practices.

---

## 📊 Performance

- Health endpoint: <50ms
- API responses: <200ms
- WebSocket latency: <10ms
- Throughput: 120+ req/s

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🎯 Quick Links

- **Getting Started**: [docs/guides/START_HERE_PRODUCTION.md](docs/guides/START_HERE_PRODUCTION.md)
- **Production Deployment**: [docs/production/PRODUCTION_DEPLOYMENT_COMPLETE.md](docs/production/PRODUCTION_DEPLOYMENT_COMPLETE.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Plugin Development**: [docs/PLUGIN_DEVELOPMENT_GUIDE.md](docs/PLUGIN_DEVELOPMENT_GUIDE.md)

---

**Unity - Your homelab intelligence platform** 🚀
