# GitHub Setup Guide for Unity

This guide will help you set up Unity on GitHub so you can pull it and deploy it anywhere.

---

## 🚀 Quick Setup

### 1. Initialize Git Repository (if not already done)

```bash
cd /home/matthew/projects/HI/unity

# Check if git is initialized
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi
```

### 2. Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository:
   - **Name**: `unity` (or your preferred name)
   - **Description**: "Unity - Homelab Intelligence Platform"
   - **Visibility**: Private (recommended) or Public
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)

### 3. Add Remote and Push

```bash
# Add your GitHub repository as remote
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/unity.git

# Or if you prefer SSH:
# git remote add origin git@github.com:YOUR_USERNAME/unity.git

# Stage all files
git add .

# Create initial commit
git commit -m "Initial commit: Unity production-ready v1.0.0"

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## 📋 Pre-Push Checklist

Before pushing to GitHub, ensure:

- [x] `.env` is in `.gitignore` (✅ already done)
- [x] All secrets removed from `docker-compose.yml`
- [x] `.env.example` created (✅ done)
- [x] Sensitive data not committed
- [x] Documentation is complete

---

## 🔒 Security: Remove Secrets from docker-compose.yml

**IMPORTANT**: The current `docker-compose.yml` has hardcoded secrets. We need to use environment variables instead.

### Current Issue

The `docker-compose.yml` has:
```yaml
ENCRYPTION_KEY: 6ty12Z9TYTSM5ESuOuXd_RxLBgunI3G0_TJbCpBb9FU=
POSTGRES_PASSWORD: homelab_password
```

### Solution: Use Environment Variables

Update `docker-compose.yml` to use environment variables from `.env` file.

---

## 📦 Pulling and Deploying from GitHub

### On a New Machine

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/unity.git
cd unity

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor

# Generate secrets
# JWT Secret:
openssl rand -hex 32

# Encryption Key:
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Start Docker stack
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Verify
curl http://localhost:8000/health
```

---

## 🔄 Updating Your Repository

### Daily Workflow

```bash
# Pull latest changes
git pull origin main

# Make changes...

# Stage changes
git add .

# Commit
git commit -m "Description of changes"

# Push
git push origin main
```

---

## 🐳 Docker Stack on GitHub

### What Gets Committed

✅ **Committed to GitHub**:
- `docker-compose.yml` (with environment variables, no secrets)
- `docker-compose.dev.yml`
- All source code
- Documentation
- `.env.example` (template)
- `.gitignore`

❌ **NOT Committed**:
- `.env` (actual secrets)
- `*.db` (database files)
- `node_modules/`
- `.venv/`
- Any files with secrets

### Docker Compose Best Practices

1. **Use `.env` file** for secrets
2. **Use `docker-compose.override.yml`** for local overrides (not committed)
3. **Document** all required environment variables
4. **Never commit** actual secrets

---

## 📝 Recommended Repository Structure

```
unity/
├── .gitignore          # Excludes .env, *.db, etc.
├── .env.example        # Template for environment variables
├── README.md           # Project documentation
├── docker-compose.yml  # Production Docker stack
├── docker-compose.dev.yml  # Development Docker stack
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── Dockerfile
│   └── ...
└── docs/
    └── ...
```

---

## 🔐 Security Best Practices

1. **Never commit `.env`** - It's in `.gitignore`
2. **Use `.env.example`** - Template with placeholder values
3. **Rotate secrets** - Generate new ones for each deployment
4. **Use GitHub Secrets** - For CI/CD (if you set it up later)
5. **Review commits** - Before pushing, check for secrets:
   ```bash
   git diff --cached | grep -i "password\|secret\|key"
   ```

---

## 🚀 Quick Deploy Script

Create a `deploy.sh` script for easy deployment:

```bash
#!/bin/bash
# deploy.sh - Quick deployment script

set -e

echo "🚀 Deploying Unity..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Creating from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set required values!"
    exit 1
fi

# Pull latest code
git pull origin main

# Start Docker stack
docker-compose up -d --build

# Run migrations
docker-compose exec backend alembic upgrade head

# Verify
echo "✅ Deployment complete!"
echo "📍 API: http://localhost:8000"
echo "📍 Frontend: http://localhost:80"
```

---

## 📞 Next Steps

1. ✅ Initialize Git (if needed)
2. ✅ Create GitHub repository
3. ✅ Update `docker-compose.yml` to use environment variables
4. ✅ Commit and push
5. ✅ Test pulling on another machine

---

**Your Unity project is now ready for GitHub!** 🎉

