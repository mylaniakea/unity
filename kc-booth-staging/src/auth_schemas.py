"""Authentication Pydantic schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8)


class User(UserBase):
    """User response schema - password excluded."""
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class APIKeyBase(BaseModel):
    """Base API key schema."""
    name: str = Field(..., description="Description or name for this API key")


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key."""
    pass


class APIKey(APIKeyBase):
    """API key response schema - actual key hash excluded."""
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class APIKeyWithKey(APIKey):
    """API key response with the actual key (only shown once at creation)."""
    key: str = Field(..., description="The actual API key - save this, it won't be shown again")


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str
