from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Import relationship for ORM
from app.database import Base



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # admin, user, viewer
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # Kept for backwards compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# ==================
# PLUGIN SYSTEM MODELS
# ==================


