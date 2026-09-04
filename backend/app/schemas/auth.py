import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleEnum(str, Enum):
    """System-wide Role Definitions for Role-Based Access Control (RBAC)."""
    ADMIN = "ADMIN"
    HEALTH_WORKER = "HEALTH_WORKER"
    PUBLIC_HEALTH_OFFICER = "PUBLIC_HEALTH_OFFICER"
    PATIENT = "PATIENT"


class UserRegisterRequest(BaseModel):
    """Schema for registering a new user."""
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full Name")
    role: RoleEnum = Field(default=RoleEnum.HEALTH_WORKER, description="Assigned role")


class UserLoginRequest(BaseModel):
    """Schema for user credentials login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Schema representing user profile output."""
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema returned upon successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
