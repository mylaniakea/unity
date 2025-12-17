# User Management & RBAC Specification

**Status**: Planned - Next Priority
**Updated**: December 12, 2025

---

## Overview

Extend the existing authentication system with comprehensive user management and role-based access control (RBAC) to support multi-user environments with different permission levels.

---

## Current State ✅

### Implemented (Phase 6)
- JWT-based authentication
- User model with bcrypt password hashing
- Login/logout functionality
- Protected routes (frontend + backend)
- User registration endpoint (`/auth/register`)
- Current user endpoint (`/auth/me`)
- Default admin user (username: `admin`, password: `admin`)

### Database Schema (Users Table)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

---

## Requirements - Phase 7: User Management & RBAC

### 1. User Management Page (Admin Only)

**Location**: New page at `/users` accessible only to admin role

**Features**:
- **User List View**
  - Table showing all users with columns:
    - Username
    - Email
    - Role (Admin/User/Viewer)
    - Status (Active/Inactive)
    - Created Date
    - Last Login (future)
    - Actions (Edit/Delete buttons)
  - Search/filter by username, email, or role
  - Sort by any column
  - Pagination if user count > 50

- **Add User Form**
  - Fields: username, email (optional), password, confirm password, role
  - Password strength indicator
  - Validation: username must be unique, password min 8 characters
  - Success notification after creation

- **Edit User**
  - Modal or side panel
  - Can change: email, role, active status
  - Cannot change: username (immutable)
  - Password reset button (admin can set new password for user)

- **Delete User**
  - Confirmation dialog with username displayed
  - Cannot delete yourself (current logged-in admin)
  - Soft delete option (set is_active=false) or hard delete

- **Bulk Operations** (future)
  - Select multiple users
  - Bulk deactivate/activate
  - Bulk role change

---

### 2. Change Password Functionality

#### A. Self-Service Password Change
**Location**: Settings page (new "Security" section)

**Features**:
- Form with three fields:
  - Current Password (required for verification)
  - New Password
  - Confirm New Password
- Password strength indicator
- Requirements displayed:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one number
  - At least one special character (optional)
- Success notification after change
- Auto-logout after successful change (optional)

**Backend Endpoint**:
```
POST /auth/change-password
Body: {
  "current_password": "string",
  "new_password": "string"
}
```

#### B. Admin Password Reset
**Location**: User Management page > Edit User > Reset Password button

**Features**:
- Admin can set a new password for any user
- No current password required (admin override)
- Generate random password option
- Option to force user to change password on next login (future)

**Backend Endpoint**:
```
POST /auth/admin/reset-password/{user_id}
Body: {
  "new_password": "string"
}
Requires: admin role
```

---

### 3. Role-Based Access Control (RBAC)

#### A. Database Changes

**Update User Model**:
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # NEW: admin, user, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Migration**:
```sql
ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user';
UPDATE users SET role = 'admin' WHERE is_superuser = TRUE;
-- Keep is_superuser for backwards compatibility, but role is source of truth
```

#### B. Role Definitions

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Admin** | Full access to everything | System administrators |
| **User** | Can view and modify data, but cannot manage users | Regular operators |
| **Viewer** | Read-only access, cannot create/edit/delete | Monitoring dashboards, guests |

#### C. Permission Matrix

| Feature | Admin | User | Viewer |
|---------|-------|------|--------|
| View Dashboard | ✅ | ✅ | ✅ |
| View Servers | ✅ | ✅ | ✅ |
| Add/Edit/Delete Servers | ✅ | ✅ | ❌ |
| View Alerts & Thresholds | ✅ | ✅ | ✅ |
| Create/Edit/Delete Alerts | ✅ | ✅ | ❌ |
| Acknowledge/Resolve Alerts | ✅ | ✅ | ❌ |
| View Reports | ✅ | ✅ | ✅ |
| Generate Reports | ✅ | ✅ | ❌ |
| View Knowledge Base | ✅ | ✅ | ✅ |
| Add/Edit/Delete Knowledge | ✅ | ✅ | ❌ |
| View Settings | ✅ | ✅ | ✅ (limited) |
| Modify Settings | ✅ | ✅ | ❌ |
| View Users | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ❌ | ❌ |
| Change Own Password | ✅ | ✅ | ✅ |
| Use Terminal | ✅ | ✅ | ❌ |
| Execute Commands | ✅ | ✅ | ❌ |

#### D. Backend Implementation

**Permission Decorators**:
```python
from functools import wraps
from fastapi import HTTPException, status

def require_role(*allowed_roles):
    """Decorator to check if user has required role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {allowed_roles}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

# Usage examples:
@router.post("/servers", response_model=ServerProfile)
@require_role("admin", "user")
def create_server(...):
    pass

@router.delete("/servers/{id}")
@require_role("admin", "user")
def delete_server(...):
    pass

@router.get("/users")
@require_role("admin")
def list_users(...):
    pass
```

**Convenience Functions**:
```python
async def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency to require admin role"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def get_current_user_or_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency to require user or admin role (not viewer)"""
    if current_user.role not in ["admin", "user"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user
```

#### E. Frontend Implementation

**Role Context**:
```tsx
// Create RoleContext to access user role throughout app
interface RoleContextType {
  role: 'admin' | 'user' | 'viewer';
  isAdmin: boolean;
  isUser: boolean;
  isViewer: boolean;
  canEdit: boolean; // true for admin/user, false for viewer
}

export const RoleProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    api.get('/auth/me').then(res => setUser(res.data));
  }, []);

  const value = {
    role: user?.role || 'viewer',
    isAdmin: user?.role === 'admin',
    isUser: user?.role === 'user',
    isViewer: user?.role === 'viewer',
    canEdit: ['admin', 'user'].includes(user?.role)
  };

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
};
```

