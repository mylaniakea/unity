"""
FastAPI Dependencies

Common dependencies used across the application, including tenant context.
"""
from fastapi import Request, Depends
from typing import Optional


def get_tenant_id(request: Request) -> str:
    """
    Extract tenant_id from request context.
    
    The tenant_id is injected by TenantContextMiddleware and stored in request.state.
    This dependency makes it easy to access tenant_id in route handlers.
    
    Usage in routes:
        @router.get("/clusters")
        def get_clusters(
            db: Session = Depends(get_db),
            tenant_id: str = Depends(get_tenant_id)
        ):
            return db.query(Cluster).filter(Cluster.tenant_id == tenant_id).all()
    
    Returns:
        str: The tenant_id for the current request (defaults to 'default')
    """
    return getattr(request.state, "tenant_id", "default")


def get_optional_tenant_id(request: Request) -> Optional[str]:
    """
    Extract tenant_id from request context, returning None if not present.
    
    Useful for routes that should work with or without tenant context.
    
    Returns:
        Optional[str]: The tenant_id or None
    """
    return getattr(request.state, "tenant_id", None)
