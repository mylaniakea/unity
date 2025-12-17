"""Container management scheduled tasks for Phase 4: Uptainer Integration."""
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.containers import ContainerHost, Container
from app.services.containers.container_monitor import ContainerMonitor
from app.services.containers.update_checker import UpdateChecker
from app.services.containers.health_validator import HealthValidator

logger = logging.getLogger(__name__)

# Feature flags from environment
ENABLE_CONTAINERS = os.getenv("ENABLE_CONTAINERS", "true").lower() == "true"
ENABLE_CONTAINER_AI = os.getenv("ENABLE_CONTAINER_AI", "false").lower() == "true"
ENABLE_TRIVY = os.getenv("ENABLE_TRIVY", "false").lower() == "true"
CONTAINER_DISCOVERY_INTERVAL = int(os.getenv("CONTAINER_DISCOVERY_INTERVAL", "300"))  # 5 minutes
CONTAINER_UPDATE_CHECK_INTERVAL = int(os.getenv("CONTAINER_UPDATE_CHECK_INTERVAL", "3600"))  # 1 hour


async def discover_containers():
    """
    Discover containers on all enabled hosts.
    Runs every 5 minutes (configurable via CONTAINER_DISCOVERY_INTERVAL).
    """
    if not ENABLE_CONTAINERS:
        return
    
    db = SessionLocal()
    try:
        logger.info("Starting container discovery task...")
        
        # Get all enabled hosts
        hosts = db.query(ContainerHost).filter(ContainerHost.enabled == True).all()
        
        if not hosts:
            logger.debug("No enabled container hosts found")
            return
        
        total_discovered = 0
        total_updated = 0
        
        for host in hosts:
            try:
                logger.debug(f"Discovering containers on host: {host.name} (ID: {host.id})")
                
                # Initialize monitor
                monitor = ContainerMonitor(db)
                
                # Discover containers (this would call the runtime provider)
                # For now, we'll just log - actual implementation would connect to Docker/Podman/K8s
                result = await monitor.discover_host(host.id)
                
                discovered = result.get('discovered', 0)
                updated = result.get('updated', 0)
                
                total_discovered += discovered
                total_updated += updated
                
                logger.info(f"Host {host.name}: discovered={discovered}, updated={updated}")
                
            except Exception as e:
                logger.error(f"Error discovering containers on host {host.name}: {e}")
                continue
        
        logger.info(f"Container discovery completed: {total_discovered} discovered, {total_updated} updated")
        
    except Exception as e:
        logger.error(f"Container discovery task failed: {e}")
    finally:
        db.close()


async def check_container_updates():
    """
    Check for available updates on all containers.
    Runs every hour (configurable via CONTAINER_UPDATE_CHECK_INTERVAL).
    """
    if not ENABLE_CONTAINERS:
        return
    
    db = SessionLocal()
    try:
        logger.info("Starting container update check task...")
        
        # Get all containers
        containers = db.query(Container).filter(
            Container.exclude_from_updates == False
        ).all()
        
        if not containers:
            logger.debug("No containers found for update checking")
            return
        
        checker = UpdateChecker(db)
        updates_found = 0
        
        for container in containers:
            try:
                # Check for updates
                result = await checker.check_update(container.id)
                
                if result.get('update_available'):
                    updates_found += 1
                    logger.info(f"Update available for {container.name}: {container.current_tag} → {result.get('available_tag')}")
                
            except Exception as e:
                logger.error(f"Error checking updates for container {container.name}: {e}")
                continue
        
        logger.info(f"Update check completed: {updates_found} updates available")
        
    except Exception as e:
        logger.error(f"Container update check task failed: {e}")
    finally:
        db.close()


async def scan_container_security():
    """
    Run security scans on containers using Trivy.
    Runs daily at 2 AM.
    """
    if not ENABLE_CONTAINERS or not ENABLE_TRIVY:
        return
    
    db = SessionLocal()
    try:
        logger.info("Starting container security scan task...")
        
        from app.services.containers.security.trivy_scanner import TrivyScanner
        
        # Get all containers
        containers = db.query(Container).all()
        
        if not containers:
            logger.debug("No containers found for security scanning")
            return
        
        scanner = TrivyScanner(db)
        scanned = 0
        critical_found = 0
        
        for container in containers:
            try:
                # Scan container
                result = await scanner.scan_container(container.id)
                
                scanned += 1
                critical = result.get('critical_count', 0)
                critical_found += critical
                
                if critical > 0:
                    logger.warning(f"Critical vulnerabilities found in {container.name}: {critical}")
                
            except Exception as e:
                logger.error(f"Error scanning container {container.name}: {e}")
                continue
        
        logger.info(f"Security scan completed: {scanned} scanned, {critical_found} critical CVEs found")
        
    except Exception as e:
        logger.error(f"Container security scan task failed: {e}")
    finally:
        db.close()


