"""
Certificate rotation scheduler.

Automatically rotates certificates that are expiring within 30 days.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from typing import Optional

from .database import SessionLocal
from . import crud, step_ca, distribution, schemas
from .logger import get_logger

logger = get_logger(__name__)


def rotate_certificates() -> None:
    """
    Rotates certificates that are expiring within the next 30 days.
    
    This function:
    1. Creates a new DB session for this job
    2. Queries all certificates
    3. Finds certificates expiring in < 30 days
    4. Issues new certificates via step-ca
    5. Stores new certificates in database
    6. Distributes certificates to servers
    7. Closes DB session
    """
    db = SessionLocal()
    try:
        logger.info("Starting certificate rotation job")
        certificates = crud.get_certificates(db)
        rotation_threshold = datetime.utcnow() + timedelta(days=30)
        rotated_count = 0
        
        for certificate in certificates:
            if certificate.expires_at < rotation_threshold:
                db_server = crud.get_server(db, certificate.server_id)
                if not db_server:
                    logger.warning(
                        f"Certificate {certificate.id} references non-existent "
                        f"server {certificate.server_id}, skipping"
                    )
                    continue
                
                try:
                    logger.info(f"Rotating certificate for {db_server.hostname}")
                    cert, key = step_ca.issue_certificate(db_server.hostname)
                    
                    expires_at = datetime.utcnow() + timedelta(days=90)
                    
                    new_certificate = schemas.CertificateCreate(
                        certificate=cert,
                        key=key,
                        expires_at=expires_at,
                        server_id=certificate.server_id,
                    )
                    crud.create_certificate(db, new_certificate)
                    
                    # Distribute to server
                    distribution.distribute_certificate(db_server, cert, key)
                    
                    rotated_count += 1
                    logger.info(f"✓ Rotated certificate for {db_server.hostname}")
                    
                except Exception as e:
                    logger.error(
                        f"✗ Failed to rotate certificate for {db_server.hostname}: {e}",
                        exc_info=True
                    )
        
        logger.info(f"Certificate rotation complete. Rotated {rotated_count} certificates.")
        
    except Exception as e:
        logger.error(f"Certificate rotation job failed: {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler() -> Optional[BackgroundScheduler]:
    """
    Starts the certificate rotation scheduler.
    
    Schedules certificate rotation to run daily.
    
    Returns:
        BackgroundScheduler instance, or None if startup fails
    """
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            rotate_certificates,
            'interval',
            days=1,
            id='certificate_rotation',
            name='Certificate Rotation',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Certificate rotation scheduler started (runs daily)")
        return scheduler
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        return None


def stop_scheduler(sched: Optional[BackgroundScheduler]) -> None:
    """
    Gracefully stops the scheduler, allowing running jobs to complete.
    
    Args:
        sched: Scheduler instance to stop
    """
    if sched is not None:
        logger.info("Shutting down scheduler, waiting for running jobs to complete...")
        sched.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")
