"""
Orchestration Router - API endpoints for AI-driven deployment.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.orchestration import EnvironmentIntelligence, ManifestGenerator, BlueprintLoader
from app.services.ai.ai_provider import AIOrchestrator
from app.routers.settings import get_settings
from app.routers.orchestration.intent_parser import IntentParser
from app import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orchestrate", tags=["orchestration"])


class DeploymentRequest(BaseModel):
    """User's deployment request."""
    request: str
    namespace: str = "homelab"
    approve: bool = False
    dry_run: bool = False


class EnvironmentResponse(BaseModel):
    """Environment information."""
    cluster: Dict[str, Any]
    storage: Dict[str, Any]
    networking: Dict[str, Any]
    ready_to_deploy: bool


@router.get("/environment")
async def get_environment() -> Dict[str, Any]:
    """Get current cluster environment state."""
    try:
        env_intel = EnvironmentIntelligence()
        summary = env_intel.get_environment_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting environment: {e}")
        return {"error": str(e), "ready_to_deploy": False}


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """List available application templates."""
    try:
        loader = BlueprintLoader()
        templates = loader.list_blueprints()
        return {
            "templates": templates,
            "count": len(templates)
        }
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return {"error": str(e), "templates": []}


@router.post("/preview")
async def preview_deployment(
    req: DeploymentRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Preview what would be deployed (dry-run)."""
    try:
        # Get settings for AI
        settings = db.query(models.Settings).first()
        if not settings:
            return {"error": "System not configured"}
        
        # Initialize components
        ai_orchestrator = AIOrchestrator(settings.providers if hasattr(settings, 'providers') else {})
        intent_parser = IntentParser(ai_orchestrator)
        blueprint_loader = BlueprintLoader()
        manifest_gen = ManifestGenerator()
        env_intel = EnvironmentIntelligence()
        
        # Get cluster context
        cluster_info = env_intel.get_cluster_info()
        storage_info = env_intel.get_available_storage()
        
        context = {
            "cpu_available": str(cluster_info.get("total_cpu", 0)),
            "memory_available": f"{cluster_info.get('total_memory_gb', 0)}Gi",
            "storage_available": storage_info.get("recommended_size_gb", 20)
        }
        
        # Parse intent
        intent = await intent_parser.parse(req.request, context)
        
        if "error" in intent:
            return {"error": intent.get("error"), "manifests": []}
        
        # Get blueprints
        app = intent.get("app")
        if not app:
            return {"error": "Could not determine application to deploy", "manifests": []}
        
        blueprint = blueprint_loader.get_blueprint(app)
        if not blueprint:
            return {"error": f"No blueprint found for {app}", "manifests": []}
        
        # Generate manifests
        result = manifest_gen.generate_from_blueprint(
            blueprint,
            namespace=req.namespace
        )
        
        # Add dependencies
        if intent.get("dependencies"):
            for dep in intent["dependencies"]:
                dep_blueprint = blueprint_loader.get_blueprint(dep)
                if dep_blueprint:
                    dep_result = manifest_gen.generate_from_blueprint(
                        dep_blueprint,
                        namespace=req.namespace
                    )
                    result["manifests"].extend(dep_result["manifests"])
        
        # Validate
        validation = manifest_gen.validate_manifests()
        
        return {
            "intent": intent,
            "manifests": result["manifests"],
            "manifest_count": len(result["manifests"]),
            "yaml": manifest_gen.to_yaml(),
            "validation": validation,
            "ready_to_deploy": validation["valid"]
        }
    
    except Exception as e:
        logger.error(f"Error previewing deployment: {e}")
        return {"error": str(e), "manifests": []}


@router.post("/deploy")
async def deploy(
    req: DeploymentRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Deploy an application based on natural language request."""
    try:
        if not req.approve:
            return {"error": "Deployment must be approved (approve=true)"}
        
        # Get settings for AI
        settings = db.query(models.Settings).first()
        if not settings:
            return {"error": "System not configured"}
        
        # Initialize components
        ai_orchestrator = AIOrchestrator(settings.providers if hasattr(settings, 'providers') else {})
        intent_parser = IntentParser(ai_orchestrator)
        blueprint_loader = BlueprintLoader()
        manifest_gen = ManifestGenerator()
        env_intel = EnvironmentIntelligence()
        
        # Get cluster context
        cluster_info = env_intel.get_cluster_info()
        storage_info = env_intel.get_available_storage()
        
        context = {
            "cpu_available": str(cluster_info.get("total_cpu", 0)),
            "memory_available": f"{cluster_info.get('total_memory_gb', 0)}Gi",
            "storage_available": storage_info.get("recommended_size_gb", 20)
        }
        
        # Parse intent
        intent = await intent_parser.parse(req.request, context)
        
        if "error" in intent:
            raise Exception(intent.get("error"))
        
        # Get blueprints and generate manifests
        app = intent.get("app")
        blueprint = blueprint_loader.get_blueprint(app)
        
        if not blueprint:
            raise Exception(f"No blueprint found for {app}")
        
        result = manifest_gen.generate_from_blueprint(blueprint, namespace=req.namespace)
        
        # Add dependencies
        for dep in intent.get("dependencies", []):
            dep_blueprint = blueprint_loader.get_blueprint(dep)
            if dep_blueprint:
                dep_result = manifest_gen.generate_from_blueprint(
                    dep_blueprint,
                    namespace=req.namespace
                )
                result["manifests"].extend(dep_result["manifests"])
        
        # Validate
        validation = manifest_gen.validate_manifests()
        if not validation["valid"]:
            raise Exception(f"Invalid manifests: {validation['errors']}")
        
        # TODO: Apply manifests to Kubernetes
        # For now, just return what would be deployed
        
        return {
            "status": "success",
            "app": app,
            "dependencies": intent.get("dependencies", []),
            "namespace": req.namespace,
            "manifest_count": len(result["manifests"]),
            "manifests": result["manifests"],
            "yaml": manifest_gen.to_yaml(),
            "message": f"{app} and its dependencies are ready to deploy. Manifests validated and ready for kubectl apply."
        }
    
    except Exception as e:
        logger.error(f"Error deploying: {e}")
        return {"error": str(e), "status": "failed"}


@router.get("/status")
async def deployment_status() -> Dict[str, Any]:
    """Get status of deployments."""
    try:
        env_intel = EnvironmentIntelligence()
        services = env_intel.get_deployed_services()
        
        return {
            "status": "operational",
            "services": services
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"status": "error", "error": str(e)}
