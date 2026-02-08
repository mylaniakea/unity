"""
Shim module to keep existing imports (`from app import database`) working.
Re-exports engine/session/Base helpers from app.core.database.
"""

from app.core.database import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
