"""
Secure Plugin Management API (v2)

Enhanced with comprehensive security:
- JWT authentication for user endpoints
- API key authentication for external plugins
- Input validation and sanitization
- Rate limiting
- Audit logging
- Authorization checks
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Plugin, PluginMetric, PluginExecution, PluginAPIKey, User
from app.services.plugin_manager import PluginManager
from app.services.plugin_security import PluginSecurityService, rate_limiter
from app.services.auth import get_current_active_user
from app.schemas_plugins import (
    PluginListResponse,
    PluginInfo,
    PluginDetailInfo,
    PluginRegisterRequest,
    PluginConfigUpdate,
    PluginMetricData,
    PluginMetricsResponse,
    PluginHealthResponse,
    PluginExecutionResponse,
    PluginActionResponse
)

router = APIRouter(
    prefix="/plugins/v2",
    tags=["plugins-v2-secure"],
    responses={404: {"description": "Not found"}},
)

security = HTTPBearer()


def get_plugin_manager(db: Session = Depends(get_db)) -> PluginManager:
    """Dependency to get PluginManager instance."""
    return PluginManager(db)


async def verify_plugin_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> tuple[str, PluginAPIKey]:
    """
    Verify API key for external plugins.
    
    Returns:
        Tuple of (plugin_id, api_key_record)
    """
    api_key = credentials.credentials
    key_hash = PluginSecurityService.hash_api_key(api_key)
    
    # Find API key
    stmt = select(PluginAPIKey).where(
        and_(
            PluginAPIKey.key_hash == key_hash,
            PluginAPIKey.is_active == True
        )
    )
    result = db.execute(stmt)
    key_record = result.scalar_one_or_none()
    
    if not key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Check expiration
    if key_record.expires_at and key_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=401,
            detail="API key expired"
        )
    
    # Update usage
    key_record.last_used = datetime.utcnow()
    key_record.uses_count += 1
    db.commit()
    
    return key_record.plugin_id, key_record


# ==================
# USER ENDPOINTS (JWT Auth Required)
# ==================

@router.get("", response_model=PluginListResponse)
async def list_plugins(
    category: Optional[str] = None,
    enabled: Optional[bool] = None,
    external: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager)
):
    """
    List all registered plugins.
    
    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    # Check rate limit
    rate_limiter.check_rate_limit(str(current_user.id), "plugin_list")
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, "all", "list", 
        {"filters": {"category": category, "enabled": enabled, "external": external}}
    )
    
    plugins = manager.list_plugins()
    
    # Apply filters
    if category:
        plugins = [p for p in plugins if p.get("category") == category]
    if enabled is not None:
        plugins = [p for p in plugins if p.get("enabled") == enabled]
    if external is not None:
        plugins = [p for p in plugins if p.get("external") == external]
    
    return PluginListResponse(
        plugins=[PluginInfo(**p) for p in plugins],
        total=len(plugins)
    )


@router.post("/register", response_model=PluginActionResponse)
async def register_external_plugin(
    request: PluginRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager)
):
    """
    Register an external plugin with the hub.
    
    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Check authorization
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can register external plugins"
        )
    
    # Check rate limit
    rate_limiter.check_rate_limit(str(current_user.id), "plugin_register")
    
    # Validate input
    PluginSecurityService.validate_plugin_metadata(request.dict())
    
    success = await manager.register_external_plugin(request.dict())
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, request.id, "register", 
        {"external": True}, success
    )
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Plugin {request.id} registered successfully",
            plugin_id=request.id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to register plugin {request.id}"
        )


@router.get("/{plugin_id}", response_model=PluginDetailInfo)
async def get_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific plugin.
    
    **Authentication:** JWT token required
    **Authorization:** All authenticated users
    """
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Check permission
    PluginSecurityService.check_user_plugin_permission(
        current_user, plugin_id, "view", db
    )
    
    plugin_info = manager.get_plugin_info(plugin_id)
    
    if not plugin_info:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    return PluginDetailInfo(**plugin_info)


