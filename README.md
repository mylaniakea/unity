# Unity - Homelab Intelligence Hub

> ⚠️ **PUBLIC REPOSITORY WARNING**  
> This repository is PUBLIC. Never commit secrets, API keys, passwords, or personal information.  
> See [PUBLIC-REPO-SECURITY.md](./PUBLIC-REPO-SECURITY.md) for guidelines.

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
   git clone https://github.com/mylaniakea/unity.git
   cd unity
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings - NEVER commit this file!
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
│   │   └── plugins/      # Plugin system
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

🚧 **Phase 1 Complete** - Plugin architecture implemented and ready for testing

- ✅ Core monitoring and auth system
- ✅ Plugin architecture foundation
- ✅ Security layer (JWT, API keys, validation, rate limiting)
- ✅ Example plugin (system-info)
- 🚧 KC-Booth credential management integration (in progress)
- 📋 Plugin SDK development
- 📋 External plugin support (bd-store, uptainer)

See [HUB-IMPLEMENTATION-PLAN.md](./HUB-IMPLEMENTATION-PLAN.md) for detailed roadmap.

## Features

### Current Features
- **Authentication & RBAC** - JWT-based auth with role-based access control
- **System Monitoring** - CPU, memory, disk, network metrics
- **Plugin System** - Extensible architecture for built-in and external plugins
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
from app.plugins.base import PluginBase, PluginMetadata, PluginCategory

class MyPlugin(PluginBase):
    def get_metadata(self):
        return PluginMetadata(
            id="my-plugin",
            name="My Plugin",
            version="1.0.0",
            description="My plugin description",
            author="Your Name",
            category=PluginCategory.SYSTEM
        )
    
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

## Security

### Public Repository Considerations

This is a **PUBLIC repository**. Please review [PUBLIC-REPO-SECURITY.md](./PUBLIC-REPO-SECURITY.md) before committing:

- ✅ Never commit secrets, API keys, or passwords
- ✅ Use environment variables for all sensitive config
- ✅ Keep `.env` files out of git (use `.env.example` instead)
- ✅ Review diffs before committing

### Security Features

- JWT authentication with RBAC
- API key authentication for external plugins
- Input validation and sanitization
- Rate limiting
- Audit logging
- Encrypted credential storage

See [SECURITY.md](./SECURITY.md) for details.

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
