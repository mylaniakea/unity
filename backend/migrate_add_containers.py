"""
Migration script to add container management tables (Phase 4).

Usage:
    python migrate_add_containers.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.containers import (
    ContainerHost, Container, UpdateCheck, UpdateHistory,
    UpdatePolicy, MaintenanceWindow, VulnerabilityScan,
    ContainerVulnerability, UpdateNotification, ContainerBackup,
    AIRecommendation, RegistryCredential
)

def run_migration():
    """Create all container-related tables."""
    print("Starting Phase 4 container tables migration...")
    
    db = SessionLocal()
    try:
        # Import Base to create all tables
        from app.core.database import Base
        
        # Create all container tables
        print("Creating container tables...")
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
        print("✓ Container tables created successfully!")
        print("\nCreated tables:")
        print("  - container_hosts")
        print("  - containers")
        print("  - update_checks")
        print("  - update_history")
        print("  - update_policies")
        print("  - maintenance_windows")
        print("  - vulnerability_scans")
        print("  - container_vulnerabilities")
        print("  - update_notifications")
        print("  - container_backups")
        print("  - ai_recommendations")
        print("  - registry_credentials")
        
        db.commit()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
