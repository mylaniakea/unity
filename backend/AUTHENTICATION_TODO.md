# Authentication Integration TODO

## Completed ✅
- Auth models, migrations, services
- Auth dependencies and middleware  
- 4 new routers: /auth, /api-keys, /users, /audit-logs

## Step 11: Protect Existing Endpoints (TODO)

The following routers need authentication added:

### High Priority (Public → Authenticated)
1. **system.py** - Dashboard stats (viewer level)
2. **profiles.py** - Server profiles (viewer for GET, editor for POST/PUT/DELETE)
3. **credentials.py** - Sensitive! (editor or admin level)
4. **settings.py** - System settings (admin level)

### Medium Priority
5. **containers.py** - Container management (editor level)
6. **infrastructure.py** - Infrastructure monitoring (editor level)
7. **reports.py** - Reports (viewer level)
8. **terminal.py** - Terminal access (editor level)

### Lower Priority
9. **ai.py** - AI features (viewer level)
10. **knowledge.py** - Knowledge base (viewer level)

### Plugin Routers
11. **plugins/v2_secure.py** - Already has some auth
12. **plugins/v2.py** - Plugin API v2 (viewer level)
13. **plugins/legacy.py** - Legacy plugin API (viewer level)
14. **plugins/keys.py** - Plugin keys (editor level)

## How to Add Auth

For each router, add:

```python
# At top of file
from app.core.dependencies import get_current_active_user, require_viewer, require_editor, require_admin
from app.models.users import User

# For viewer-level endpoints (GET)
@router.get("/something")
async def get_something(
    current_user: User = Depends(require_viewer()),
    db: Session = Depends(get_db)
):
    ...

# For editor-level endpoints (POST/PUT/PATCH)
@router.post("/something")
async def create_something(
    data: SomeModel,
    current_user: User = Depends(require_editor()),
    db: Session = Depends(get_db)
):
    ...

# For admin-only endpoints (DELETE, settings)
@router.delete("/something/{id}")
async def delete_something(
    id: str,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    ...
```

## Notes
- Keep /health and /docs public
- Plugin execution endpoints may need API key auth
- Consider making /auth/register admin-only in production
