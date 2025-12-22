"""
Stack models for Docker Compose deployment management.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Stack(Base):
    """
    Represents a Docker Compose stack managed by Unity.
    """
    __tablename__ = "stacks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    compose_content = Column(Text, nullable=False)
    env_vars = Column(JSON, nullable=True)  # Encrypted environment variables
    status = Column(String(50), default="stopped")  # stopped, running, error, deploying
    deployment_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deployed_at = Column(DateTime, nullable=True)
    deployed_by = Column(String(255), nullable=True)
    labels = Column(JSON, nullable=True)  # Custom labels/tags for organization
    
    # Relationships
    deployments = relationship("StackDeployment", back_populates="stack", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stack(name='{self.name}', status='{self.status}')>"


class StackDeployment(Base):
    """
    Tracks deployment history for stacks.
    """
    __tablename__ = "stack_deployments"

    id = Column(Integer, primary_key=True, index=True)
    stack_id = Column(Integer, ForeignKey("stacks.id"), nullable=False)
    action = Column(String(50), nullable=False)  # deploy, stop, restart, destroy
    status = Column(String(50), nullable=False)  # success, failed, in_progress
    error_message = Column(Text, nullable=True)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    stack = relationship("Stack", back_populates="deployments")

    def __repr__(self):
        return f"<StackDeployment(stack_id={self.stack_id}, action='{self.action}', status='{self.status}')>"
