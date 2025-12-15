"""
Migration script to add missing columns to existing tables.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://homelab_user:homelab_password@db:5432/homelab_db")
print(f"Connecting to database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

def run_migration():
    print("\n=== Starting Missing Columns Migration ===\n")

    with engine.connect() as conn:
        # Add snoozed_until to alerts table
        try:
            print("Adding 'snoozed_until' column to alerts table...")
            conn.execute(text("""
                ALTER TABLE alerts
                ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMP WITH TIME ZONE
            """))
            print("   ✓ 'snoozed_until' column added to alerts.")
        except Exception as e:
            print(f"   - Error adding snoozed_until: {e}")

        # Add alert_sound_enabled to settings table
        try:
            print("Adding 'alert_sound_enabled' column to settings table...")
            conn.execute(text("""
                ALTER TABLE settings
                ADD COLUMN IF NOT EXISTS alert_sound_enabled BOOLEAN DEFAULT FALSE
            """))
            print("   ✓ 'alert_sound_enabled' column added to settings.")
        except Exception as e:
            print(f"   - Error adding alert_sound_enabled: {e}")

        # Add maintenance_mode_until to settings table
        try:
            print("Adding 'maintenance_mode_until' column to settings table...")
            conn.execute(text("""
                ALTER TABLE settings
                ADD COLUMN IF NOT EXISTS maintenance_mode_until TIMESTAMP WITH TIME ZONE
            """))
            print("   ✓ 'maintenance_mode_until' column added to settings.")
        except Exception as e:
            print(f"   - Error adding maintenance_mode_until: {e}")

        # Add muted_until to threshold_rules table
        try:
            print("Adding 'muted_until' column to threshold_rules table...")
            conn.execute(text("""
                ALTER TABLE threshold_rules
                ADD COLUMN IF NOT EXISTS muted_until TIMESTAMP WITH TIME ZONE
            """))
            print("   ✓ 'muted_until' column added to threshold_rules.")
        except Exception as e:
            print(f"   - Error adding muted_until: {e}")

        # Add template to alert_channels table
        try:
            print("Adding 'template' column to alert_channels table...")
            conn.execute(text("""
                ALTER TABLE alert_channels
                ADD COLUMN IF NOT EXISTS template TEXT
            """))
            print("   ✓ 'template' column added to alert_channels.")
        except Exception as e:
            print(f"   - Error adding template: {e}")

        conn.commit()

    print("\n=== Migration Complete! ===\n")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
