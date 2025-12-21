# Unity - Homelab Intelligence Platform

> **IMPORTANT**: This repository is PUBLIC. Never commit secrets, API keys, passwords, or personal information.  
> See [PUBLIC-REPO-SECURITY.md](./PUBLIC-REPO-SECURITY.md) for guidelines.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg) ![Status](https://img.shields.io/badge/status-active_development-yellow.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

**Unity** is a unified homelab intelligence platform that brings together monitoring, automation, and management into a single, extensible hub with a plugin architecture.

## 🎯 Project Status

**Current Version**: 1.0.0 (Runs 1-5 Complete)  
**Progress**: 83% to MVP (5/6 runs complete)

### Completed ✅
- ✅ **Run 1**: Infrastructure & Architecture
- ✅ **Run 2**: Database Schema & Migrations  
- ✅ **Run 3**: Data Collection Pipeline
- ✅ **Run 4**: API Layer & Endpoints
- ✅ **Run 5**: Testing & Validation

### In Progress 🔵
- 🔵 **Run 6**: Documentation & Deployment (Current)

### Features

**Available Now**:
- ⚡ REST API with 10 endpoints
- 🔌 WebSocket real-time streaming
- 📊 Plugin scheduler (automatic data collection)
- 🗄️ PostgreSQL database with time-series support
- 🧪 Comprehensive test suite (31 tests, 100% coverage)
- 🚀 Docker Compose deployment
- 📈 Performance: <50ms API response, 120+ req/s throughput

**Coming Soon**:
- 🎨 React frontend (planned)
- 🔐 JWT authentication
- 🔔 Alert system
- 📱 Push notifications

## 🚀 Quick Start

### Prerequisites
- Docker 20.10+ & Docker Compose 2.0+
- Python 3.11+ (for local development)

### Deploy with Docker

```bash
# Clone repository
git clone <repository-url>
cd unity

# Create environment file
cp .env.example .env

# Start services
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

Access:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Local Development

```bash
cd backend

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up database
export DATABASE_URL="sqlite:///./data/homelab.db"
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

See [DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md) for detailed instructions.

## 📊 Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Unity Platform                      │
│                                                      │
│  ┌──────────────┐     ┌──────────────┐            │
│  │   Frontend   │────▶│   Backend    │            │
│  │   (React)    │     │   (FastAPI)  │            │
│  │   Planned    │     │   Port: 8000 │            │
│  └──────────────┘     └──────┬───────┘            │
│                               │                     │
│                      ┌────────▼────────┐           │
│                      │  PluginScheduler │           │
│                      │  (APScheduler)   │           │
│                      └────────┬─────────┘           │
│                               │                     │
│                      ┌────────▼────────┐           │
│                      │   PostgreSQL    │           │
│                      │   Port: 5432    │           │
│                      └─────────────────┘           │
└─────────────────────────────────────────────────────┘
```

### Key Components

**Backend** (FastAPI):
- REST API (10 endpoints)
- WebSocket streaming
- Plugin scheduler
- Metrics collection

**Database** (PostgreSQL 16):
- Plugin registrations
- Time-series metrics
- Execution history
- Health status

**Plugins** (39 available):
- System monitoring
- Docker containers
- Network stats
- Storage metrics
- Custom extensible

## 🔌 Plugin System

Unity uses a plugin architecture for extensible monitoring:

```python
from app.plugins.base import PluginBase

class MyPlugin(PluginBase):
    async def collect_data(self) -> dict:
        return {"metric": "value"}
    
    async def health_check(self) -> bool:
        return True
```

Built-in plugins include:
- `system_info` - CPU, memory, disk usage
- `docker_monitor` - Container status and stats
- `network_monitor` - Network interfaces and traffic
- Plus 36 more!

See [Plugin Showcase](https://mylaniakea.github.io/unity/) for full list.

## 📡 API Reference

### REST Endpoints

```bash
GET  /health                              # Health check
GET  /api/plugins                         # List all plugins
GET  /api/plugins/{id}                    # Plugin details
POST /api/plugins/{id}/enable             # Enable/disable
GET  /api/plugins/{id}/status             # Health status
GET  /api/plugins/{id}/metrics            # Latest metrics
GET  /api/plugins/{id}/metrics/history    # Historical data
GET  /api/plugins/{id}/executions         # Execution log
GET  /api/plugins/categories/list         # Categories
GET  /api/plugins/stats/summary           # Statistics
```

### WebSocket Streaming

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'metrics_update') {
        console.log('New metrics:', data.metrics);
    }
};
```

See [API Documentation](docs/RUN4_API_LAYER.md) for complete reference.

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_plugin_api.py -v
pytest tests/test_websocket.py -v
pytest tests/test_performance.py -v -s

# Run with coverage
pytest --cov=app --cov-report=html
```

**Test Results** (Run 5):
- 31 tests, 100% API coverage
- Performance: All targets exceeded by 3-4x
- 0% error rate under sustained load

See [Testing Guide](docs/RUN5_TESTING.md) for details.

## 📚 Documentation

### Deployment
- [Deployment Architecture](docs/DEPLOYMENT_ARCHITECTURE.md) - System overview
- [Development Setup](docs/DEVELOPMENT_SETUP.md) - Local development
- [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) - Production guide
- [Performance Tuning](docs/PERFORMANCE_TUNING.md) - Optimization

### Development
- [Run 3: Data Collection](docs/RUN3_DATA_COLLECTION.md) - Scheduler implementation
- [Run 4: API Layer](docs/RUN4_API_LAYER.md) - API endpoints
- [Run 5: Testing](docs/RUN5_TESTING.md) - Test suite
- [Architecture](ARCHITECTURE.md) - Technical architecture

### Guides
- [Contributing](CONTRIBUTING.md) - How to contribute
- [Security](SECURITY.md) - Security practices

## 🗂️ Project Structure

```
unity/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py      # Application entry
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   ├── plugins/     # Plugin implementations
│   │   └── core/        # Core utilities
│   ├── tests/           # Test suite
│   └── requirements.txt
├── frontend/            # React frontend (planned)
├── docs/                # Documentation
├── docker-compose.yml   # Production config
└── .env.example         # Configuration template
```

## ⚙️ Configuration

Environment variables (`.env`):

```bash
# Database
DATABASE_URL=postgresql+psycopg2://user:pass@db:5432/homelab_db

# Security
ENCRYPTION_KEY=<generate-with-fernet>
JWT_SECRET_KEY=<random-secret>

# Application
DEBUG=false
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000

# Optional
REDIS_URL=redis://localhost:6379/0
```

See [.env.example](.env.example) for all options.

## 🚀 Deployment

### Docker Compose (Recommended)

```bash
# Production
docker-compose up -d

# Development (hot-reload)
docker-compose -f docker-compose.dev.yml up
```

### Manual Deployment

See [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md) for:
- Security checklist
- SSL/TLS configuration
- Backup strategies
- Monitoring setup

## 📈 Performance

**Benchmarks** (from Run 5 testing):
- Health endpoint: 25ms average (target: <100ms) ✅
- Plugins list: 35ms average (target: <150ms) ✅
- Metrics query: 45ms average (target: <200ms) ✅
- Throughput: 120 req/s (target: >10 req/s) ✅
- WebSocket latency: <10ms ✅

**Capacity**:
- ~100 plugins supported
- ~10 monitored servers
- ~1000 metrics/minute

See [Performance Tuning](docs/PERFORMANCE_TUNING.md) for optimization.

## 🔒 Security

- ✅ Input validation (Pydantic)
- ✅ Credential encryption
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ CORS configuration
- ⏳ JWT authentication (planned)
- ⏳ Rate limiting (planned)

**Never commit secrets!** Use environment variables.

See [SECURITY.md](SECURITY.md) for security practices.

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Development workflow**:
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🎯 Roadmap

### Phase 1: Core Platform (Current - Run 6)
- ✅ Backend API
- ✅ Plugin system
- ✅ Data collection
- ✅ Testing
- 🔵 Documentation (in progress)

### Phase 2: User Interface
- Frontend development
- Dashboard UI
- Real-time visualizations
- Plugin management UI

### Phase 3: Advanced Features
- Authentication & authorization
- Alert system
- Push notifications
- Multi-user support

### Phase 4: Enterprise Features
- RBAC
- Audit logging
- SSO integration
- High availability

See [ROADMAP.md](ROADMAP.md) for detailed timeline.

## 📞 Support

- 📖 **Documentation**: `docs/` directory
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions

---

**Unity** - Unified homelab intelligence for the modern homelab enthusiast.

*Co-Authored-By: Warp <agent@warp.dev>*
