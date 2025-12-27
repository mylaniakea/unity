# Homelab Intelligence - Start Here

## Project Overview
Homelab Intelligence is a comprehensive monitoring and management platform for homelab servers. It provides real-time system monitoring, AI-powered insights, alerting, knowledge management, and multi-user role-based access control.

## Current Status: Production Ready ✅

### Recently Completed Features
- **User Management & RBAC System** (Just Completed!)
  - Three-tier role system: Admin, User, Viewer
  - Unified Users page accessible to all users
  - Self-service password management for all users
  - Admin-only user management capabilities
  - Protected routes and conditional UI based on roles

### Core Features
- 📊 **Real-time Dashboard** - System metrics and health monitoring
- 🖥️ **Server Management** - SSH connection profiles with encrypted credentials
- 🤖 **AI Intelligence** - Multi-provider AI integration (Anthropic, OpenAI, Ollama, Gemini)
- 📈 **Hardware Monitoring** - CPU, memory, disk, network metrics
- 🔔 **Smart Alerts** - Configurable thresholds with multiple notification channels
- 📄 **Reports** - Automated system reports with scheduling
- 🧠 **Knowledge Base** - Searchable documentation and notes
- 🔌 **Plugin System** - Extensible architecture for custom integrations
- 👥 **User Management** - Role-based access control with self-service features
- ⚙️ **Settings** - System configuration and preferences

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Ports 3000 (frontend) and 8000 (backend) available

### Running the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the application at: `http://localhost:3000`

### Default Admin Credentials
- **Username:** `admin`
- **Password:** `admin123`

⚠️ **Important:** Change the admin password immediately after first login via Users → Edit → Change Password

## Architecture

### Stack
- **Frontend:** React 18 + TypeScript + Vite + TailwindCSS
- **Backend:** FastAPI (Python) + SQLAlchemy
- **Database:** PostgreSQL
- **Containerization:** Docker Compose

### Key Directories
```
├── backend/
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── models.py       # Database models
│   │   └── schemas.py      # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/          # Route components
│   │   ├── components/     # Reusable components
│   │   ├── contexts/       # React contexts (Auth, Theme, etc.)
│   │   └── api/            # API client
│   └── package.json
└── docker-compose.yml
```

## User Roles & Permissions

### Admin
- Full system access
- User management (create, edit, delete users)
- Can reset passwords for any user
- Configure system settings
- Manage all resources

### User
- Can view and edit most resources
- Can change their own password
- Cannot manage other users
- Cannot modify system-critical settings

### Viewer
- Read-only access to dashboards and reports
- Can view system metrics and knowledge base
- Can change their own password
- Cannot edit or delete resources

## Recent Implementation: Unified Users Page

The Users page now serves dual purposes:

**For Regular Users/Viewers:**
- Access via sidebar → Users
- See only their own account
- Page title: "My Account"
- Can change password (requires current password)
- Clean, focused interface

**For Admins:**
- See all users in searchable list
- Page title: "User Management"
- Full CRUD operations
- Can reset passwords without current password
- Manage roles and account status

## Environment Configuration

Key environment variables (see `.env.example`):

```bash
# Database
POSTGRES_USER=homelab
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=homelab_intelligence

# Backend
DATABASE_URL=postgresql://homelab:password@db:5432/homelab_intelligence
SECRET_KEY=your_secret_key_here

# AI Providers (Optional)
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
```

## Development Workflow

### Making Changes

1. **Frontend changes:**
   ```bash
   docker-compose build frontend
   docker-compose restart frontend
   ```

2. **Backend changes:**
   ```bash
   docker-compose build backend
   docker-compose restart backend
   ```

3. **Database migrations:**
   ```bash
   docker-compose exec backend python migrate_add_users.py
   ```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f backend
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/change-password` - Change own password
- `POST /auth/admin/reset-password/{user_id}` - Admin reset password
- `GET /auth/me` - Get current user info

### Users (Admin only)
- `GET /users/` - List all users
- `POST /users/` - Create user
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

### System Monitoring
- `GET /system/info` - System information
- `GET /profiles/` - SSH profiles
- `GET /alerts/` - Active alerts
- `GET /reports/` - Generated reports

## Known Issues & Notes

- Browser caching: After frontend updates, hard refresh (Ctrl+Shift+R / Cmd+Shift+R) may be needed
- SSH keys are encrypted at rest in the database
- Alert notifications require channel configuration (email, Slack, Discord, etc.)
- AI features require API keys for respective providers

## Next Steps / Potential Enhancements

- [ ] Add email verification for new users
- [ ] Implement password reset via email
- [ ] Add audit logging for admin actions
- [ ] Enhance dashboard with customizable widgets
- [ ] Add mobile app or responsive improvements
- [ ] Implement API rate limiting
- [ ] Add backup/restore functionality
- [ ] Expand plugin marketplace
- [ ] Add multi-language support

## Troubleshooting

### Cannot Login
- Verify backend is running: `docker-compose ps`
- Check backend logs: `docker-compose logs backend`
- Ensure database migrations ran: `docker-compose exec backend python migrate_add_users.py`

### Frontend Not Updating
- Rebuild container: `docker-compose build frontend`
- Hard refresh browser: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
- Clear browser cache completely

### Database Connection Issues
- Check PostgreSQL is running: `docker-compose ps db`
- Verify DATABASE_URL in backend environment
- Check database logs: `docker-compose logs db`

## Support & Documentation

- See `README.md` for installation details
- See `IMPLEMENTATION_PLAN.md` for architecture decisions
- See `TODO.md` for planned features

---

**Last Updated:** 2025-12-12
**Version:** 1.0.0 with RBAC
**Status:** Production Ready
