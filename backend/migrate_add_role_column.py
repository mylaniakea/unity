"""
Migration script to add role column to users table and populate based on is_superuser.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://homelab_user:homelab_password@db:5432/homelab_db")
print(f"Connecting to database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

def run_migration():
    print("\n=== Starting Role Column Migration ===\n")

    with engine.connect() as conn:
        # Add role column to users table
        try:
            print("Adding 'role' column to users table...")
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user' NOT NULL
            """))
            print("   ✓ 'role' column added to users table.")
        except Exception as e:
            print(f"   - Error adding role column: {e}")

        # Update existing users: set role='admin' where is_superuser=TRUE
        try:
            print("Updating existing admin users...")
            result = conn.execute(text("""
                UPDATE users
                SET role = 'admin'
                WHERE is_superuser = TRUE
            """))
            print(f"   ✓ Updated {result.rowcount} admin user(s).")
        except Exception as e:
            print(f"   - Error updating admin users: {e}")

        # Update existing users: set role='user' where is_superuser=FALSE
        try:
            print("Updating existing regular users...")
            result = conn.execute(text("""
                UPDATE users
                SET role = 'user'
                WHERE is_superuser = FALSE
            """))
            print(f"   ✓ Updated {result.rowcount} regular user(s).")
        except Exception as e:
            print(f"   - Error updating regular users: {e}")

        conn.commit()

    print("\n=== Migration Complete! ===\n")
    print("Note: is_superuser column is kept for backwards compatibility.")
    print("The 'role' column is now the source of truth for permissions.\n")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
