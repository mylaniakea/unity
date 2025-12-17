# ⚠️ PUBLIC REPOSITORY - SECURITY GUIDELINES

**CRITICAL:** This repository is PUBLIC on GitHub. All commits are visible to everyone.

---

## 🚫 NEVER Commit:

### Credentials & Secrets
- ❌ API keys (OpenAI, Anthropic, Google, etc.)
- ❌ Database passwords
- ❌ JWT secret keys
- ❌ SSH private keys
- ❌ OAuth client secrets
- ❌ Any passwords or tokens
- ❌ Plugin API keys (generated keys)

### Personal Information
- ❌ Email addresses (except generic contact)
- ❌ Phone numbers
- ❌ Home addresses
- ❌ Server IP addresses
- ❌ Internal network details
- ❌ Personal server hostnames

### Infrastructure Details
- ❌ Production database connection strings
- ❌ Internal API endpoints
- ❌ VPN configurations
- ❌ Firewall rules
- ❌ Certificate private keys

---

## ✅ Safe to Commit:

### Code & Configuration
- ✅ Source code (without hardcoded secrets)
- ✅ Example configurations (`.env.example` with placeholders)
- ✅ Documentation
- ✅ Tests
- ✅ Schema definitions
- ✅ Public API documentation

### Placeholders & Examples
- ✅ `JWT_SECRET_KEY=your-secret-key-here`
- ✅ `DATABASE_URL=postgresql://user:pass@localhost/db`
- ✅ `API_KEY=<your-api-key>`
- ✅ `example@example.com`

---

## 🔍 Pre-Commit Checklist

Before EVERY commit, check:

1. **Scan for secrets:**
   ```bash
   # Check what you're committing
   git diff --cached
   
   # Search for common secret patterns
   git diff --cached | grep -iE "(password|secret|key|token|api_key)"
   ```

2. **Review .env files:**
   - ✅ `.env.example` - SAFE (contains placeholders)
   - ❌ `.env` - NEVER commit (should be in .gitignore)

3. **Check for IPs/hostnames:**
   ```bash
   git diff --cached | grep -E "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
   ```

4. **Verify .gitignore:**
   - Ensure `.env`, `.env.local`, `*.key`, `*.pem` are ignored

---

## 🛡️ Current Safety Measures

### In Place:
✅ `.env.example` with placeholders only
✅ `.gitignore` excludes sensitive files
✅ Default JWT secret is clearly marked as "dev-only"
✅ No hardcoded credentials in code
✅ All secrets read from environment variables

### Code Examples:
```python
# ✅ GOOD - Reads from environment
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")

# ❌ BAD - Hardcoded secret
SECRET_KEY = "my-actual-secret-key-12345"
```

---

## 🚨 If You Accidentally Commit Secrets:

### Immediate Actions:

1. **DO NOT just delete and recommit** - The secret is still in git history!

2. **Rotate the compromised secret immediately:**
   - Change the password/key/token
   - Revoke the old one if possible

3. **Remove from git history:**
   ```bash
   # For recent commits
   git reset --soft HEAD~1
   git reset HEAD <file>
   
   # For older commits - use git filter-branch or BFG Repo-Cleaner
   # This rewrites history and requires force push
   ```

4. **Force push (if already pushed):**
   ```bash
   git push --force origin <branch>
   # ⚠️ Only do this on feature branches, not main!
   ```

5. **Consider the secret compromised** - Even after removal, assume it was seen

---

## 📋 Regular Audits

### Monthly:
- [ ] Review recent commits for any leaked secrets
- [ ] Update .gitignore if new sensitive file types appear
- [ ] Check GitHub security scanning alerts

### Before Release:
- [ ] Full repository scan for secrets
- [ ] Review all environment variable documentation
- [ ] Ensure production deployment guides don't expose internals

---

## 🔒 Tools to Help

### Git Hooks (Pre-commit):
```bash
#!/bin/sh
# .git/hooks/pre-commit

# Check for common secret patterns
if git diff --cached | grep -iE "(password|secret_key|api_key|token).*=.*['\"]"; then
    echo "⚠️  WARNING: Potential secret detected in commit!"
    echo "Review your changes before committing."
    exit 1
fi
```

### GitHub Secret Scanning:
- Enabled by default for public repos
- Alerts you if known secret patterns are detected

---

## 📝 Unity-Specific Considerations

### Safe to Share:
- Plugin architecture code
- API endpoint definitions
- Database schema (structure only)
- Example plugin implementations
- Security documentation (this file!)

### Never Share:
- Production database credentials
- Plugin API keys (after generation)
- JWT secrets used in production
- Server SSH keys
- OAuth credentials for AI providers

---

## ✅ Quick Reference Card

**Before Every Commit:**
```bash
# 1. Review your changes
git diff --cached

# 2. Search for secrets
git diff --cached | grep -iE "(password|secret|key|token|api)"

# 3. Check .env files
git status | grep "\.env$"  # Should be empty!

# 4. Commit if clean
git commit -m "Your message"
```

**Golden Rules:**
1. If in doubt, DON'T commit it
2. Use environment variables, not hardcoded values
3. Keep .env files OUT of git
4. Review diffs before pushing
5. Assume everything committed is public forever

---

**Last Updated:** December 15, 2025

**Remember:** Once on GitHub, assume it's been seen by everyone on the internet!
