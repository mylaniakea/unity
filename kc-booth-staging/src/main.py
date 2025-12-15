"""Main FastAPI application for kc-booth."""
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.orm import Session
from . import crud, models, schemas, step_ca, scheduler
from . import auth, auth_crud, auth_models, auth_schemas
from . import audit, audit_schemas
from .database import SessionLocal, engine
from .config import get_settings
from .rate_limit import limiter
from datetime import datetime, timedelta
from . import metrics
from .metrics import MetricsMiddleware
from .correlation_middleware import CorrelationIdMiddleware
import sys

# Validate configuration at startup
try:
    settings = get_settings()
    print("✓ Configuration validated successfully")
    print(f"  - Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    print(f"  - Encryption: Enabled")
    print(f"  - Step-CA: {settings.step_ca_url}")
    print(f"  - Authentication: {'Disabled (dev mode)' if settings.disable_auth else 'Enabled'}")
except Exception as e:
    print(f"✗ Configuration validation failed: {e}", file=sys.stderr)
    print("\nPlease ensure all required environment variables are set:", file=sys.stderr)
    print("  - DATABASE_URL", file=sys.stderr)
    print("  - ENCRYPTION_KEY (generate with: python3 generate_encryption_key.py)", file=sys.stderr)
    print("  - STEP_PROVISIONER_PASSWORD", file=sys.stderr)
    sys.exit(1)

# Create database tables
models.Base.metadata.create_all(bind=engine)
auth_models.Base.metadata.create_all(bind=engine)
audit.Base.metadata.create_all(bind=engine)

app = FastAPI(title="kc-booth", description="SSH key and certificate management for homelabs")

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
\n# Add correlation ID tracking
app.add_middleware(CorrelationIdMiddleware)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Store scheduler instance for graceful shutdown
app_scheduler = None

@app.on_event("startup")
def startup_event():
    global app_scheduler
    db = SessionLocal()
    try:
        app_scheduler = scheduler.start_scheduler()
        print("✓ Scheduler started")
    except Exception as e:
        print(f"✗ Failed to start scheduler: {e}", file=sys.stderr)

@app.on_event("shutdown")
def shutdown_event():
    """Gracefully shutdown scheduler on app termination."""
    global app_scheduler
    if app_scheduler:
        scheduler.stop_scheduler(app_scheduler)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health Check

\n# Metrics endpoint (no auth required for monitoring systems)
@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint."""
    return metrics.metrics_endpoint()

@app.get("/health")
def health_check():
    return {"status": "OK"}

# Authentication Endpoints

@app.post("/auth/users/", response_model=auth_schemas.User, tags=["Authentication"])
def create_user(
    user: auth_schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    """Create a new user (requires authentication)."""
    db_user = auth_crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    return auth_crud.create_user(db=db, user=user)

@app.post("/auth/login", response_model=auth_schemas.APIKeyWithKey, tags=["Authentication"])
@limiter.limit(settings.rate_limit_login)  # Configurable rate limit
def login(
    request: Request,
    login_request: auth_schemas.LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with username/password and receive an API key."""
    user = auth.authenticate_user(db, login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Create a new API key for this login
    api_key_create = auth_schemas.APIKeyCreate(name=f"Login - {datetime.utcnow().isoformat()}")
    db_api_key, plaintext_key = auth_crud.create_api_key(db, api_key_create, user.id)
    
    # Return the API key with metadata
    return auth_schemas.APIKeyWithKey(
        id=db_api_key.id,
        name=db_api_key.name,
        user_id=db_api_key.user_id,
        is_active=db_api_key.is_active,
        created_at=db_api_key.created_at,
        last_used_at=db_api_key.last_used_at,
        key=plaintext_key
    )

@app.post("/auth/api-keys/", response_model=auth_schemas.APIKeyWithKey, tags=["Authentication"])
def create_api_key(
    api_key: auth_schemas.APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    """Create a new API key for the authenticated user."""
    db_api_key, plaintext_key = auth_crud.create_api_key(db, api_key, current_user.id)
    
    return auth_schemas.APIKeyWithKey(
        id=db_api_key.id,
        name=db_api_key.name,
        user_id=db_api_key.user_id,
        is_active=db_api_key.is_active,
        created_at=db_api_key.created_at,
        last_used_at=db_api_key.last_used_at,
        key=plaintext_key
    )

@app.get("/auth/api-keys/", response_model=List[auth_schemas.APIKey], tags=["Authentication"])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    """List all API keys for the authenticated user."""
    return auth_crud.get_user_api_keys(db, current_user.id)

@app.delete("/auth/api-keys/{key_id}", response_model=auth_schemas.APIKey, tags=["Authentication"])
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    """Revoke (deactivate) an API key."""
    db_api_key = auth_crud.get_api_key(db, key_id)
    if not db_api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Ensure user can only revoke their own keys
    if db_api_key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this API key")
    
    return auth_crud.deactivate_api_key(db, key_id)

# SSH Keys

@app.post("/ssh-keys/", response_model=schemas.SSHKey, tags=["SSH Keys"])
def create_ssh_key(
    ssh_key: schemas.SSHKeyCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    db_ssh_key = crud.get_ssh_key_by_name(db, name=ssh_key.name)
    if db_ssh_key:
        raise HTTPException(status_code=400, detail="SSH key with this name already exists")
    return crud.create_ssh_key(db=db, ssh_key=ssh_key)

@app.get("/ssh-keys/", response_model=List[schemas.SSHKey], tags=["SSH Keys"])
def read_ssh_keys(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    ssh_keys = crud.get_ssh_keys(db, skip=skip, limit=limit)
    return ssh_keys

@app.get("/ssh-keys/{ssh_key_id}", response_model=schemas.SSHKey, tags=["SSH Keys"])
def read_ssh_key(
    ssh_key_id: int,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    db_ssh_key = crud.get_ssh_key(db, ssh_key_id=ssh_key_id)
    if db_ssh_key is None:
        raise HTTPException(status_code=404, detail="SSH key not found")
    return db_ssh_key

# Servers

@app.post("/servers/", response_model=schemas.Server, tags=["Servers"])
def create_server(
    server: schemas.ServerCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    db_server = crud.get_server_by_hostname(db, hostname=server.hostname)
    if db_server:
        raise HTTPException(status_code=400, detail="Server with this hostname already exists")
    return crud.create_server(db=db, server=server)

@app.get("/servers/", response_model=List[schemas.Server], tags=["Servers"])
def read_servers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    servers = crud.get_servers(db, skip=skip, limit=limit)
    return servers

@app.get("/servers/{server_id}", response_model=schemas.Server, tags=["Servers"])
def read_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    db_server = crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server

# CA

@app.get("/ca/fingerprint", tags=["Certificate Authority"])
def get_ca_fingerprint(current_user: auth_models.User = Depends(auth.get_current_user)):
    return {"fingerprint": step_ca.get_root_fingerprint()}

@app.post("/ca/issue-certificate", tags=["Certificate Authority"])
def issue_certificate_endpoint(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    db_server = crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    cert, key = step_ca.issue_certificate(db_server.hostname)
    
    expires_at = datetime.utcnow() + timedelta(days=90) # Certificates are valid for 90 days
    
    certificate = schemas.CertificateCreate(
        certificate=cert,
        key=key,
        expires_at=expires_at,
        server_id=server_id,
    )
    crud.create_certificate(db, certificate)
    
    return {"certificate": cert, "key": key}

@app.get("/certificates/", response_model=List[schemas.Certificate], tags=["Certificates"])
def read_certificates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    certificates = crud.get_certificates(db, skip=skip, limit=limit)
    return certificates

@app.get("/")
async def read_root():
    return {"message": "Welcome to kc-booth"}

# Audit Log Endpoints

@app.get("/audit/logs/", response_model=List[audit_schemas.AuditLog], tags=["Audit"])
def get_audit_logs_endpoint(
    user_id: int = None,
    resource_type: str = None,
    action: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    """Get audit logs with optional filters."""
    return audit.get_audit_logs(
        db,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        limit=limit,
        offset=offset
    )


@app.get("/audit/resource/{resource_type}/{resource_id}/", response_model=List[audit_schemas.AuditLog], tags=["Audit"])
def get_resource_audit_trail_endpoint(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(auth.get_current_user)
):
    """Get complete audit trail for a specific resource."""
    return audit.get_resource_audit_trail(db, resource_type, resource_id)
