#!/usr/bin/env python3
"""Run Alembic migrations programmatically."""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from alembic.config import Config
from alembic import command

def run_migrations():
    """Run database migrations to head."""
    print("Running database migrations...")
    
    alembic_cfg = Config("alembic.ini")
    
    try:
        # Show current revision
        print("\nCurrent revision:")
        command.current(alembic_cfg)
        
        # Upgrade to head
        print("\nUpgrading to head...")
        command.upgrade(alembic_cfg, "head")
        
        # Show new current revision
        print("\nNew revision:")
        command.current(alembic_cfg)
        
        print("\n✅ Migrations completed successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_migrations())
