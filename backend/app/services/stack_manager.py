"""
Stack management service for Docker Compose deployments.
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import docker

from backend.app.models.stack import Stack, StackDeployment
from backend.app.schemas.stack import (
    StackCreate, StackUpdate, ValidationResult, ContainerStatus, StackStatusResponse
)
from backend.app.services.compose_validator import ComposeValidator
from backend.app.services.label_injector import LabelInjector
from backend.app.core.logging import get_logger
from backend.app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class StackManager:
    """
    Manages Docker Compose stacks including validation, deployment, and monitoring.
    """
    
    def __init__(self):
        self.validator = ComposeValidator()
        self.label_injector = LabelInjector()
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
        
        # Get base deployment path from settings or use default
        self.deployments_base = Path(
            os.getenv("UNITY_DEPLOYMENTS_PATH", "/tmp/unity/deployments")
        )
        self.deployments_base.mkdir(parents=True, exist_ok=True)
    
    def create_stack(self, db: Session, stack_data: StackCreate, deployed_by: str = "unity") -> Stack:
        """
        Create a new stack.
        
        Args:
            db: Database session
            stack_data: Stack creation data
            deployed_by: User creating the stack
            
        Returns:
            Created Stack object
        """
        # Check if stack name already exists
        existing = db.query(Stack).filter(Stack.name == stack_data.name).first()
        if existing:
            raise ValueError(f"Stack with name '{stack_data.name}' already exists")
        
        # Create deployment directory
        stack_path = self.deployments_base / stack_data.name
        stack_path.mkdir(parents=True, exist_ok=True)
        
        # Save original compose file
        compose_file = stack_path / "docker-compose.yml"
        compose_file.write_text(stack_data.compose_content)
        
        # Inject Unity labels and save
        compose_with_labels = self.label_injector.inject_labels(
            stack_data.compose_content,
            stack_data.name,
            deployed_by
        )
        unity_compose_file = stack_path / "docker-compose.unity.yml"
        unity_compose_file.write_text(compose_with_labels)
        
        # Save metadata
        metadata = {
            "name": stack_data.name,
            "description": stack_data.description,
            "created_at": datetime.utcnow().isoformat(),
            "deployed_by": deployed_by
        }
        metadata_file = stack_path / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        # Save env vars if provided
        if stack_data.env_vars:
            self._save_env_file(stack_path, stack_data.env_vars)
        
        # Create database record
        stack = Stack(
            name=stack_data.name,
            description=stack_data.description,
            compose_content=stack_data.compose_content,
            env_vars=stack_data.env_vars,
            deployment_path=str(stack_path),
            status="stopped",
            deployed_by=deployed_by,
            labels=stack_data.labels
        )
        
        db.add(stack)
        db.commit()
        db.refresh(stack)
        
        logger.info(f"Created stack '{stack_data.name}' at {stack_path}")
        return stack
    
    def update_stack(self, db: Session, stack_name: str, stack_update: StackUpdate) -> Stack:
        """Update an existing stack."""
        stack = db.query(Stack).filter(Stack.name == stack_name).first()
        if not stack:
            raise ValueError(f"Stack '{stack_name}' not found")
        
        # Update fields
        if stack_update.description is not None:
            stack.description = stack_update.description
        
        if stack_update.compose_content is not None:
            stack.compose_content = stack_update.compose_content
            # Update files
            stack_path = Path(stack.deployment_path)
            compose_file = stack_path / "docker-compose.yml"
            compose_file.write_text(stack_update.compose_content)
            
            # Regenerate Unity compose
            compose_with_labels = self.label_injector.inject_labels(
                stack_update.compose_content,
                stack_name,
                stack.deployed_by or "unity"
            )
            unity_compose_file = stack_path / "docker-compose.unity.yml"
            unity_compose_file.write_text(compose_with_labels)
        
        if stack_update.env_vars is not None:
            stack.env_vars = stack_update.env_vars
            stack_path = Path(stack.deployment_path)
            self._save_env_file(stack_path, stack_update.env_vars)
        
        if stack_update.labels is not None:
            stack.labels = stack_update.labels
        
        stack.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(stack)
        
        logger.info(f"Updated stack '{stack_name}'")
        return stack
    
    def delete_stack(self, db: Session, stack_name: str) -> bool:
        """Delete a stack and its files."""
        stack = db.query(Stack).filter(Stack.name == stack_name).first()
        if not stack:
            raise ValueError(f"Stack '{stack_name}' not found")
        
        # Stop and remove containers if running
        if stack.status == "running":
            try:
                self.destroy_stack(db, stack_name)
            except Exception as e:
                logger.warning(f"Failed to destroy stack before deletion: {e}")
        
        # Delete files
        stack_path = Path(stack.deployment_path)
        if stack_path.exists():
            import shutil
            shutil.rmtree(stack_path)
            logger.info(f"Deleted stack directory: {stack_path}")
        
        # Delete database record
        db.delete(stack)
        db.commit()
        
        logger.info(f"Deleted stack '{stack_name}'")
        return True
    
    def validate_stack(self, compose_content: str, stack_name: str) -> ValidationResult:
        """Validate a compose file."""
        return self.validator.validate(compose_content, stack_name)
    
    def deploy_stack(self, db: Session, stack_name: str, env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Deploy a stack using docker compose.
        
        Args:
            db: Database session
            stack_name: Name of the stack to deploy
            env_vars: Optional environment variables for this deployment
            
        Returns:
            Deployment result
        """
        stack = db.query(Stack).filter(Stack.name == stack_name).first()
        if not stack:
            raise ValueError(f"Stack '{stack_name}' not found")
        
        # Update env vars if provided
        if env_vars:
            stack.env_vars = env_vars
            stack_path = Path(stack.deployment_path)
            self._save_env_file(stack_path, env_vars)
            db.commit()
        
        # Create deployment record
        deployment = StackDeployment(
            stack_id=stack.id,
            action="deploy",
            status="in_progress"
        )
        db.add(deployment)
        db.commit()
        
        try:
            # Run docker compose up
            stack_path = Path(stack.deployment_path)
            compose_file = stack_path / "docker-compose.unity.yml"
            env_file = stack_path / ".env"
            
            cmd = ["docker", "compose", "-f", str(compose_file), "-p", stack_name]
            
            if env_file.exists():
                cmd.extend(["--env-file", str(env_file)])
            
            cmd.extend(["up", "-d"])
            
            logger.info(f"Deploying stack '{stack_name}': {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(stack_path)
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to deploy stack '{stack_name}': {error_msg}")
                
                # Update deployment record
                deployment.status = "failed"
                deployment.error_message = error_msg
                stack.status = "error"
                db.commit()
                
                return {
                    "success": False,
                    "message": f"Failed to deploy stack '{stack_name}'",
                    "error": error_msg
                }
            
            # Success
            deployment.status = "success"
            stack.status = "running"
            stack.deployed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Successfully deployed stack '{stack_name}'")
            
            return {
                "success": True,
                "message": f"Stack '{stack_name}' deployed successfully",
                "output": result.stdout
            }
            
        except Exception as e:
            logger.error(f"Exception during stack deployment: {e}")
            deployment.status = "failed"
            deployment.error_message = str(e)
            stack.status = "error"
            db.commit()
            
            return {
                "success": False,
                "message": f"Exception during deployment: {str(e)}",
                "error": str(e)
            }
    
    def stop_stack(self, db: Session, stack_name: str) -> Dict[str, Any]:
        """Stop a running stack."""
        return self._execute_compose_command(db, stack_name, ["stop"], "stop")
    
    def restart_stack(self, db: Session, stack_name: str) -> Dict[str, Any]:
        """Restart a stack."""
        return self._execute_compose_command(db, stack_name, ["restart"], "restart")
    
    def destroy_stack(self, db: Session, stack_name: str) -> Dict[str, Any]:
        """Destroy a stack (removes containers, networks, volumes)."""
        return self._execute_compose_command(db, stack_name, ["down", "-v"], "destroy")
    
    def get_stack_status(self, db: Session, stack_name: str) -> StackStatusResponse:
        """Get detailed status of a stack."""
        stack = db.query(Stack).filter(Stack.name == stack_name).first()
        if not stack:
            raise ValueError(f"Stack '{stack_name}' not found")
        
        # Get containers for this stack
        containers = []
        if self.docker_client:
            try:
                all_containers = self.docker_client.containers.list(all=True)
                for container in all_containers:
                    labels = container.labels
                    if labels.get("unity.stack") == stack_name:
                        containers.append(ContainerStatus(
                            container_id=container.id[:12],
                            name=container.name,
                            status=container.status,
                            image=container.image.tags[0] if container.image.tags else container.image.id[:12],
                            created=datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00'))
                        ))
            except Exception as e:
                logger.error(f"Failed to get containers for stack: {e}")
        
        # Get last error if any
        last_deployment = db.query(StackDeployment).filter(
            StackDeployment.stack_id == stack.id,
            StackDeployment.status == "failed"
        ).order_by(StackDeployment.deployed_at.desc()).first()
        
        last_error = last_deployment.error_message if last_deployment else None
        
        return StackStatusResponse(
            stack_name=stack_name,
            status=stack.status,
            containers=containers,
            deployed_at=stack.deployed_at,
            last_error=last_error
        )
    
    def _execute_compose_command(self, db: Session, stack_name: str, compose_args: List[str], action: str) -> Dict[str, Any]:
        """Execute a docker compose command."""
        stack = db.query(Stack).filter(Stack.name == stack_name).first()
        if not stack:
            raise ValueError(f"Stack '{stack_name}' not found")
        
        # Create deployment record
        deployment = StackDeployment(
            stack_id=stack.id,
            action=action,
            status="in_progress"
        )
        db.add(deployment)
        db.commit()
        
        try:
            stack_path = Path(stack.deployment_path)
            compose_file = stack_path / "docker-compose.unity.yml"
            
            cmd = ["docker", "compose", "-f", str(compose_file), "-p", stack_name] + compose_args
            
            logger.info(f"Executing command for stack '{stack_name}': {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(stack_path)
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to {action} stack '{stack_name}': {error_msg}")
                
                deployment.status = "failed"
                deployment.error_message = error_msg
                stack.status = "error"
                db.commit()
                
                return {
                    "success": False,
                    "message": f"Failed to {action} stack '{stack_name}'",
                    "error": error_msg
                }
            
            # Success
            deployment.status = "success"
            if action == "destroy":
                stack.status = "stopped"
            elif action == "stop":
                stack.status = "stopped"
            elif action == "restart":
                stack.status = "running"
            
            db.commit()
            
            logger.info(f"Successfully executed {action} for stack '{stack_name}'")
            
            return {
                "success": True,
                "message": f"Stack '{stack_name}' {action} successful",
                "output": result.stdout
            }
            
        except Exception as e:
            logger.error(f"Exception during {action}: {e}")
            deployment.status = "failed"
            deployment.error_message = str(e)
            stack.status = "error"
            db.commit()
            
            return {
                "success": False,
                "message": f"Exception during {action}: {str(e)}",
                "error": str(e)
            }
    
    def _save_env_file(self, stack_path: Path, env_vars: Dict[str, str]):
        """Save environment variables to .env file."""
        env_file = stack_path / ".env"
        env_content = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        env_file.write_text(env_content)
        logger.debug(f"Saved env file: {env_file}")
