"""Infrastructure data collection task for Phase 3: BD-Store Integration."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Tuple
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.services.infrastructure.ssh_service import ssh_service, SSHConnectionError
from app.services.infrastructure import storage_discovery, pool_discovery, database_discovery

logger = logging.getLogger(__name__)


def collect_server_data(server_id: int) -> Tuple[bool, str]:
    """
    Collect infrastructure data for a monitored server.
    
    Args:
        server_id: ID of the MonitoredServer
        
    Returns:
        Tuple of (success, message)
    """
    db = next(get_db())
    
    try:
        # Load server
        server = db.query(models.MonitoredServer).filter(
            models.MonitoredServer.id == server_id
        ).first()
        
        if not server:
            return False, f"Server {server_id} not found"
        
        if not server.monitoring_enabled:
            return False, f"Monitoring disabled for {server.hostname}"
        
        logger.info(f"Collecting data for server: {server.hostname}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Discover storage devices
            device_count = 0
            pool_count = 0
            db_count = 0
            errors = []
            
            try:
                devices, device_errors = loop.run_until_complete(
                    storage_discovery.StorageDiscoveryService(db).discover_all_devices(server, db)
                )
                device_count = len(devices)
                if device_errors:
                    errors.extend(device_errors)
            except Exception as e:
                logger.error(f"Storage discovery failed: {e}")
                errors.append(f"Storage discovery error: {str(e)}")
            
            try:
                pools, pool_errors = loop.run_until_complete(
                    pool_discovery.PoolDiscoveryService(db).discover_all_pools(server, db)
                )
                pool_count = len(pools)
                if pool_errors:
                    errors.extend(pool_errors)
            except Exception as e:
                logger.error(f"Pool discovery failed: {e}")
                errors.append(f"Pool discovery error: {str(e)}")
            
            try:
                db_result = loop.run_until_complete(
                    database_discovery.DatabaseDiscoveryService(db).discover_databases(
                        server_id,
                        db_types=[
                            models.DatabaseType.POSTGRESQL,
                            models.DatabaseType.MYSQL
                        ],
                        test_connection=True
                    )
                )
                db_count = len(db_result.get("databases", []))
                if db_result.get("errors"):
                    errors.extend(db_result["errors"])
            except Exception as e:
                logger.error(f"Database discovery failed: {e}")
                errors.append(f"Database discovery error: {str(e)}")
            
            # Update server status
            server.status = models.ServerStatus.ONLINE
            server.last_seen = datetime.now(timezone.utc)
            if errors:
                server.last_error = "; ".join(errors[:3])  # Keep last 3 errors
            else:
                server.last_error = None
            
            db.commit()
            
            # Build result message
            message = f"Collected: {device_count} devices, {pool_count} pools, {db_count} databases"
            if errors:
                message += f" ({len(errors)} errors)"
            
            logger.info(f"Collection completed for {server.hostname}: {message}")
            return True, message
            
        finally:
            loop.close()
            
    except SSHConnectionError as e:
        logger.error(f"SSH connection failed for server {server_id}: {e}")
        server = db.query(models.MonitoredServer).filter(
            models.MonitoredServer.id == server_id
        ).first()
        if server:
            server.status = models.ServerStatus.OFFLINE
            server.last_error = f"SSH connection failed: {str(e)}"
            db.commit()
        return False, f"SSH connection failed: {str(e)}"
    
    except Exception as e:
        logger.exception(f"Unexpected error collecting data for server {server_id}")
        return False, f"Collection failed: {str(e)}"
    
    finally:
        db.close()


def collect_all_servers() -> dict:
    """
    Collect data for all monitored servers with monitoring enabled.
    
    Returns:
        Dictionary with collection results
    """
    db = next(get_db())
    
    try:
        servers = db.query(models.MonitoredServer).filter(
            models.MonitoredServer.monitoring_enabled == True
        ).all()
        
        results = {
            "total": len(servers),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for server in servers:
            success, message = collect_server_data(server.id)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{server.hostname}: {message}")
        
        logger.info(
            f"Bulk collection completed: {results['successful']}/{results['total']} successful"
        )
        
        return results
        
    finally:
        db.close()