@router.post("/{plugin_id}/enable", response_model=PluginActionResponse)
async def enable_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager),
    db: Session = Depends(get_db)
):
    """
    Enable a plugin.
    
    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Check permission
    PluginSecurityService.check_user_plugin_permission(
        current_user, plugin_id, "enable", db
    )
    
    # Check rate limit
    rate_limiter.check_rate_limit(str(current_user.id), "plugin_control")
    
    success = await manager.enable_plugin(plugin_id)
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, plugin_id, "enable", success=success
    )
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Plugin {plugin_id} enabled",
            plugin_id=plugin_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to enable plugin {plugin_id}"
        )


@router.post("/{plugin_id}/disable", response_model=PluginActionResponse)
async def disable_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager),
    db: Session = Depends(get_db)
):
    """
    Disable a plugin.
    
    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Check permission
    PluginSecurityService.check_user_plugin_permission(
        current_user, plugin_id, "disable", db
    )
    
    # Check rate limit
    rate_limiter.check_rate_limit(str(current_user.id), "plugin_control")
    
    success = await manager.disable_plugin(plugin_id)
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, plugin_id, "disable", success=success
    )
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Plugin {plugin_id} disabled",
            plugin_id=plugin_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to disable plugin {plugin_id}"
        )


@router.post("/{plugin_id}/execute", response_model=PluginExecutionResponse)
async def execute_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager),
    db: Session = Depends(get_db)
):
    """
    Execute a plugin manually (on-demand).
    
    **Authentication:** JWT token required
    **Authorization:** Admin or operator
    """
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Check permission
    PluginSecurityService.check_user_plugin_permission(
        current_user, plugin_id, "execute", db
    )
    
    # Check rate limit
    rate_limiter.check_rate_limit(str(current_user.id), "plugin_execution")
    
    result = await manager.execute_plugin(plugin_id)
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, plugin_id, "execute", 
        success=result.get("success", False)
    )
    
    return PluginExecutionResponse(
        success=result.get("success", False),
        plugin_id=plugin_id,
        timestamp=result.get("timestamp", datetime.utcnow().isoformat()),
        data=result.get("data"),
        error=result.get("error")
    )


@router.put("/{plugin_id}/config", response_model=PluginActionResponse)
async def update_plugin_config(
    plugin_id: str,
    request: PluginConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    manager: PluginManager = Depends(get_plugin_manager),
    db: Session = Depends(get_db)
):
    """
    Update plugin configuration.
    
    **Authentication:** JWT token required
    **Authorization:** Admin only
    """
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Check permission (config changes are admin-only)
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can update plugin configuration"
        )
    
    # Validate config
    PluginSecurityService.validate_plugin_config(request.config)
    
    # Check rate limit
    rate_limiter.check_rate_limit(str(current_user.id), "config_update")
    
    success = await manager.update_plugin_config(plugin_id, request.config)
    
    # Log action
    PluginSecurityService.log_plugin_action(
        current_user, plugin_id, "config_update", 
        {"config_keys": list(request.config.keys())}, success
    )
    
    if success:
        return PluginActionResponse(
            success=True,
            message=f"Configuration updated for plugin {plugin_id}",
            plugin_id=plugin_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update configuration for plugin {plugin_id}"
        )


# ==================
# EXTERNAL PLUGIN ENDPOINTS (API Key Auth Required)
# ==================

