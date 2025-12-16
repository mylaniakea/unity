"""
Core application configuration and infrastructure.

This package contains:
- config: Centralized configuration management
- database: Database engine and session management
"""
from app.core.config import settings
from app.core.database import engine, SessionLocal, Base, get_db

__all__ = [
    "settings",
    "engine",
    "SessionLocal", 
    "Base",
    "get_db",
]
