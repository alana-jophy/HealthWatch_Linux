from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RoleEnum

# Security scheme using Bearer token
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer JWT token and return the authenticated User instance."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing subject identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user no longer exists",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def require_roles(allowed_roles: List[RoleEnum]) -> Callable[[User], User]:
    """Factory dependency to enforce Role-Based Access Control (RBAC)."""
    allowed_role_names = [r.value if isinstance(r, RoleEnum) else str(r) for r in allowed_roles]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_name = current_user.role.name if current_user.role else ""
        
        # Superusers bypass role checks
        if current_user.is_superuser:
            return current_user

        if user_role_name not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Required role in {allowed_role_names}, but user possesses role '{user_role_name}'",
            )
        return current_user

    return role_checker


# Role convenience dependencies
require_admin = require_roles([RoleEnum.ADMIN])
require_admin_or_officer = require_roles([RoleEnum.ADMIN, RoleEnum.PUBLIC_HEALTH_OFFICER])
require_public_health_officer = require_roles([RoleEnum.ADMIN, RoleEnum.PUBLIC_HEALTH_OFFICER])
require_health_worker = require_roles([RoleEnum.ADMIN, RoleEnum.PUBLIC_HEALTH_OFFICER, RoleEnum.HEALTH_WORKER])
require_patient = require_roles([RoleEnum.PATIENT, RoleEnum.ADMIN])


def verify_patient_access(current_user: User, patient) -> None:
    """
    Enforce granular RBAC ownership and assignment across all 4 roles:
    - Superuser / ADMIN: Full authorized access.
    - PUBLIC_HEALTH_OFFICER: Full epidemiological surveillance authority.
    - HEALTH_WORKER: Authorized ONLY for assigned patients.
    - PATIENT: Authorized ONLY for own user profile.
    """
    if current_user.is_superuser:
        return

    user_role = current_user.role.name if current_user.role else ""

    if user_role == RoleEnum.ADMIN.value:
        return

    if user_role == RoleEnum.PUBLIC_HEALTH_OFFICER.value:
        return

    if user_role == RoleEnum.HEALTH_WORKER.value:
        if patient.assigned_worker_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patient is not assigned to this health worker",
            )
        return

    if user_role == RoleEnum.PATIENT.value:
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own patient records",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: Role '{user_role}' is not authorized to access patient records",
    )

