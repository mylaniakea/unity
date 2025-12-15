# Unity - Homelab Intelligence Hub

**Unity** is the unified homelab intelligence platform that brings together monitoring, automation, and management into a single, extensible hub with a plugin architecture.

## What is Unity?

Unity evolved from the homelab-intelligence project and serves as the central hub for:
- **System Monitoring** - Track CPU, memory, disk, network, and more
- **Container Management** - Monitor and update Docker containers (via uptainer plugin)
- **Storage Intelligence** - Database and storage monitoring (via bd-store plugin)
- **Credential Management** - SSH keys and certificate management (integrated from kc-booth)
- **AI-Powered Insights** - Intelligent analysis and recommendations
- **Extensible Plugin System** - Add custom monitoring and automation capabilities

## Architecture

Unity uses a plugin-based architecture where:
- **Hub Core** - FastAPI backend + React frontend with auth, database, alerts, terminal access
- **Built-in Plugins** - System monitoring, network stats, storage metrics
- **External Plugins** - Standalone services that integrate via the Plugin SDK
- **Credential Store** - Centralized SSH key and certificate management

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd unity
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Install dependencies**
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend
   cd ../frontend
   npm install
   ```

5. **Run migrations**
   ```bash
   cd backend
   python -m alembic upgrade head
   ```

6. **Start development servers**
   ```bash
   # Backend (in backend/)
   uvicorn app.main:app --reload
   
   # Frontend (in frontend/)
   npm run dev
   ```

7. **Access Unity**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
unity/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── models.py     # Database models
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   └── plugins/      # Plugin system (NEW)
│   └── requirements.txt
├── frontend/             # React frontend
│   ├── src/
│   │   ├── pages/        # Page components
│   │   ├── components/   # Reusable components
│   │   └── services/     # API clients
│   └── package.json
├── docker-compose.yml    # Service orchestration
└── HUB-IMPLEMENTATION-PLAN.md  # Development roadmap
```

## Current Status

🚧 **In Active Development** - Implementing plugin architecture (Phase 1-2)

- ✅ Core monitoring and auth system
- 🚧 Plugin architecture foundation
- 🚧 KC-Booth credential management integration
- 📋 Plugin SDK development
- 📋 External plugin support (bd-store, uptainer)

See [HUB-IMPLEMENTATION-PLAN.md](./HUB-IMPLEMENTATION-PLAN.md) for detailed roadmap.

## Features

### Current Features
- **Authentication & RBAC** - JWT-based auth with role-based access control
- **System Monitoring** - CPU, memory, disk, network metrics
- **Terminal Access** - Web-based SSH terminal
- **Alert System** - Configurable thresholds and notifications
- **AI Integration** - Intelligent insights and recommendations
- **Multi-Profile Support** - Monitor multiple systems

### Planned Features (Plugin System)
- **Plugin Marketplace** - Discover and install community plugins
- **External Plugin Support** - Run plugins as standalone services
- **Real-time Event Streams** - Redis-based plugin communication
- **Health Dashboard** - Monitor plugin status and performance
- **Configuration Management** - Web UI for plugin settings

## Development

### Adding a Plugin

See the Plugin SDK documentation (coming soon) for creating custom plugins.

Built-in plugins follow this structure:
```python
from app.plugins.base import PluginBase

class MyPlugin(PluginBase):
    def get_metadata(self):
        return {
            "id": "my-plugin",
            "name": "My Plugin",
            "version": "1.0.0",
            "category": "monitoring"
        }
    
    async def collect_data(self):
        # Collect and return data
        return {"metric": "value"}
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

[License TBD]

## Related Projects

- **bd-store** - Storage and database monitoring plugin
- **uptainer** - Container update automation with AI
- **kc-booth** - SSH key and certificate management (integrated into Unity core)

## Support

For issues, questions, or contributions, please open an issue on GitHub.
