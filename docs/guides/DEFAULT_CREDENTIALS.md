# Default Credentials

## 🔐 Default Login

**Username**: `admin`  
**Password**: `admin123`

⚠️ **IMPORTANT**: Change this password immediately after first login!

---

## 🚀 First Time Setup

### If Admin User Doesn't Exist

If you can't login with the default credentials, you may need to create the admin user first:

#### Option 1: Via API (Recommended)

```bash
# Register admin user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@unity.local",
    "password": "admin123",
    "full_name": "System Administrator"
  }'
```

Then update the role to admin:

```bash
# Login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# Update role to admin (if you have another admin user)
curl -X PUT http://localhost:8000/api/v1/users/{user_id}/role \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

#### Option 2: Via Database (Direct)

```bash
# Enter backend container
docker compose exec backend bash

# Run Python to create admin
python3 << EOF
from app.core.database import SessionLocal
from app.models.users import User
from app.services.auth.user_service import UserService

db = SessionLocal()
service = UserService(db)

# Create admin user
user = service.create_user(
    username="admin",
    email="admin@unity.local",
    password="admin123",
    full_name="System Administrator",
    role="admin"
)
print(f"Admin user created: {user.username}")
EOF
```

---

## 🔒 Security Best Practices

1. **Change Password Immediately**
   - Login with default credentials
   - Go to Users → Edit → Change Password
   - Set a strong password

2. **Disable Registration** (Production)
   - After creating admin, disable `/auth/register`
   - Or make it admin-only

3. **Use Strong Passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, symbols

---

## 📝 Quick Reference

```bash
# Default login
Username: admin
Password: admin123

# Change after first login!
```

---

**Remember**: Always change the default password before production use! 🔒

