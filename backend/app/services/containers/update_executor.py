import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import app.models as models
from app.services.containers.container_runtime_manager import DockerManager
from app.services.containers.container_backup import ContainerBackup
from app.services.containers.health_validator import HealthValidator

logger = logging.getLogger(__name__)


class UpdateExecutor:
    """Service for executing container updates with safety checks and rollback"""
    
    def __init__(self, db: Session, docker_manager: DockerManager, enable_security_validation: bool = False):
        self.db = db
        self.docker_manager = docker_manager
        self.enable_security_validation = enable_security_validation
        self._trivy_scanner = None
        self._policy_engine = None
        
        # Lazy-load security components if enabled
        if enable_security_validation:
            try:
                from app.services.containers.security.trivy_scanner import TrivyScanner
                from app.services.containers.security.policy_engine import SecurityPolicyEngine
                self._trivy_scanner = TrivyScanner(db)
                self._policy_engine = SecurityPolicyEngine(db)
                logger.info("Security validation enabled for updates")
            except ImportError as e:
                logger.warning(f"Security validation requested but components not available: {e}")
                self.enable_security_validation = False
    
    async def execute_update(
        self,
        container_id: int,
        update_type: str = "manual",
        dry_run: bool = False,
        skip_security_check: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a container update with full safety checks.
        
        Args:
            container_id: Database container ID
            update_type: "manual", "automatic", or "scheduled"
            dry_run: If True, simulate update without executing
            skip_security_check: Override security policy (with audit logging)
        
        Returns:
            Dict with update result details
        """
        start_time = time.time()
        update_history = None
        backup_record = None
        old_container = None
        new_container = None
        pre_scan_id = None
        post_scan_id = None
        
        try:
            # Get container from database
            container = self.db.query(models.Container).filter(
                models.Container.id == container_id
            ).first()
            
            if not container:
                raise ValueError(f"Container with ID {container_id} not found")
            
            if not container.update_available:
                raise ValueError(f"No update available for container {container.name}")
            
            # Dry-run mode: simulate update without executing
            if dry_run:
                return await self._simulate_update(container, update_type)
            
            logger.info(f"Starting update for container {container.name} (ID: {container_id})")
            
            # Get Docker client for container's host
            docker_client = await self.docker_manager.get_client(container.host_id)
            
            # Create backup and health services
            backup_service = ContainerBackup(docker_client, self.db)
            health_service = HealthValidator(docker_client)
            
            # Create update history record
            update_history = models.UpdateHistory(
                container_id=container.id,
                update_type=update_type,
                from_image=container.image,
                to_image=container.image,
                from_tag=container.current_tag,
                to_tag=container.available_tag or container.current_tag,
                status="in_progress",
                started_at=datetime.utcnow()
            )
            self.db.add(update_history)
            self.db.commit()
            self.db.refresh(update_history)
            
            # Pre-update security validation
            if self.enable_security_validation and self._trivy_scanner and not skip_security_check:
                logger.info(f"Performing pre-update security scan for {container.name}")
                try:
                    # Scan the target image
                    target_image = f"{container.image}:{container.available_tag or container.current_tag}"
                    if container.available_digest:
                        target_image = f"{container.image}@{container.available_digest}"
                    
                    pre_scan = await self._trivy_scanner.scan_image(
                        image=target_image,
                        container_id=container.id,
                        scan_type="pre-update"
                    )
                    
                    if pre_scan:
                        pre_scan_id = pre_scan.id
                        
                        # Evaluate against security policy
                        policy_result = await self._policy_engine.evaluate_update(
                            container_id=container.id,
                            new_scan_id=pre_scan.id
                        )
                        
                        if not policy_result["allowed"]:
                            violations = policy_result.get("violations", [])
                            violation_msg = f"Update blocked by security policy: {len(violations)} violations"
                            logger.error(f"{violation_msg} for {container.name}")
                            
                            # Update history with security block
                            update_history.status = "security_blocked"
                            update_history.success = False
                            update_history.completed_at = datetime.utcnow()
                            update_history.execution_duration = time.time() - start_time
                            update_history.error_message = violation_msg
                            update_history.logs = f"Security violations:\n" + "\n".join(
                                f"- {v.get('type', 'unknown')}: {v.get('message', 'no details')}"
                                for v in violations
                            )
                            update_history.metadata = {
                                "pre_scan_id": pre_scan_id,
                                "security_violations": violations,
                                "security_score": pre_scan.security_score
                            }
                            self.db.commit()
                            
                            return {
                                "success": False,
                                "error": violation_msg,
                                "container_id": container_id,
                                "security_blocked": True,
                                "violations": violations,
                                "pre_scan_id": pre_scan_id,
                                "update_history_id": update_history.id
                            }
                        
                        logger.info(
                            f"Pre-update security check passed for {container.name} "
                            f"(score: {pre_scan.security_score}/100)"
                        )
                        
                except Exception as e:
                    logger.error(f"Pre-update security scan failed for {container.name}: {e}")
                    # Don't block on scan failure unless policy requires it
                    if not skip_security_check:
                        logger.warning("Continuing with update despite scan failure")
            
            elif skip_security_check:
                logger.warning(
                    f"Security check BYPASSED for {container.name} by user request. "
                    f"Update type: {update_type}"
                )
            
            # Step 1: Create backup
            logger.info(f"Creating backup for {container.name}")
            backup_record = await backup_service.backup_container(
                container.container_id,
                backup_type="config"
            )
            
            if not backup_record:
                raise Exception("Failed to create container backup")
            
            update_history.backup_id = backup_record.id
            update_history.backup_created = True
            update_history.backup_path = backup_record.backup_path
            update_history.rollback_available = True
            self.db.commit()
            
            # Step 2: Get current container
            try:
                old_container = docker_client.containers.get(container.container_id)
            except Exception as e:
                raise Exception(f"Failed to get current container: {e}")
            
            # Step 3: Pull new image
            new_image_tag = f"{container.image}:{container.available_tag or container.current_tag}"
            logger.info(f"Pulling new image: {new_image_tag}")
            
            try:
                docker_client.images.pull(new_image_tag)
            except Exception as e:
                raise Exception(f"Failed to pull image {new_image_tag}: {e}")
            
            # Step 4: Stop old container
            logger.info(f"Stopping old container {container.name}")
            try:
                old_container.stop(timeout=30)
            except Exception as e:
                logger.warning(f"Error stopping container (may already be stopped): {e}")
            
            # Step 5: Rename old container for safety
            old_container_name = f"{container.name}_old_{int(time.time())}"
            try:
                old_container.rename(old_container_name)
                logger.info(f"Renamed old container to {old_container_name}")
            except Exception as e:
                logger.warning(f"Failed to rename old container: {e}")
            
            # Step 6: Create new container with same configuration
            logger.info(f"Creating new container with image {new_image_tag}")
            
            config = backup_record.backup_metadata.get("config", {})
            host_config = backup_record.backup_metadata.get("host_config", {})
            
            try:
                new_container = docker_client.containers.create(
                    image=new_image_tag,
                    name=container.name,
                    command=config.get("Cmd"),
                    entrypoint=config.get("Entrypoint"),
                    environment=config.get("Env", []),
                    ports=host_config.get("PortBindings", {}),
                    volumes=host_config.get("Binds", []),
                    network_mode=host_config.get("NetworkMode", "bridge"),
                    restart_policy=host_config.get("RestartPolicy", {}),
                    labels=config.get("Labels", {}),
                    working_dir=config.get("WorkingDir"),
                    user=config.get("User"),
                    privileged=host_config.get("Privileged", False),
                    cap_add=host_config.get("CapAdd"),
                    cap_drop=host_config.get("CapDrop"),
                    detach=True
                )
            except Exception as e:
                # Failed to create new container, try to restore old one
                logger.error(f"Failed to create new container: {e}")
                await self._restore_old_container(old_container, container.name)
                raise Exception(f"Failed to create new container: {e}")
            
            # Step 7: Start new container
            logger.info(f"Starting new container")
            try:
                new_container.start()
            except Exception as e:
                logger.error(f"Failed to start new container: {e}")
                new_container.remove(force=True)
                await self._restore_old_container(old_container, container.name)
                raise Exception(f"Failed to start new container: {e}")
            
            # Step 8: Validate health
            logger.info(f"Validating health of new container")
            health_result = await health_service.validate_container_health(new_container)
            
            update_history.health_check_result = health_result
            self.db.commit()
            
            if not health_result.get("healthy"):
                # Health check failed, rollback
                logger.error(f"Health check failed: {health_result.get('errors')}")
                
                # Stop and remove new container
                try:
                    new_container.stop(timeout=10)
                    new_container.remove(force=True)
                except Exception as e:
                    logger.error(f"Error removing failed container: {e}")
                
                # Restore old container
                await self._restore_old_container(old_container, container.name)
                
                raise Exception(f"Health check failed: {health_result.get('errors')}")
            
            # Post-update security scan
            if self.enable_security_validation and self._trivy_scanner:
                logger.info(f"Performing post-update security scan for {container.name}")
                try:
                    post_scan = await self._trivy_scanner.scan_image(
                        image=new_image_tag,
                        container_id=container.id,
                        scan_type="post-update"
                    )
                    
                    if post_scan:
                        post_scan_id = post_scan.id
                        
                        # Compare with pre-scan if available
                        if pre_scan_id:
                            comparison = await self._trivy_scanner.compare_scans(
                                pre_scan_id, post_scan_id
                            )
                            
                            if comparison.get("regression"):
                                logger.warning(
                                    f"Security regression detected for {container.name}: "
                                    f"score decreased by {comparison.get('score_change', 0)} points"
                                )
                            else:
                                logger.info(
                                    f"Security improved for {container.name}: "
                                    f"score changed by {comparison.get('score_change', 0)} points"
                                )
                        
                        # Update container security fields
                        container.security_score = post_scan.security_score
                        container.critical_cves = post_scan.critical_count
                        container.high_cves = post_scan.high_count
                        container.last_scanned_at = post_scan.scanned_at
                        
                except Exception as e:
                    logger.error(f"Post-update security scan failed: {e}")
                    # Don't rollback on post-scan failure
            
            # Step 9: Success! Remove old container
            logger.info(f"Update successful, removing old container")
            try:
                old_container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove old container: {e}")
            
            # Update container record in database
            container.current_tag = container.available_tag or container.current_tag
            container.current_digest = container.available_digest
            container.update_available = False
            container.available_tag = None
            container.available_digest = None
            container.container_id = new_container.id
            
            # Complete update history
            execution_duration = time.time() - start_time
            update_history.status = "success"
            update_history.success = True
            update_history.completed_at = datetime.utcnow()
            update_history.execution_duration = execution_duration
            update_history.logs = f"Update completed successfully in {execution_duration:.2f}s"
            update_history.metadata = {
                "pre_scan_id": pre_scan_id,
                "post_scan_id": post_scan_id,
                "security_check_bypassed": skip_security_check
            }
            
            self.db.commit()
            
            logger.info(
                f"Container {container.name} updated successfully from "
                f"{update_history.from_tag} to {update_history.to_tag} "
                f"in {execution_duration:.2f}s"
            )
            
            return {
                "success": True,
                "container_id": container.id,
                "container_name": container.name,
                "from_tag": update_history.from_tag,
                "to_tag": update_history.to_tag,
                "execution_duration": execution_duration,
                "health_check": health_result,
                "pre_scan_id": pre_scan_id,
                "post_scan_id": post_scan_id,
                "update_history_id": update_history.id
            }
            
        except Exception as e:
            logger.error(f"Update failed for container {container_id}: {e}")
            
            # Update history with failure
            if update_history:
                execution_duration = time.time() - start_time
                update_history.status = "failed"
                update_history.success = False
                update_history.completed_at = datetime.utcnow()
                update_history.execution_duration = execution_duration
                update_history.error_message = str(e)
                update_history.logs = f"Update failed: {str(e)}"
                if pre_scan_id:
                    update_history.metadata = {"pre_scan_id": pre_scan_id}
                self.db.commit()
            
            return {
                "success": False,
                "error": str(e),
                "container_id": container_id,
                "update_history_id": update_history.id if update_history else None
            }
    
    async def rollback_update(
        self,
        update_history_id: int
    ) -> Dict[str, Any]:
        """
        Rollback a container update using backup.
        
        Args:
            update_history_id: UpdateHistory record ID
        
        Returns:
            Dict with rollback result
        """
        try:
            # Get update history
            update_history = self.db.query(models.UpdateHistory).filter(
                models.UpdateHistory.id == update_history_id
            ).first()
            
            if not update_history:
                raise ValueError(f"Update history {update_history_id} not found")
            
            if not update_history.rollback_available:
                raise ValueError("Rollback not available for this update")
            
            if not update_history.backup_id:
                raise ValueError("No backup available for rollback")
            
            # Get backup record
            backup_record = self.db.query(models.BackupRecord).filter(
                models.BackupRecord.id == update_history.backup_id
            ).first()
            
            if not backup_record:
                raise ValueError("Backup record not found")
            
            # Get container
            container = self.db.query(models.Container).filter(
                models.Container.id == update_history.container_id
            ).first()
            
            if not container:
                raise ValueError("Container not found")
            
            logger.info(f"Rolling back update {update_history_id} for container {container.name}")
            
            # Get Docker client
            docker_client = await self.docker_manager.get_client(container.host_id)
            backup_service = ContainerBackup(docker_client, self.db)
            
            # Restore from backup
            success = await backup_service.restore_container(backup_record, force=True)
            
            if not success:
                raise Exception("Failed to restore container from backup")
            
            # Update records
            update_history.rolled_back = True
            update_history.rollback_at = datetime.utcnow()
            update_history.rollback_reason = "Manual rollback requested"
            update_history.status = "rolled_back"
            
            # Revert container record
            container.current_tag = update_history.from_tag
            container.update_available = True
            container.available_tag = update_history.to_tag
            
            self.db.commit()
            
            logger.info(f"Successfully rolled back update for {container.name}")
            
            return {
                "success": True,
                "container_id": container.id,
                "container_name": container.name,
                "rolled_back_from": update_history.to_tag,
                "restored_to": update_history.from_tag
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _simulate_update(
        self,
        container: models.Container,
        update_type: str
    ) -> Dict[str, Any]:
        """
        Simulate an update without executing it (dry-run mode).
        
        Returns:
            Dict with simulation results
        """
        logger.info(f"DRY-RUN: Simulating update for container {container.name}")
        
        try:
            # Get Docker client
            docker_client = await self.docker_manager.get_client(container.host_id)
            
            # Simulate: Get current container
            try:
                old_container = docker_client.containers.get(container.container_id)
                logger.info(f"DRY-RUN: Retrieved current container {container.name}")
            except Exception as e:
                return {
                    "success": False,
                    "dry_run": True,
                    "error": f"Failed to get current container: {e}",
                    "container_id": container.id
                }
            
            # Simulate: Check if new image exists
            new_image_tag = f"{container.image}:{container.available_tag or container.current_tag}"
            logger.info(f"DRY-RUN: Would pull image: {new_image_tag}")
            
            # Try to inspect the image (without pulling)
            try:
                try:
                    docker_client.images.get(new_image_tag)
                    image_available = True
                    logger.info(f"DRY-RUN: Image {new_image_tag} already available locally")
                except:
                    image_available = False
                    logger.info(f"DRY-RUN: Image {new_image_tag} would need to be pulled")
            except Exception as e:
                logger.warning(f"DRY-RUN: Could not verify image availability: {e}")
                image_available = None
            
            # Simulate: Get container configuration
            container_config = old_container.attrs
            config = container_config.get("Config", {})
            host_config = container_config.get("HostConfig", {})
            
            logger.info(f"DRY-RUN: Retrieved container configuration")
            
            # Build simulation steps
            steps = [
                {"step": 0, "action": "Pre-update security scan", "status": "would_check" if self.enable_security_validation else "skipped"},
                {"step": 1, "action": "Create backup", "status": "would_succeed"},
                {"step": 2, "action": "Get current container", "status": "success"},
                {"step": 3, "action": f"Pull image {new_image_tag}", 
                 "status": "would_succeed" if image_available is not False else "might_fail"},
                {"step": 4, "action": f"Stop container {container.name}", "status": "would_succeed"},
                {"step": 5, "action": "Rename old container", "status": "would_succeed"},
                {"step": 6, "action": "Create new container", "status": "would_succeed"},
                {"step": 7, "action": "Start new container", "status": "would_succeed"},
                {"step": 8, "action": "Validate health", "status": "would_check"},
                {"step": 9, "action": "Post-update security scan", "status": "would_check" if self.enable_security_validation else "skipped"},
                {"step": 10, "action": "Remove old container", "status": "would_succeed"}
            ]
            
            # Return simulation results
            return {
                "success": True,
                "dry_run": True,
                "container_id": container.id,
                "container_name": container.name,
                "from_tag": container.current_tag,
                "to_tag": container.available_tag,
                "new_image": new_image_tag,
                "image_available_locally": image_available,
                "update_type": update_type,
                "security_validation_enabled": self.enable_security_validation,
                "simulated_steps": steps,
                "message": f"Dry-run successful. Update would proceed: {container.name} from {container.current_tag} to {container.available_tag}",
                "warnings": [
                    "This is a simulation. No actual changes were made.",
                    "Actual execution may differ based on runtime conditions."
                ]
            }
            
        except Exception as e:
            logger.error(f"DRY-RUN: Simulation failed: {e}")
            return {
                "success": False,
                "dry_run": True,
                "error": str(e),
                "container_id": container.id,
                "message": "Dry-run simulation encountered an error"
            }
    
    async def _restore_old_container(self, old_container, original_name: str):
        """Helper to restore old container after failed update"""
        try:
            logger.info(f"Restoring old container {original_name}")
            old_container.rename(original_name)
            old_container.start()
            logger.info(f"Old container restored successfully")
        except Exception as e:
            logger.error(f"Failed to restore old container: {e}")
            raise Exception(f"Critical: Failed to restore old container: {e}")
