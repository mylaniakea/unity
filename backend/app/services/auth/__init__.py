"""Authentication and authorization services."""
# Only export functions, not modules, to avoid circular imports
from app.services.auth.password import hash_password, verify_password, needs_rehash
from app.services.auth.jwt_handler import (
    create_access_token,
    decode_token,
    get_token_subject,
    verify_token
)
from app.services.auth.session_manager import SessionManager

__all__ = [
    # Password functions
    "hash_password",
    "verify_password",
    "needs_rehash",
    # JWT functions
    "create_access_token",
    "decode_token",
    "get_token_subject",
    "verify_token",
    # Session manager
    "SessionManager",
]