@router.post("/{plugin_id}/metrics/report", response_model=PluginActionResponse)
async def report_plugin_metrics(
    plugin_id: str,
    metric_data: PluginMetricData,
    auth_info: tuple = Depends(verify_plugin_api_key),
    db: Session = Depends(get_db)
):
    """
    Report plugin metrics (for external plugins).
    
    **Authentication:** API key required
    **Authorization:** API key must belong to the plugin
    """
    authenticated_plugin_id, api_key_record = auth_info
    
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Ensure API key matches plugin
    if authenticated_plugin_id != plugin_id:
        raise HTTPException(
            status_code=403,
            detail="API key does not belong to this plugin"
        )
    
    # Check permission
    if "report_metrics" not in api_key_record.permissions:
        raise HTTPException(
            status_code=403,
            detail="API key does not have report_metrics permission"
        )
    
    # Validate metrics data
    PluginSecurityService.validate_metrics_data(metric_data.data)
    
    # Check rate limit
    rate_limiter.check_rate_limit(plugin_id, "metric_reporting")
    
    # Verify plugin exists
    stmt = select(Plugin).where(Plugin.id == plugin_id)
    result = db.execute(stmt)
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    # Store metrics
    metric = PluginMetric(
        plugin_id=plugin_id,
        timestamp=metric_data.timestamp or datetime.utcnow(),
        data=metric_data.data
    )
    db.add(metric)
    db.commit()
    
    # Log action
    PluginSecurityService.log_plugin_action(
        None, plugin_id, "report_metrics", 
        {"metrics_keys": list(metric_data.data.keys())}
    )
    
    return PluginActionResponse(
        success=True,
        message="Metrics recorded",
        plugin_id=plugin_id
    )


@router.post("/{plugin_id}/health/report", response_model=PluginActionResponse)
async def report_plugin_health(
    plugin_id: str,
    health_data: dict,
    auth_info: tuple = Depends(verify_plugin_api_key),
    db: Session = Depends(get_db)
):
    """
    Update plugin health status (for external plugins).
    
    **Authentication:** API key required
    **Authorization:** API key must belong to the plugin
    """
    authenticated_plugin_id, api_key_record = auth_info
    
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Ensure API key matches plugin
    if authenticated_plugin_id != plugin_id:
        raise HTTPException(
            status_code=403,
            detail="API key does not belong to this plugin"
        )
    
    # Check permission
    if "update_health" not in api_key_record.permissions:
        raise HTTPException(
            status_code=403,
            detail="API key does not have update_health permission"
        )
    
    # Check rate limit
    rate_limiter.check_rate_limit(plugin_id, "health_check")
    
    stmt = select(Plugin).where(Plugin.id == plugin_id)
    result = db.execute(stmt)
    plugin = result.scalar_one_or_none()
    
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    plugin.last_health_check = datetime.utcnow()
    plugin.health_status = "healthy" if health_data.get("healthy") else "unhealthy"
    plugin.health_message = health_data.get("message")
    db.commit()
    
    # Log action
    PluginSecurityService.log_plugin_action(
        None, plugin_id, "update_health", 
        {"healthy": health_data.get("healthy")}
    )
    
    return PluginActionResponse(
        success=True,
        message="Health status updated",
        plugin_id=plugin_id
    )


@router.get("/{plugin_id}/config/fetch")
async def fetch_plugin_config(
    plugin_id: str,
    auth_info: tuple = Depends(verify_plugin_api_key),
    manager: PluginManager = Depends(get_plugin_manager)
):
    """
    Get plugin configuration (for external plugins).
    
    **Authentication:** API key required
    **Authorization:** API key must belong to the plugin
    """
    authenticated_plugin_id, api_key_record = auth_info
    
    # Validate plugin ID
    PluginSecurityService.validate_plugin_id(plugin_id)
    
    # Ensure API key matches plugin
    if authenticated_plugin_id != plugin_id:
        raise HTTPException(
            status_code=403,
            detail="API key does not belong to this plugin"
        )
    
    # Check permission
    if "get_config" not in api_key_record.permissions:
        raise HTTPException(
            status_code=403,
            detail="API key does not have get_config permission"
        )
    
    plugin_info = manager.get_plugin_info(plugin_id)
    
    if not plugin_info:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin_id} not found"
        )
    
    return {
        "plugin_id": plugin_id,
        "config": plugin_info.get("config", {})
    }
