from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import app.models as models
from app.services.containers.registry_client import RegistryClient

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Service for checking container updates"""
    
    def __init__(self, db: Session, enable_security_scan: bool = False):
        self.db = db
        self.registry_client = RegistryClient()
        self.enable_security_scan = enable_security_scan
        self._trivy_scanner = None
        self._policy_engine = None
        
        # Lazy-load security components if enabled
        if enable_security_scan:
            try:
                from app.services.containers.security.trivy_scanner import TrivyScanner
                from app.services.containers.security.policy_engine import SecurityPolicyEngine
                self._trivy_scanner = TrivyScanner(db)
                self._policy_engine = SecurityPolicyEngine(db)
                logger.info("Security scanning enabled for update checks")
            except ImportError as e:
                logger.warning(f"Security scanning requested but components not available: {e}")
                self.enable_security_scan = False
    
    async def check_all_containers(self) -> Dict[str, Any]:
        """Check for updates across all containers"""
        logger.info("Starting update checks for all containers...")
        
        containers = self.db.query(models.Container).filter(
            models.Container.exclude_from_updates == False
        ).all()
        
        total_checked = 0
        updates_found = 0
        security_blocked = 0
        errors = []
        
        for container in containers:
            try:
                result = await self.check_container_update(container.id)
                total_checked += 1
                if result and result.get("update_available"):
                    updates_found += 1
                if result and result.get("security_blocked"):
                    security_blocked += 1
            except Exception as e:
                error_msg = f"Failed to check updates for container '{container.name}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Update check complete. Checked {total_checked} containers, "
                   f"found {updates_found} updates available, {security_blocked} blocked by security policy")
        
        return {
            "total_checked": total_checked,
            "updates_found": updates_found,
            "security_blocked": security_blocked,
            "errors": errors
        }
    
    async def check_container_update(self, container_id: int) -> Optional[Dict[str, Any]]:
        """Check for updates for a specific container"""
        container = self.db.query(models.Container).filter(
            models.Container.id == container_id
        ).first()
        
        if not container:
            raise ValueError(f"Container with ID {container_id} not found")
        
        if container.exclude_from_updates:
            logger.info(f"Container {container.name} is excluded from updates")
            return None
        
        # Get current image and tag
        image_name = f"{container.image}:{container.current_tag}"
        
        logger.info(f"Checking for updates: {container.name} ({image_name})")
        
        try:
            # Query registry for latest digest
            registry_info = await self.registry_client.get_latest_digest(
                container.image, 
                container.current_tag
            )
            
            if not registry_info:
                logger.warning(f"Could not get registry info for {image_name}")
                return None
            
            registry_digest = registry_info.get("digest")
            
            # Compare digests
            update_available = False
            if container.current_digest and registry_digest:
                update_available = (container.current_digest != registry_digest)
            elif not container.current_digest:
                # If we don't have a current digest, assume update might be available
                update_available = True
            
            # Initialize security check results
            security_scan_id = None
            security_blocked = False
            security_warnings = []
            
            # Perform security scan if enabled and update is available
            if update_available and self.enable_security_scan and self._trivy_scanner:
                logger.info(f"Performing security scan for {container.name} update")
                try:
                    # Scan the new image
                    target_image = f"{container.image}@{registry_digest}" if registry_digest else f"{container.image}:{container.current_tag}"
                    scan_result = await self._trivy_scanner.scan_image(
                        image=target_image,
                        container_id=container.id,
                        scan_type="pre-update"
                    )
                    
                    if scan_result:
                        security_scan_id = scan_result.id
                        
                        # Evaluate against security policy
                        policy_result = await self._policy_engine.evaluate_update(
                            container_id=container.id,
                            new_scan_id=scan_result.id
                        )
                        
                        security_blocked = not policy_result["allowed"]
                        security_warnings = policy_result.get("violations", [])
                        
                        if security_blocked:
                            logger.warning(
                                f"Update blocked by security policy for {container.name}: "
                                f"{len(security_warnings)} violations found"
                            )
                        elif security_warnings:
                            logger.info(
                                f"Security warnings for {container.name}: "
                                f"{len(security_warnings)} issues found but update allowed"
                            )
                        
                        # Update container security fields
                        container.security_score = scan_result.security_score
                        container.critical_cves = scan_result.critical_count
                        container.high_cves = scan_result.high_count
                        container.last_scanned_at = scan_result.scanned_at
                        
                except Exception as e:
                    logger.error(f"Security scan failed for {container.name}: {e}")
                    # Don't block update on scan failure, just log
                    security_warnings.append(f"Security scan failed: {str(e)}")
            
            # Create update check record with security info
            metadata = {
                "registry_info": registry_info,
                "security_scan_id": security_scan_id,
                "security_blocked": security_blocked,
                "security_warnings": security_warnings
            }
            
            update_check = models.UpdateCheck(
                container_id=container.id,
                checked_at=datetime.utcnow(),
                update_available=update_available,
                current_tag=container.current_tag,
                current_digest=container.current_digest,
                available_tag=container.current_tag,
                available_digest=registry_digest,
                registry_data=registry_info,
                metadata=metadata
            )
            
            self.db.add(update_check)
            
            # Update container record
            container.last_checked = datetime.utcnow()
            container.update_available = update_available and not security_blocked
            container.available_digest = registry_digest
            
            self.db.commit()
            self.db.refresh(update_check)
            
            result_msg = f"Container {container.name}: Update available = {update_available}"
            if security_blocked:
                result_msg += " (BLOCKED by security policy)"
            logger.info(result_msg)
            
            return {
                "container_id": container.id,
                "container_name": container.name,
                "current_digest": container.current_digest,
                "available_digest": registry_digest,
                "update_available": update_available,
                "security_scan_id": security_scan_id,
                "security_blocked": security_blocked,
                "security_warnings": security_warnings,
                "checked_at": update_check.checked_at
            }
            
        except Exception as e:
            logger.error(f"Error checking updates for {container.name}: {e}")
            raise
    
    async def check_host_containers(self, host_id: int) -> Dict[str, Any]:
        """Check for updates for all containers on a specific host"""
        containers = self.db.query(models.Container).filter(
            models.Container.host_id == host_id,
            models.Container.exclude_from_updates == False
        ).all()
        
        total_checked = 0
        updates_found = 0
        security_blocked = 0
        errors = []
        
        for container in containers:
            try:
                result = await self.check_container_update(container.id)
                total_checked += 1
                if result and result.get("update_available"):
                    updates_found += 1
                if result and result.get("security_blocked"):
                    security_blocked += 1
            except Exception as e:
                error_msg = f"Failed to check updates for container '{container.name}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "host_id": host_id,
            "total_checked": total_checked,
            "updates_found": updates_found,
            "security_blocked": security_blocked,
            "errors": errors
        }
