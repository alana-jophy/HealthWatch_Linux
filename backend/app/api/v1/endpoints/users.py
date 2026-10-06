"""System User Management Endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_admin_or_officer
from app.core.security import get_password_hash
from app.models.user import User, Role
from app.schemas.auth import RoleEnum

router = APIRouter()


class CreateUserRequest(BaseModel):
    """Schema for creating a new system user account."""
    email: EmailStr = Field(..., description="Unique email address")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full Legal Name")
    role: RoleEnum = Field(default=RoleEnum.HEALTH_WORKER, description="Assigned platform role")
    password: str = Field(..., min_length=6, description="Temporary password (must be reset on first login)")


class AdminResetPasswordRequest(BaseModel):
    """Schema for administrative temporary password reset."""
    temporary_password: str = Field(..., min_length=6, description="New temporary password")


@router.get(
    "/",
    summary="List all system users",
    description="Authorized for Administrators and Public Health Officers.",
)
def list_system_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
):
    """Retrieve all system users with role assignment and must_change_password status."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role_name": u.role.name if u.role else "PATIENT",
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "must_change_password": bool(getattr(u, "must_change_password", False)),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new system user",
    description="Authorized exclusively for Administrators. New users are assigned must_change_password=True by default.",
)
def create_system_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new system user account with mandatory first-login password change."""
    # 1. Check email uniqueness
    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{payload.email}' already exists.",
        )

    # 2. Resolve Role
    role = db.query(Role).filter(Role.name == payload.role.value).first()
    if not role:
        role = Role(name=payload.role.value, description=f"{payload.role.value} platform role")
        db.add(role)
        db.flush()

    # 3. Create user with must_change_password = True
    new_user = User(
        email=payload.email.lower().strip(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        role_id=role.id,
        is_active=True,
        is_superuser=(payload.role == RoleEnum.ADMIN),
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role_name": role.name,
        "is_active": new_user.is_active,
        "is_superuser": new_user.is_superuser,
        "must_change_password": True,
        "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
        "message": f"User {new_user.email} created successfully. They will be required to change their password on first login.",
    }


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Admin reset of user password",
    description="Assigns a new temporary password and sets must_change_password=True.",
)
def admin_reset_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Reset user password to a temporary password and require password change on next login."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    target_user.hashed_password = get_password_hash(payload.temporary_password)
    target_user.must_change_password = True
    db.commit()

    return {
        "status": "success",
        "message": f"Temporary password assigned to {target_user.email}. User must change it upon their next login.",
        "must_change_password": True,
    }
