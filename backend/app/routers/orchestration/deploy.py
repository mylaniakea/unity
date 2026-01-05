"""
Orchestration API Endpoints

Semantic AI-powered deployment orchestration API.
Allows users to deploy applications using natural language commands.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.services.auth import get_current_active_user as get_current_user
from app.models import User, DeploymentIntent
from app.services.orchestration.deployment_orchestrator import DeploymentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/orchestration",
    tags=["orchestration"]
)


# ==================
# Request/Response Schemas
# ==================

class DeployRequest(BaseModel):
    """Request to deploy an application via natural language command."""
    command: str = Field(..., description="Natural language deployment command", example="install authentik")
    options: Optional[dict] = Field(default={}, description="Optional configuration overrides")

    class Config:
        json_schema_extra = {
            "example": {
                "command": "install authentik with TLS",
                "options": {
                    "namespace": "auth",
                    "domain": "auth.example.com"
                }
            }
        }


class DeployResponse(BaseModel):
    """Response from deployment request."""
    success: bool
    intent_id: int
    application: Optional[str] = None
    platform: Optional[str] = None
    message: str
    deployment_result: Optional[dict] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class IntentStatusResponse(BaseModel):
    """Deployment intent status."""
    id: int
    command: str
    status: str
    platform: Optional[str]
    namespace: Optional[str]
    application: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_ms: Optional[int]
    error: Optional[str]
    logs: List[dict] = []
    deployed_resources: List[dict] = []


class BlueprintResponse(BaseModel):
    """Application blueprint metadata."""
    name: str
    description: Optional[str]
    category: Optional[str]
    platform: str
    type: str
    is_official: bool
    source: str


# ==================
# Deployment Endpoints
# ==================

@router.post("/deploy", response_model=DeployResponse)
async def deploy_application(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deploy application using natural language command.

    Examples:
    - "install authentik"
    - "deploy postgresql with 3 replicas"
    - "setup grafana with TLS and ingress"

    The system will:
    1. Parse the command using AI
    2. Load the application blueprint
    3. Resolve dependencies
    4. Generate platform-specific manifests
    5. Deploy to the target platform
    6. Track status and provide logs
    """
    try:
        logger.info(f"User {current_user.username} requested deployment: {request.command}")

        orchestrator = DeploymentOrchestrator(db)

        # Execute deployment in background to avoid timeout
        result = await orchestrator.execute_intent(
            command_text=request.command,
            user_id=current_user.id,
            options=request.options
        )

        return DeployResponse(**result)

    except Exception as e:
        logger.error(f"Deployment request failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@router.get("/intents", response_model=List[IntentStatusResponse])
async def list_deployment_intents(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List deployment intents.

    Filter by status: pending, parsing, generating, deploying, completed, failed, cancelled
    """
    try:
        query = db.query(DeploymentIntent).filter_by(user_id=current_user.id)

        if status_filter:
            query = query.filter_by(status=status_filter)

        intents = query.order_by(DeploymentIntent.created_at.desc()).offset(offset).limit(limit).all()

        return [
            IntentStatusResponse(
                id=intent.id,
                command=intent.command_text,
                status=intent.status,
                platform=intent.target_platform,
                namespace=intent.target_namespace,
                application=intent.parsed_intent.get("application") if intent.parsed_intent else None,
                created_at=intent.created_at.isoformat() if intent.created_at else None,
                started_at=intent.started_at.isoformat() if intent.started_at else None,
                completed_at=intent.completed_at.isoformat() if intent.completed_at else None,
                duration_ms=intent.duration_ms,
                error=intent.error_message,
                logs=intent.execution_log or [],
                deployed_resources=intent.deployed_resources or []
            )
            for intent in intents
        ]

    except Exception as e:
        logger.error(f"Failed to list intents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list intents: {str(e)}"
        )


@router.get("/intents/{intent_id}", response_model=IntentStatusResponse)
async def get_deployment_intent(
    intent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed status of a deployment intent.

    Includes:
    - Current status
    - Execution logs
    - Deployed resources
    - Error messages (if failed)
    """
    try:
        intent = db.query(DeploymentIntent).filter_by(
            id=intent_id,
            user_id=current_user.id
        ).first()

        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent {intent_id} not found"
            )

        return IntentStatusResponse(
            id=intent.id,
            command=intent.command_text,
            status=intent.status,
            platform=intent.target_platform,
            namespace=intent.target_namespace,
            application=intent.parsed_intent.get("application") if intent.parsed_intent else None,
            created_at=intent.created_at.isoformat() if intent.created_at else None,
            started_at=intent.started_at.isoformat() if intent.started_at else None,
            completed_at=intent.completed_at.isoformat() if intent.completed_at else None,
            duration_ms=intent.duration_ms,
            error=intent.error_message,
            logs=intent.execution_log or [],
            deployed_resources=intent.deployed_resources or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get intent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get intent: {str(e)}"
        )


@router.post("/intents/{intent_id}/retry")
async def retry_deployment_intent(
    intent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry a failed deployment intent.

    Only intents with status 'failed' or 'cancelled' can be retried.
    """
    try:
        intent = db.query(DeploymentIntent).filter_by(
            id=intent_id,
            user_id=current_user.id
        ).first()

        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent {intent_id} not found"
            )

        orchestrator = DeploymentOrchestrator(db)
        result = await orchestrator.retry_intent(intent_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry intent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry intent: {str(e)}"
        )


@router.delete("/intents/{intent_id}")
async def cancel_deployment_intent(
    intent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running or pending deployment intent.

    Completed intents cannot be cancelled.
    """
    try:
        intent = db.query(DeploymentIntent).filter_by(
            id=intent_id,
            user_id=current_user.id
        ).first()

        if not intent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Intent {intent_id} not found"
            )

        orchestrator = DeploymentOrchestrator(db)
        result = await orchestrator.cancel_intent(intent_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel intent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel intent: {str(e)}"
        )


# ==================
# Blueprint Endpoints
# ==================

@router.get("/blueprints", response_model=List[BlueprintResponse])
async def list_blueprints(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List available application blueprints.

    Blueprints define how applications are deployed, including:
    - Required dependencies
    - Default configuration
    - Platform support
    - Resource templates

    Filter by category: auth, database, cache, monitoring, web, proxy, etc.
    """
    try:
        from app.services.orchestration.blueprint_loader import BlueprintLoader

        loader = BlueprintLoader(db)
        blueprints = loader.list_blueprints(category=category)

        return [BlueprintResponse(**bp) for bp in blueprints]

    except Exception as e:
        logger.error(f"Failed to list blueprints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list blueprints: {str(e)}"
        )


@router.get("/blueprints/{name}")
async def get_blueprint(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific blueprint.

    Includes:
    - Template structure
    - Variables and defaults
    - Dependencies
    - Ports and volumes
    - Environment variables
    """
    try:
        from app.services.orchestration.blueprint_loader import BlueprintLoader

        loader = BlueprintLoader(db)
        blueprint = loader.get_blueprint(name)

        if not blueprint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blueprint '{name}' not found"
            )

        return blueprint

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get blueprint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blueprint: {str(e)}"
        )


@router.get("/blueprints/{name}/dependencies")
async def get_blueprint_dependencies(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all dependencies for a blueprint (recursive).

    Returns list of blueprint names that must be deployed first.
    """
    try:
        from app.services.orchestration.blueprint_loader import BlueprintLoader

        loader = BlueprintLoader(db)
        dependencies = loader.get_blueprint_dependencies(name)

        return {
            "application": name,
            "dependencies": dependencies,
            "count": len(dependencies)
        }

    except Exception as e:
        logger.error(f"Failed to get dependencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dependencies: {str(e)}"
        )
