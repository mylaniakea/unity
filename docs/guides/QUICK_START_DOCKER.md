# Quick Start - Docker Compose

## 🚀 Starting Unity

### Step 1: Configure Environment (First Time Only)

```bash
# Copy the template
cp .env.example .env

# Edit with your values (optional for testing)
# For quick testing, you can use defaults
nano .env
```

### Step 2: Start Services

**For Testing (Recommended):**
```bash
docker-compose up -d
```

**For Development (Hot-Reload):**
```bash
docker-compose -f docker-compose.dev.yml up
```

### Step 3: Run Migrations

```bash
# If using docker-compose.yml
docker-compose exec backend alembic upgrade head

# If using docker-compose.dev.yml
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

### Step 4: Verify

```bash
# Health check
curl http://localhost:8000/health

# Or visit in browser:
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:80
```

---

## 📋 Common Commands

### Start Services
```bash
# Production/Testing
docker-compose up -d

# Development
docker-compose -f docker-compose.dev.yml up
```

### Stop Services
```bash
# Production/Testing
docker-compose down

# Development
docker-compose -f docker-compose.dev.yml down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Development
docker-compose -f docker-compose.dev.yml logs -f
```

### Restart Services
```bash
docker-compose restart

# Or specific service
docker-compose restart backend
```

### Check Status
```bash
docker-compose ps
```

---

## 🎯 Quick Start (Copy & Paste)

```bash
# 1. Configure (first time)
cp .env.example .env

# 2. Start
docker-compose up -d

# 3. Migrations
docker-compose exec backend alembic upgrade head

# 4. Test
curl http://localhost:8000/health
```

---

## ⚠️ Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :8000

# Or change ports in docker-compose.yml
```

### Services Won't Start
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose up -d --build
```

### Database Issues
```bash
# Reset database (WARNING: deletes data)
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

---

**That's it! Unity should now be running.** 🎉

