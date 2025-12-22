# Unity - Quick Start Guide

**Current Status**: Week 2 Complete ✅  
**Last Updated**: December 22, 2024

---

## 🚀 Quick Commands

### Start Development Server
```bash
cd /home/matthew/projects/HI/unity/backend
source ../.venv/bin/activate
export PYTHONPATH=/home/matthew/projects/HI/unity/backend
uvicorn app.main:app --reload
```

### Run Migrations
```bash
cd /home/matthew/projects/HI/unity/backend
source ../.venv/bin/activate
export PYTHONPATH=/home/matthew/projects/HI/unity/backend
alembic upgrade head
```

### Run Tests
```bash
cd /home/matthew/projects/HI/unity/backend
source ../.venv/bin/activate
export PYTHONPATH=/home/matthew/projects/HI/unity/backend
pytest tests/ -v
```

---

## 📚 Key Files

- **Save Point**: `WEEK2_COMPLETE.md` - Detailed save point
- **Plan**: View with Warp plan tools - "Unity Phase 2: Complete Platform Enhancement"
- **Config**: `.env` (copy from `.env.example`)
- **API Docs**: http://localhost:8000/docs (when server running)

---

## 🔗 Important Endpoints

### Notifications
- `GET /api/notifications/services` - List 78+ available services
- `GET /api/notifications/channels` - List configured channels
- `POST /api/notifications/channels` - Create new channel
- `POST /api/notifications/send` - Send notification

### OAuth
- `GET /api/auth/oauth/providers` - List configured providers
- `GET /api/auth/oauth/github` - Login with GitHub
- `GET /api/auth/oauth/google` - Login with Google

---

## 🗄️ Database

**Location**: `backend/unity.db` (SQLite)  
**Migrations**: `backend/alembic/versions/`

**Key Tables**:
- `users` - User accounts
- `user_oauth_links` - OAuth provider links
- `notification_channels` - Notification configs
- `notification_logs` - Notification history

---

## 📋 Next Work Session

Open `WEEK2_COMPLETE.md` and go to "Next Steps (Week 3)"

**Week 3 Focus**: Alerting System
- Alert rules engine
- Alert management
- Notification integration

---

## 🆘 Troubleshooting

### Import errors
```bash
export PYTHONPATH=/home/matthew/projects/HI/unity/backend
```

### Missing dependencies
```bash
cd /home/matthew/projects/HI/unity
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Database issues
```bash
# Reset and rerun migrations
rm backend/unity.db
cd backend
export PYTHONPATH=/home/matthew/projects/HI/unity/backend
alembic upgrade head
```

---

**Resume**: See `WEEK2_COMPLETE.md` for full details
