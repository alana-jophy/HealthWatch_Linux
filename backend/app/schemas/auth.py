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
    """Schema for user credentials login (accepts email or account ID)."""
    email: str = Field(..., description="User email address or patient Account ID")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Schema representing user profile output."""
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    patient_pseudo_id: Optional[str] = None
    patient_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema returned upon successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
