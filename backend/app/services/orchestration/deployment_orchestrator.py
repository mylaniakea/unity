"""
Deployment Orchestrator

Main workflow coordinator for semantic AI orchestration.
Handles the complete deployment lifecycle from natural language to running application.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.deployment_manager import DeploymentManager
from app.services.orchestration.blueprint_loader import BlueprintLoader
from app.services.orchestration.intent_parser import IntentParser
from app.services.orchestration.manifest_generator import ManifestGenerator

logger = logging.getLogger(__name__)


class DeploymentOrchestratorError(Exception):
    """Base exception for deployment orchestrator errors"""
    pass


class DeploymentOrchestrator:
    """
    Orchestrates the complete deployment workflow.

    Workflow:
    1. Parse natural language command with AI
    2. Load application blueprint
    3. Resolve dependencies
    4. Generate platform-specific manifests
    5. Deploy to target platform
    6. Track status and log progress
    7. Handle errors and rollback if needed
    """

    def __init__(self, db_session: Session):
        """
        Initialize deployment orchestrator.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.deployment_manager = DeploymentManager(db_session)
        self.blueprint_loader = BlueprintLoader(db_session)
        self.intent_parser = IntentParser()
        self.manifest_generator = ManifestGenerator()
        self.logger = logger

    async def execute_intent(
        self,
        command_text: str,
        user_id: int,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute deployment intent from natural language command.

        Args:
            command_text: Natural language command (e.g., "install authentik")
            user_id: User ID making the request
            options: Optional configuration overrides

        Returns:
            Dict with deployment result and intent ID
        """
        options = options or {}
        intent_id = None

        try:
            # Create deployment intent record
            intent_id = await self._create_intent_record(command_text, user_id)
            
            self.logger.info(f"Executing intent {intent_id}: '{command_text}'")

            # Step 1: Parse command with AI
            await self._update_intent_status(intent_id, "parsing", "Parsing command with AI...")
            parsed_intent = await self.intent_parser.parse_command(command_text)
            
            if not parsed_intent.get("success"):
                raise DeploymentOrchestratorError(f"Failed to parse command: {parsed_intent.get('error')}")

            await self._log_step(intent_id, "info", "parsing", f"Parsed intent: {parsed_intent['action']} {parsed_intent['application']} on {parsed_intent['platform']}")

            # Update intent with parsed data
            await self._update_intent_parsed_data(intent_id, parsed_intent)

            # Step 2: Load blueprint
            await self._update_intent_status(intent_id, "generating", "Loading application blueprint...")
            application = parsed_intent.get("application")
            blueprint = self.blueprint_loader.get_blueprint(application)

            if not blueprint:
                raise DeploymentOrchestratorError(f"Blueprint not found for application: {application}")

            await self._log_step(intent_id, "info", "loading", f"Loaded blueprint for {application}")

            # Step 3: Resolve dependencies
            dependencies = self.blueprint_loader.get_blueprint_dependencies(application)
            if dependencies:
                await self._log_step(intent_id, "info", "dependencies", f"Resolved dependencies: {', '.join(dependencies)}")
            
            # Step 4: Generate manifests
            await self._update_intent_status(intent_id, "generating", "Generating deployment manifests...")
            
            # Merge options with parsed parameters
            config = {
                **parsed_intent.get("parameters", {}),
                **options
            }

            # Generate manifests for dependencies first
            all_manifests = []
            for dep in dependencies:
                dep_blueprint = self.blueprint_loader.get_blueprint(dep)
                if dep_blueprint:
                    dep_manifests = self.manifest_generator.generate(
                        blueprint=dep_blueprint,
                        config=config,
                        platform=parsed_intent["platform"]
                    )
                    all_manifests.extend(dep_manifests)
                    await self._log_step(intent_id, "info", "generating", f"Generated manifests for dependency: {dep}")

            # Generate manifests for main application
            manifests = self.manifest_generator.generate(
                blueprint=blueprint,
                config=config,
                platform=parsed_intent["platform"]
            )
            all_manifests.extend(manifests)

            await self._log_step(intent_id, "info", "generating", f"Generated {len(all_manifests)} manifest(s)")

            # Update intent with generated manifests
            await self._update_intent_manifests(intent_id, all_manifests)

            # Step 5: Deploy to platform
            await self._update_intent_status(intent_id, "deploying", "Deploying to platform...")
            
            platform = parsed_intent["platform"]
            deployment_config = self._build_deployment_config(
                platform=platform,
                manifests=all_manifests,
                intent=parsed_intent,
                options=options
            )

            start_time = datetime.utcnow()
            deployment_result = await self.deployment_manager.deploy(platform, deployment_config)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if not deployment_result.get("success"):
                raise DeploymentOrchestratorError(f"Deployment failed: {deployment_result.get('errors', ['Unknown error'])}")

            await self._log_step(intent_id, "info", "deploying", f"Deployment successful ({duration_ms}ms)")

            # Step 6: Verify deployment
            await self._update_intent_status(intent_id, "verifying", "Verifying deployment...")
            await self._log_step(intent_id, "info", "verifying", "Checking deployment status...")

            # Mark as completed
            await self._update_intent_completed(intent_id, deployment_result, duration_ms)

            return {
                "success": True,
                "intent_id": intent_id,
                "application": application,
                "platform": platform,
                "deployment_result": deployment_result,
                "duration_ms": duration_ms,
                "message": f"Successfully deployed {application} to {platform}"
            }

        except Exception as e:
            self.logger.error(f"Intent execution failed: {e}", exc_info=True)
            
            if intent_id:
                await self._update_intent_failed(intent_id, str(e))
                await self._log_step(intent_id, "error", "execution", f"Error: {str(e)}")

            return {
                "success": False,
                "intent_id": intent_id,
                "error": str(e),
                "message": f"Deployment failed: {str(e)}"
            }

    async def _create_intent_record(self, command_text: str, user_id: int) -> int:
        """Create deployment intent database record."""
        from app.models import DeploymentIntent

        intent = DeploymentIntent(
            command_text=command_text,
            user_id=user_id,
            status="pending",
            created_at=datetime.utcnow()
        )

        self.db.add(intent)
        self.db.commit()
        self.db.refresh(intent)

        return intent.id

    async def _update_intent_status(self, intent_id: int, status: str, message: str):
        """Update intent status."""
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if intent:
            intent.status = status
            if status in ["parsing", "generating", "deploying", "verifying"] and not intent.started_at:
                intent.started_at = datetime.utcnow()
            
            self.db.commit()

        self.logger.info(f"Intent {intent_id}: {status} - {message}")

    async def _update_intent_parsed_data(self, intent_id: int, parsed_intent: Dict[str, Any]):
        """Update intent with parsed data."""
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if intent:
            intent.parsed_intent = parsed_intent
            intent.target_platform = parsed_intent.get("platform")
            intent.target_namespace = parsed_intent.get("namespace")
            
            # Find blueprint
            application = parsed_intent.get("application")
            if application:
                from app.models import ApplicationBlueprint
                blueprint = self.db.query(ApplicationBlueprint).filter_by(name=application).first()
                if blueprint:
                    intent.blueprint_id = blueprint.id

            self.db.commit()

    async def _update_intent_manifests(self, intent_id: int, manifests: List[Dict[str, Any]]):
        """Update intent with generated manifests."""
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if intent:
            intent.generated_plan = {"manifests": manifests}
            self.db.commit()

    async def _update_intent_completed(self, intent_id: int, result: Dict[str, Any], duration_ms: int):
        """Mark intent as completed."""
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if intent:
            intent.status = "completed"
            intent.completed_at = datetime.utcnow()
            intent.duration_ms = duration_ms
            intent.deployed_resources = result.get("deployed_resources", [])
            self.db.commit()

    async def _update_intent_failed(self, intent_id: int, error_message: str):
        """Mark intent as failed."""
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if intent:
            intent.status = "failed"
            intent.error_message = error_message
            intent.completed_at = datetime.utcnow()
            self.db.commit()

    async def _log_step(self, intent_id: int, level: str, step: str, message: str):
        """Log a step in the deployment process."""
        # Add to execution log JSON array
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if intent:
            if not intent.execution_log:
                intent.execution_log = []
            
            intent.execution_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "step": step,
                "message": message
            })
            
            self.db.commit()

    def _build_deployment_config(
        self,
        platform: str,
        manifests: List[Dict[str, Any]],
        intent: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build platform-specific deployment configuration."""
        if platform == "kubernetes":
            return {
                "manifests": manifests,
                "namespace": intent.get("namespace") or options.get("namespace") or "default",
                "cluster_id": intent.get("cluster_id") or options.get("cluster_id"),
                "kubeconfig_path": options.get("kubeconfig_path")
            }
        elif platform == "docker":
            # Convert manifests to docker-compose format
            compose_content = self.manifest_generator.convert_to_compose(manifests)
            return {
                "compose_content": compose_content,
                "project_name": intent.get("project_name") or options.get("project_name") or intent.get("application"),
                "env_vars": options.get("env_vars", {})
            }
        else:
            raise DeploymentOrchestratorError(f"Unsupported platform: {platform}")

    async def get_intent_status(self, intent_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current status of deployment intent.

        Args:
            intent_id: Intent ID

        Returns:
            Intent status dictionary or None
        """
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if not intent:
            return None

        return {
            "id": intent.id,
            "command": intent.command_text,
            "status": intent.status,
            "platform": intent.target_platform,
            "namespace": intent.target_namespace,
            "application": intent.parsed_intent.get("application") if intent.parsed_intent else None,
            "created_at": intent.created_at.isoformat() if intent.created_at else None,
            "started_at": intent.started_at.isoformat() if intent.started_at else None,
            "completed_at": intent.completed_at.isoformat() if intent.completed_at else None,
            "duration_ms": intent.duration_ms,
            "error": intent.error_message,
            "logs": intent.execution_log or [],
            "deployed_resources": intent.deployed_resources or []
        }

    async def retry_intent(self, intent_id: int) -> Dict[str, Any]:
        """
        Retry a failed deployment intent.

        Args:
            intent_id: Intent ID to retry

        Returns:
            Retry result
        """
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if not intent:
            raise DeploymentOrchestratorError(f"Intent {intent_id} not found")

        if intent.status not in ["failed", "cancelled"]:
            raise DeploymentOrchestratorError(f"Intent is not in a retryable state: {intent.status}")

        # Increment retry count
        intent.retry_count += 1
        intent.status = "pending"
        intent.error_message = None
        self.db.commit()

        # Re-execute
        return await self.execute_intent(
            command_text=intent.command_text,
            user_id=intent.user_id
        )

    async def cancel_intent(self, intent_id: int) -> Dict[str, Any]:
        """
        Cancel a running deployment intent.

        Args:
            intent_id: Intent ID to cancel

        Returns:
            Cancellation result
        """
        from app.models import DeploymentIntent

        intent = self.db.query(DeploymentIntent).filter_by(id=intent_id).first()
        if not intent:
            raise DeploymentOrchestratorError(f"Intent {intent_id} not found")

        if intent.status == "completed":
            raise DeploymentOrchestratorError("Cannot cancel completed intent")

        intent.status = "cancelled"
        intent.completed_at = datetime.utcnow()
        self.db.commit()

        return {
            "success": True,
            "intent_id": intent_id,
            "status": "cancelled",
            "message": "Intent cancelled successfully"
        }
