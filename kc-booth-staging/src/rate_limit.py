"""Rate limiting configuration for API endpoints."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from .config import get_settings

settings = get_settings()

# Create rate limiter instance with configurable default limit
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_api]
)
