# Docker Compose Files Guide

Unity has three Docker Compose files for different use cases. Here's when to use each:

---

## 📋 File Comparison

| Feature | `docker-compose.yml` | `docker-compose.dev.yml` | `docker-compose.demo.yml` |
|---------|---------------------|-------------------------|--------------------------|
| **Purpose** | Production/Testing | Development | Demo/Reference |
| **Hot Reload** | ❌ No | ✅ Yes | ❌ No |
| **Redis** | ✅ Yes | ❌ No | ✅ Yes |
| **Environment** | Uses `.env` | Hardcoded | Uses `.env` |
| **Debug Mode** | `DEBUG=false` | `DEBUG=true` | `DEBUG=false` |
| **Log Level** | `info` | `debug` | `debug` |
| **Code Mounting** | No | Yes (live changes) | No |
| **Container Names** | `homelab-*` | `homelab-*-dev` | `homelab-*` |

---

## 🎯 Which One to Use?

### Use `docker-compose.yml` (Production/Testing) ✅ **RECOMMENDED FOR TESTING**

**When to use:**
- ✅ Testing production-like setup
- ✅ Final testing before deployment
- ✅ Want Redis caching
- ✅ Want to use `.env` file for configuration

**How to use:**
```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your values

# 2. Start
docker-compose up -d

# 3. Check logs
docker-compose logs -f backend
```

**Features:**
- Uses environment variables from `.env`
- Includes Redis for caching
- Production-like configuration
- Proper logging levels

---

### Use `docker-compose.dev.yml` (Development)

**When to use:**
- ✅ Active development
- ✅ Need hot-reloading (code changes without rebuild)
- ✅ Want debug logging
- ✅ Quick iteration

**How to use:**
```bash
# Start with dev compose
docker-compose -f docker-compose.dev.yml up -d

# Or with logs
docker-compose -f docker-compose.dev.yml up
```

**Features:**
- Hot-reloading (code changes auto-reload)
- Debug mode enabled
- Mounts code for live editing
- Separate dev volumes (won't conflict with production)

**Note:** Uses hardcoded values, not `.env` file.

---

### Use `docker-compose.demo.yml` (Reference Only)

**When to use:**
- ✅ Reference for example values
- ✅ See how configuration should look
- ❌ **NOT for actual deployment**

**Note:** This is the same as `docker-compose.yml` but with example values filled in. Use it as a reference, but use `docker-compose.yml` with your own `.env` for actual testing.

---

## 🚀 Recommended Testing Workflow

### For Testing (Production-Like)

```bash
# 1. Use the production template
cp .env.example .env

# 2. Edit .env with your test values
nano .env

# 3. Start with production compose
docker-compose up -d

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Test
curl http://localhost:8000/health
```

### For Development

```bash
# Use dev compose for hot-reloading
docker-compose -f docker-compose.dev.yml up
```

---

## 🔍 Key Differences

### `docker-compose.yml` (Recommended for Testing)

```yaml
# Uses .env file
env_file:
  - .env

# Includes Redis
redis:
  image: redis:7-alpine

# Production-like settings
DEBUG: ${DEBUG:-false}
LOG_LEVEL: ${LOG_LEVEL:-info}
```

### `docker-compose.dev.yml` (Development)

```yaml
# Hot-reloading
command: uvicorn app.main:app --reload

# Mounts code for live editing
volumes:
  - ./backend:/app

# Debug mode
DEBUG=true
```

---

## ✅ Recommendation

**For testing, use `docker-compose.yml`** because:

1. ✅ Uses `.env` file (proper configuration)
2. ✅ Includes Redis (full feature set)
3. ✅ Production-like setup (realistic testing)
4. ✅ Proper logging levels
5. ✅ Clean container names

**For active development, use `docker-compose.dev.yml`** for hot-reloading.

---

## 📝 Quick Reference

```bash
# Testing (production-like)
docker-compose up -d

# Development (hot-reload)
docker-compose -f docker-compose.dev.yml up

# Stop
docker-compose down
# or
docker-compose -f docker-compose.dev.yml down
```

---

**Use `docker-compose.yml` for testing!** ✅