**Conditional Rendering**:
```tsx
import { useRole } from '@/contexts/RoleContext';

function ServerList() {
  const { canEdit, isAdmin } = useRole();

  return (
    <>
      <ServerTable servers={servers} />
      {canEdit && (
        <Button onClick={handleAddServer}>Add Server</Button>
      )}
      {isAdmin && (
        <Button onClick={handleBulkDelete}>Bulk Delete</Button>
      )}
    </>
  );
}
```

**Route Protection**:
```tsx
// Extend ProtectedRoute to support role requirements
function RoleProtectedRoute({
  children,
  allowedRoles = ['admin', 'user', 'viewer']
}) {
  const { role } = useRole();

  if (!allowedRoles.includes(role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Usage in App.tsx
<Route
  path="/users"
  element={
    <RoleProtectedRoute allowedRoles={['admin']}>
      <UsersPage />
    </RoleProtectedRoute>
  }
/>
```

---

## Implementation Phases

### Phase 7A: Change Password (1-2 hours)
1. Add `/auth/change-password` endpoint
2. Add `/auth/admin/reset-password/{user_id}` endpoint
3. Add Security section to Settings page
4. Add password change form with validation
5. Test password change flow

### Phase 7B: Add Role Column (30 minutes)
1. Add `role` column to User model
2. Create migration script
3. Update default admin user to have `role='admin'`
4. Update `/auth/register` to accept role (admin only)
5. Update `/auth/me` to return role

### Phase 7C: User Management Page (3-4 hours)
1. Create `/users` route (admin only)
2. Create UsersPage component
3. Add user list table with search/filter
4. Add user creation form
5. Add user edit form
6. Add user deletion with confirmation
7. Test all CRUD operations

### Phase 7D: RBAC Backend (2-3 hours)
1. Create permission decorators
2. Apply role checks to all sensitive endpoints:
   - POST/PUT/DELETE on servers, alerts, thresholds, knowledge
   - User management endpoints
   - Settings modification endpoints
3. Update OpenAPI docs to show required roles
4. Test with different role users

### Phase 7E: RBAC Frontend (2-3 hours)
1. Create RoleContext
2. Update all pages to conditionally show/hide based on role
3. Hide create/edit/delete buttons for viewers
4. Add role indicators in UI (badge on username?)
5. Test all pages with viewer account

### Phase 7F: Testing & Polish (1-2 hours)
1. Create test users for each role
2. Test permission matrix end-to-end
3. Fix any UI/UX issues
4. Add role-based help text
5. Update documentation

---

## API Endpoints Summary

### New Endpoints

**User Management** (Admin only):
```
GET    /users               - List all users
POST   /users               - Create new user
GET    /users/{id}          - Get user details
PUT    /users/{id}          - Update user
DELETE /users/{id}          - Delete user
```

**Password Management**:
```
POST   /auth/change-password           - Change own password
POST   /auth/admin/reset-password/{id} - Admin reset user password
```

**Extended Existing**:
```
POST   /auth/register       - Add role field (admin-only if called by API)
GET    /auth/me             - Include role in response
```

---

## Security Considerations

1. **Password Requirements**
   - Minimum 8 characters
   - Enforce on both frontend and backend
   - Consider password strength meter

2. **Role Changes**
   - Log all role changes for audit
   - Cannot change own role (prevent privilege escalation)
   - Must be admin to change roles

3. **Session Management**
   - Consider invalidating sessions on role change
   - Consider invalidating sessions on password change

4. **Default Accounts**
   - Change default admin password on first login (future)
   - Display warning if using default credentials

5. **Rate Limiting** (future)
   - Limit login attempts
   - Limit password change attempts
   - Prevent brute force attacks

---

## UI/UX Notes

1. **Role Badges**
   - Show role badge next to username in sidebar
   - Color code: Admin (red), User (blue), Viewer (gray)

2. **Disabled UI Elements**
   - For viewers, show disabled buttons with tooltip: "Read-only access"
   - Don't hide features, just disable them (better UX)

3. **User Management**
   - Use modal for add/edit forms
   - Inline editing option for quick changes
   - Bulk actions with checkboxes

4. **Password Strength**
   - Visual strength meter
   - Real-time validation feedback
   - Suggest strong passwords

---

## Future Enhancements

### Advanced RBAC
- Custom roles with granular permissions
- Permission groups (e.g., "Server Manager", "Alert Manager")
- Per-resource permissions (e.g., can only manage servers in "Production" group)

### Audit Logging
- Track all user actions
- Show audit log in admin panel
- Export audit logs

### Advanced Features
- LDAP/Active Directory integration
- SSO (Single Sign-On) with OAuth2
- API keys for programmatic access
- Temporary access tokens
- User groups/teams

---

## Testing Checklist

- [ ] Admin can create users with any role
- [ ] Admin can edit any user
- [ ] Admin can delete any user except self
- [ ] Admin can reset any user's password
- [ ] User can change own password
- [ ] Viewer can change own password
- [ ] User cannot access user management page
- [ ] Viewer cannot access user management page
- [ ] Viewer cannot create/edit/delete any resources
- [ ] Viewer can view all pages
- [ ] User can create/edit/delete resources
- [ ] User cannot manage other users
- [ ] All API endpoints enforce correct permissions
- [ ] Frontend hides/disables UI based on role
- [ ] Password change requires current password (non-admin)
- [ ] Strong passwords are enforced
- [ ] Role changes are logged
- [ ] Cannot change own role

---

**Ready for implementation when prioritized!** 🚀
