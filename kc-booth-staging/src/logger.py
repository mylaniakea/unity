"""Centralized logging configuration with correlation IDs and structured logging."""
import logging
import sys
import uuid
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger
from typing import Optional

# Context variable for request correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get() or "none"
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['app'] = 'kc-booth'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['correlation_id'] = getattr(record, 'correlation_id', 'none')


def setup_logging(json_logs: bool = False) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        json_logs: If True, use JSON formatted logs (recommended for production)
                   If False, use human-readable format (better for development)
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger("kc-booth")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())
    
    if json_logs:
        # JSON format for production (easier to parse by log aggregators)
        formatter = CustomJsonFormatter(
            '%(asctime)s %(level)s %(logger)s %(correlation_id)s %(message)s'
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    corr_id = correlation_id.get()
    if corr_id is None:
        corr_id = str(uuid.uuid4())
        correlation_id.set(corr_id)
    return corr_id


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id.set(corr_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id.set(None)


# Initialize logger (can be imported by other modules)
logger = setup_logging()
