"""Error tracking models for debugging and observability."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class CollectionError(Base):
    """Track infrastructure collection errors for debugging."""
    
    __tablename__ = "collection_errors"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("monitored_servers.id", ondelete="CASCADE"), nullable=True, index=True)
    error_type = Column(String(100), nullable=False, index=True)  # "ssh", "discovery", "metrics", "alert"
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    service_name = Column(String(100), nullable=True)  # Which service failed
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<CollectionError(id={self.id}, type='{self.error_type}', server={self.server_id})>"