async def execute_scheduled_backups():
    """
    Execute scheduled container backups.
    Runs daily at 1 AM.
    """
    if not ENABLE_CONTAINERS:
        return
    
    db = SessionLocal()
    try:
        logger.info("Starting scheduled container backups task...")
        
        from app.services.containers.container_backup import ContainerBackupService
        
        # Get containers with backup schedules
        # This would check container labels or policy settings
        containers = db.query(Container).filter(
            Container.labels.contains({'backup.enabled': 'true'})
        ).all()
        
        if not containers:
            logger.debug("No containers scheduled for backup")
            return
        
        backup_service = ContainerBackupService(db)
        backed_up = 0
        
        for container in containers:
            try:
                # Create backup
                result = await backup_service.backup_container(container.id)
                
                if result.get('success'):
                    backed_up += 1
                    logger.info(f"Backed up container: {container.name}")
                
            except Exception as e:
                logger.error(f"Error backing up container {container.name}: {e}")
                continue
        
        logger.info(f"Scheduled backups completed: {backed_up} containers backed up")
        
    except Exception as e:
        logger.error(f"Container backup task failed: {e}")
    finally:
        db.close()


async def validate_container_health():
    """
    Validate health status of running containers.
    Runs every 10 minutes.
    """
    if not ENABLE_CONTAINERS:
        return
    
    db = SessionLocal()
    try:
        logger.info("Starting container health validation task...")
        
        # Get running containers
        containers = db.query(Container).filter(
            Container.status == 'running'
        ).all()
        
        if not containers:
            logger.debug("No running containers found for health check")
            return
        
        validator = HealthValidator(db)
        checked = 0
        unhealthy = 0
        
        for container in containers:
            try:
                # Validate health
                result = await validator.check_health(container.id)
                
                checked += 1
                
                if not result.get('healthy'):
                    unhealthy += 1
                    logger.warning(f"Unhealthy container detected: {container.name}")
                    
                    # Create alert if needed
                    if result.get('create_alert'):
                        from app.models.monitoring import Alert
                        alert = Alert(
                            source='container',
                            message=f"Container {container.name} is unhealthy",
                            severity='high',
                            metadata={'container_id': container.id}
                        )
                        db.add(alert)
                        db.commit()
                
            except Exception as e:
                logger.error(f"Error checking health for container {container.name}: {e}")
                continue
        
        logger.info(f"Health validation completed: {checked} checked, {unhealthy} unhealthy")
        
    except Exception as e:
        logger.error(f"Container health validation task failed: {e}")
    finally:
        db.close()


def setup_container_scheduler(scheduler: AsyncIOScheduler):
    """
    Setup container management tasks in the APScheduler.
    
    Args:
        scheduler: APScheduler instance
    """
    if not ENABLE_CONTAINERS:
        logger.info("Container management disabled (ENABLE_CONTAINERS=false)")
        return
    
    # Container discovery (every 5 minutes by default)
    discovery_minutes = CONTAINER_DISCOVERY_INTERVAL // 60
    scheduler.add_job(
        discover_containers,
        'interval',
        minutes=discovery_minutes,
        id='container_discovery',
        name='Container Discovery',
        replace_existing=True
    )
    
    # Update checking (every hour by default)
    update_minutes = CONTAINER_UPDATE_CHECK_INTERVAL // 60
    scheduler.add_job(
        check_container_updates,
        'interval',
        minutes=update_minutes,
        id='container_update_check',
        name='Container Update Check',
        replace_existing=True
    )
    
    # Security scanning (daily at 2 AM)
    if ENABLE_TRIVY:
        scheduler.add_job(
            scan_container_security,
            'cron',
            hour=2,
            minute=0,
            id='container_security_scan',
            name='Container Security Scan',
            replace_existing=True
        )
    
    # Scheduled backups (daily at 1 AM)
    scheduler.add_job(
        execute_scheduled_backups,
        'cron',
        hour=1,
        minute=0,
        id='container_backups',
        name='Container Scheduled Backups',
        replace_existing=True
    )
    
    # Health validation (every 10 minutes)
    scheduler.add_job(
        validate_container_health,
        'interval',
        minutes=10,
        id='container_health_check',
        name='Container Health Validation',
        replace_existing=True
    )
    
    logger.info("Container management scheduler tasks configured")
    logger.info(f"  - Discovery: every {discovery_minutes} minutes")
    logger.info(f"  - Update check: every {update_minutes} minutes")
    if ENABLE_TRIVY:
        logger.info("  - Security scan: daily at 2:00 AM")
    logger.info("  - Backups: daily at 1:00 AM")
    logger.info("  - Health check: every 10 minutes")
