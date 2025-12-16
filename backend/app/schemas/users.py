"""
User and authentication schema definitions.

User models and JWT token schemas.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: Optional[str] = "user"  # admin, user, viewer


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class AdminResetPassword(BaseModel):
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
