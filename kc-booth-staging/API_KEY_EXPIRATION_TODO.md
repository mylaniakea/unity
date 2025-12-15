# API Key Expiration - Implementation Guide

## Status
Not implemented - requires database migration.

## What's Needed

### 1. Database Migration
Add `expires_at` column to `api_keys` table:
```sql
ALTER TABLE api_keys ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
```

### 2. Model Update (src/auth_models.py)
```python
class APIKey(Base):
    __tablename__ = "api_keys"
    # ... existing fields ...
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL = never expires
```

### 3. Schema Update (src/auth_schemas.py)
```python
class APIKeyCreate(APIKeyBase):
    expires_in_days: Optional[int] = Field(default=90, description="Days until expiration")

class APIKey(APIKeyBase):
    # ... existing fields ...
    expires_at: Optional[datetime] = None
```

### 4. CRUD Update (src/auth_crud.py)
```python
def create_api_key(...):
    expires_at = None
    if api_key_create.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=api_key_create.expires_in_days)
    
    db_api_key = auth_models.APIKey(
        # ... existing fields ...
        expires_at=expires_at
    )
```

### 5. Auth Check Update (src/auth.py)
```python
async def get_current_user(...):
    # ... existing code ...
    
    # Check expiration
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
```

### 6. Configuration (src/config.py)
```python
api_key_expiration_days: int = Field(
    default=90,
    description="Default API key expiration in days (0 = never expires)"
)
```

## Migration Steps

1. Install Alembic: `pip install alembic`
2. Initialize: `alembic init alembic`
3. Configure `alembic.ini` with DATABASE_URL
4. Create migration: `alembic revision --autogenerate -m "Add expires_at to api_keys"`
5. Review generated migration
6. Apply: `alembic upgrade head`

## Testing

```bash
# Create key with expiration
curl -X POST http://localhost:8001/auth/api-keys/ \
  -H "X-API-Key: existing-key" \
  -d '{"name": "Test Key", "expires_in_days": 30}'

# Use after expiration should return 401
```

## Notes
- Existing keys will have NULL expires_at (never expire)
- Add cleanup job to delete expired keys periodically
- Consider grace period before deletion
