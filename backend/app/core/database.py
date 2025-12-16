"""
Database configuration and session management.

Provides SQLAlchemy engine, session factory, and dependency injection
for database access throughout the application.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create database engine with configuration from settings
engine = create_engine(
    settings.database_url,
    connect_args=settings.get_database_connect_args()
)

# Session factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session.
    
    Yields a database session and ensures it's properly closed after use.
    Use this in FastAPI route dependencies to get database access.
    
    Example:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
