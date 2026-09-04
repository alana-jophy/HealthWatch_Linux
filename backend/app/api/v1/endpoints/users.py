"""System User Management Endpoints."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_officer
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    summary="List all system users",
    description="Authorized for Administrators and Public Health Officers.",
)
def list_system_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
):
    """Retrieve all system users with role assignment."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role_name": u.role.name if u.role else "PATIENT",
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
