"""
Pydantic schemas for Stack API requests and responses.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


# Stack Schemas
class StackBase(BaseModel):
    """Base schema for Stack"""
    name: str = Field(..., min_length=1, max_length=255, description="Unique stack name")
    description: Optional[str] = Field(None, description="Stack description")
    compose_content: str = Field(..., min_length=1, description="Docker Compose YAML content")
    env_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    labels: Optional[Dict[str, str]] = Field(None, description="Custom labels for organization")

    @validator('name')
    def validate_name(cls, v):
        """Validate stack name (alphanumeric, hyphens, underscores only)"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Stack name must contain only alphanumeric characters, hyphens, and underscores')
        return v


class StackCreate(StackBase):
    """Schema for creating a new stack"""
    pass


class StackUpdate(BaseModel):
    """Schema for updating an existing stack"""
    description: Optional[str] = None
    compose_content: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None


class StackResponse(StackBase):
    """Schema for stack response"""
    id: int
    status: str
    deployment_path: str
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime]
    deployed_by: Optional[str]

    class Config:
        from_attributes = True


class StackListResponse(BaseModel):
    """Schema for listing stacks"""
    id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    deployed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Validation Schemas
class ValidationError(BaseModel):
    """Individual validation error"""
    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    fix: str = Field(..., description="Suggested fix")
    line: Optional[int] = Field(None, description="Line number in compose file")
    service: Optional[str] = Field(None, description="Service name")


class ValidationWarning(BaseModel):
    """Individual validation warning"""
    type: str
    message: str
    fix: str
    line: Optional[int] = None
    service: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of compose file validation"""
    valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationWarning] = []
    required_env_vars: List[str] = []
    env_files_needed: List[str] = []


# Environment Schema
class EnvVarSchema(BaseModel):
    """Schema for environment variable definition"""
    name: str
    required: bool = True
    type: str = "string"  # string, password, number, boolean
    description: Optional[str] = None
    default: Optional[str] = None


class EnvSchemaResponse(BaseModel):
    """Schema for environment variable form generation"""
    env_vars: List[EnvVarSchema]


# Deployment Schemas
class DeploymentRequest(BaseModel):
    """Request to deploy a stack"""
    env_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables for this deployment")


class DeploymentResponse(BaseModel):
    """Response from deployment action"""
    success: bool
    message: str
    error: Optional[str] = None


# Stack Status Schema
class ContainerStatus(BaseModel):
    """Container status within a stack"""
    container_id: str
    name: str
    status: str
    image: str
    created: datetime


class StackStatusResponse(BaseModel):
    """Detailed stack status"""
    stack_name: str
    status: str
    containers: List[ContainerStatus]
    deployed_at: Optional[datetime]
    last_error: Optional[str] = None


# Deployment History Schema
class StackDeploymentResponse(BaseModel):
    """Stack deployment history entry"""
    id: int
    action: str
    status: str
    error_message: Optional[str]
    deployed_at: datetime
    
    class Config:
        from_attributes = True
