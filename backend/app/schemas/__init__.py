"""
Unity Schema Definitions

Pydantic models for request/response validation organized by domain.
This __init__.py provides backward compatibility by re-exporting all schemas.
"""

# Core schemas (Server profiles, settings)
from .core import (
    ServerProfileBase,
    ServerProfileCreate,
    ServerProfileUpdate,
    ServerProfile,
    SettingsBase,
    SettingsUpdate,
    Settings,
)

# User schemas
from .users import (
    UserBase,
    UserCreate,
    UserUpdate,
    User,
    Token,
    TokenData,
)

# Alert schemas
from .alerts import *

# Credential schemas
from .credentials import *

# Plugin schemas
from .plugins import *

# Report schemas
from .reports import *

# Notification schemas
from .notifications import *

# Knowledge base schemas
from .knowledge import *

__all__ = [
    # Core
    "ServerProfileBase",
    "ServerProfileCreate",
    "ServerProfileUpdate",
    "ServerProfile",
    "SettingsBase",
    "SettingsUpdate",
    "Settings",
    # Users
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "User",
    "Token",
    "TokenData",
]
