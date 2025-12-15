#!/usr/bin/env python3
"""
Create an admin user for kc-booth.

This script creates an initial admin user that can be used to access
the API and create additional users and API keys.
"""
import sys
import getpass
from sqlalchemy.orm import Session

# Add src to path
sys.path.insert(0, 'src')

from src.database import SessionLocal
from src import auth_models, auth_schemas, auth_crud
from src.config import get_settings

def create_admin_user():
    """Create an admin user interactively."""
    print("=" * 70)
    print("Create Admin User for kc-booth")
    print("=" * 70)
    print()
    
    # Validate configuration
    try:
        settings = get_settings()
        print("✓ Configuration validated")
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        print("\nPlease ensure all required environment variables are set.")
        sys.exit(1)
    
    # Create database tables if they don't exist
    from src.database import engine
    auth_models.Base.metadata.create_all(bind=engine)
    print("✓ Database tables created/verified")
    print()
    
    # Get username
    while True:
        username = input("Enter username (3-50 characters): ").strip()
        if len(username) >= 3 and len(username) <= 50:
            break
        print("❌ Username must be between 3 and 50 characters")
    
    # Get password
    while True:
        password = getpass.getpass("Enter password (min 8 characters): ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters")
            continue
        
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            continue
        
        break
    
    # Create user
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = auth_crud.get_user_by_username(db, username)
        if existing_user:
            print(f"\n❌ User '{username}' already exists")
            sys.exit(1)
        
        # Create the user
        user_create = auth_schemas.UserCreate(username=username, password=password)
        user = auth_crud.create_user(db, user_create)
        
        print(f"\n✓ User '{username}' created successfully (ID: {user.id})")
        
        # Ask if they want to create an initial API key
        create_key = input("\nCreate an initial API key for this user? (y/n): ").strip().lower()
        if create_key == 'y':
            key_name = input("Enter a name for this API key (e.g., 'Initial Setup'): ").strip() or "Initial Setup"
            
            api_key_create = auth_schemas.APIKeyCreate(name=key_name)
            db_api_key, plaintext_key = auth_crud.create_api_key(db, api_key_create, user.id)
            
            print()
            print("=" * 70)
            print("API KEY CREATED")
            print("=" * 70)
            print()
            print(f"Name: {key_name}")
            print(f"Key:  {plaintext_key}")
            print()
            print("⚠️  IMPORTANT: Save this API key now! It will not be shown again.")
            print()
            print("Use this key in the X-API-Key header for API requests:")
            print(f'  curl -H "X-API-Key: {plaintext_key}" http://localhost:8001/health')
            print()
            print("=" * 70)
        
        print("\n✓ Setup complete!")
        
    except Exception as e:
        print(f"\n❌ Error creating user: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
