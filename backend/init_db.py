#!/usr/bin/env python3
"""
Database initialization script for Unity
Creates admin user and ensures database is ready
"""
import os
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User
from app.services.auth import AuthService

def init_database():
    """Initialize database with admin user and default settings"""

    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"Connecting to database...")

    # Create engine and session
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables (if they don't exist)
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.email == "admin@unity.local").first()

        if admin_user:
            print("✓ Admin user already exists")
        else:
            # Create admin user
            print("Creating admin user...")
            hashed_password = AuthService.get_password_hash("admin123")

            admin_user = User(
                username="admin",
                email="admin@unity.local",
                hashed_password=hashed_password,
                role="admin",
                is_active=True,
                is_superuser=True
            )

            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            print(f"✓ Created admin user (ID: {admin_user.id})")
            print(f"  Email: admin@unity.local")
            print(f"  Password: admin123")
            print(f"  Role: admin")

        print("\n✓ Database initialization complete!")
        print("\nYou can now log in with:")
        print("  Email: admin@unity.local")
        print("  Password: admin123")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
