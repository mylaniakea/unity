"""
DEPRECATED: This module has been moved to app.core.database

This file is kept for backward compatibility.
Please update your imports to:
    from app.core.database import engine, SessionLocal, Base, get_db
"""
import warnings

# Issue deprecation warning when this module is imported
warnings.warn(
    "app.database is deprecated. Use app.core.database instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from app.core.database import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
