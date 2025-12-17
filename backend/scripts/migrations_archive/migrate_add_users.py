"""
Migration script to add Users table and default admin user.
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from passlib.context import CryptContext

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/homelab.db")
print(f"Connecting to database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def table_exists(table_name):
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def get_password_hash(password):
    return pwd_context.hash(password)

def run_migration():
    print("\n=== Starting User Table Migration ===\n")
    
    with engine.connect() as conn:
        if not table_exists('users'):
            print("Creating 'users' table...")
            # Create table
            conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR UNIQUE NOT NULL,
                    email VARCHAR UNIQUE,
                    hashed_password VARCHAR NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_superuser BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            conn.execute(text("CREATE INDEX ix_users_username ON users(username)"))
            conn.execute(text("CREATE INDEX ix_users_email ON users(email)"))
            print("   ✓ 'users' table created.")
        else:
            print("   - 'users' table already exists.")
            
        # Check if default user needs to be added
        result = conn.execute(text("SELECT count(*) FROM users"))
        user_count = result.scalar()
        
        if user_count == 0:
            print("\nCreating default admin user...")
            admin_user = "admin"
            admin_pass = "admin" # Change this immediately!
            hashed = get_password_hash(admin_pass)
            
            conn.execute(text("""
                INSERT INTO users (username, hashed_password, is_superuser)
                VALUES (:username, :password, :superuser)
            """), {"username": admin_user, "password": hashed, "superuser": True})
            print(f"   ✓ Default user created: {admin_user} / {admin_pass}")
            print("   ⚠️  IMPORTANT: Login and change your password immediately!")
        else:
            print(f"   - {user_count} users found. Skipping default user creation.")
            
        conn.commit()

    print("\n=== Migration Complete! ===\n")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
