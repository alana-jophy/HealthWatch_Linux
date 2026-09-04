from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    require_admin,
    require_health_worker,
    require_patient,
    require_public_health_officer,
)
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.auth import (
    RoleEnum,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="Creates a new user with hashed password and assigned system role.",
)
def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )

    # Resolve Role
    role = db.query(Role).filter(Role.name == payload.role.value).first()
    if not role:
        # If role does not exist, create it dynamically
        role = Role(name=payload.role.value, description=f"{payload.role.value} role")
        db.add(role)
        db.flush()

    new_user = User(
        email=payload.email.lower(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role_id=role.id,
        is_active=True,
        is_superuser=(payload.role == RoleEnum.ADMIN),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User registered: {new_user.email} with role {role.name}")

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=role.name,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        created_at=new_user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT Access Token",
    description="Validates credentials and returns JWT bearer token along with user profile metadata.",
)
def login_user(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials and issue signed JWT token."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    role_name = user.role.name if user.role else RoleEnum.PATIENT.value

    # Generate JWT Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=str(user.id),
        role=role_name,
        extra_claims={
            "email": user.email,
            "full_name": user.full_name,
        },
        expires_delta=access_token_expires,
    )

    logger.info(f"User logged in successfully: {user.email} (Role: {role_name})")

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description="Requires valid Bearer token. Returns authenticated user information and role.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile data of the currently authenticated user."""
    role_name = current_user.role.name if current_user.role else "UNKNOWN"
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=role_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
    )


# ==============================================================================
# Role-Based Verification & Protection Test Endpoints
# ==============================================================================

@router.get(
    "/protected/admin",
    summary="Admin only endpoint",
    description="Accessible exclusively by users with ADMIN role.",
)
def test_admin_route(current_user: User = Depends(require_admin)):
    return {
        "status": "authorized",
        "message": "Welcome Administrator. Full surveillance configuration granted.",
        "user": current_user.email,
        "role": current_user.role.name if current_user.role else "",
    }


@router.get(
    "/protected/officer",
    summary="Public Health Officer & Admin endpoint",
    description="Accessible by PUBLIC_HEALTH_OFFICER and ADMIN roles.",
)
def test_officer_route(current_user: User = Depends(require_public_health_officer)):
    return {
        "status": "authorized",
        "message": "Access granted: Outbreak decision & epidemiological command authorized.",
        "user": current_user.email,
        "role": current_user.role.name if current_user.role else "",
    }


@router.get(
    "/protected/worker",
    summary="Health Worker, Officer & Admin endpoint",
    description="Accessible by HEALTH_WORKER, PUBLIC_HEALTH_OFFICER, and ADMIN roles.",
)
def test_worker_route(current_user: User = Depends(require_health_worker)):
    return {
        "status": "authorized",
        "message": "Access granted: Field contact tracing and case reporting authorized.",
        "user": current_user.email,
        "role": current_user.role.name if current_user.role else "",
    }


@router.get(
    "/protected/patient",
    summary="Patient only endpoint",
    description="Accessible by PATIENT role.",
)
def test_patient_route(current_user: User = Depends(require_patient)):
    return {
        "status": "authorized",
        "message": "Access granted: Authorized patient location consent telemetry portal.",
        "user": current_user.email,
        "role": current_user.role.name if current_user.role else "",
    }
