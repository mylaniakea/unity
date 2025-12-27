# Unity - Quick Start for Production

**Get Unity running in production in 5 minutes!**

---

## 🚀 Step-by-Step Deployment

### 1. Run Database Migration (REQUIRED)

```bash
cd backend
alembic upgrade head
```

This creates all new tables:
- `marketplace_plugins`
- `plugin_reviews`
- `plugin_installations`
- `plugin_downloads`
- `dashboards`
- `dashboard_widgets`
- Adds `conditions_json` to `alert_rules`

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade 8f3d9e2a1c45 -> a1b2c3d4e5f6, Add marketplace and dashboard tables
```

### 2. Install New Dependencies

```bash
cd backend
pip install numpy>=1.24.0  # For AI insights
```

Or update requirements:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example if needed
cp .env.example .env

# Edit .env and set:
# - DATABASE_URL (your database connection)
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)
# - ENCRYPTION_KEY (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# - DEBUG=false
```

### 4. Start Services

```bash
# Docker Compose (Recommended)
docker-compose up -d

# Or manually:
# Backend: uvicorn app.main:app --host 0.0.0.0 --port 8000
# Frontend: cd frontend && npm run dev
```

### 5. Verify

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "scheduler": "running", "cache": "connected" or "disconnected"}
```

### 6. Access Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Default Login**: admin / admin123 (⚠️ CHANGE IMMEDIATELY!)

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Health endpoint responds
- [ ] Can login to frontend
- [ ] Dashboard loads
- [ ] Plugins list shows
- [ ] WebSocket connects (check browser console)
- [ ] Can create dashboard
- [ ] Can browse marketplace (will be empty initially)
- [ ] API docs accessible

---

## 🎉 You're Ready!

Unity is now running in production. All features are available:

- ✅ Real-time monitoring dashboard
- ✅ 39 builtin plugins
- ✅ Alert system
- ✅ User management
- ✅ Plugin marketplace (API ready)
- ✅ Custom dashboards (API ready)
- ✅ AI insights (API ready)

**Enjoy your homelab intelligence platform!** 🚀

