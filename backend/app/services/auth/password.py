"""Password hashing and verification using bcrypt."""
from passlib.context import CryptContext
from app.core.config import settings

# Create password context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a hashed password needs to be rehashed.
    
    Useful when changing bcrypt rounds or upgrading security.
    
    Args:
        hashed_password: Hashed password to check
        
    Returns:
        True if password should be rehashed, False otherwise
    """
    return pwd_context.needs_update(hashed_password)
