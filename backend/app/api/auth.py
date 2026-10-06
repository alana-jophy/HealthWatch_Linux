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
    ChangePasswordRequest,
    ChangePasswordResponse,
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
        must_change_password=True,
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
        must_change_password=bool(new_user.must_change_password),
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
    """Authenticate user credentials (via Email or Patient Account ID) and issue signed JWT token."""
    from app.models.patient import Patient

    identifier = payload.email.strip()
    user = db.query(User).filter(User.email == identifier.lower()).first()

    linked_patient = None
    if not user:
        # Check if identifier matches a Patient Account ID (pseudo_id)
        linked_patient = db.query(Patient).filter(Patient.pseudo_id.ilike(identifier)).first()
        if linked_patient and linked_patient.user_id:
            user = db.query(User).filter(User.id == linked_patient.user_id).first()

    if not user:
        # Check if identifier matches Patient contact_number (phone)
        clean_phone = identifier.replace(" ", "").replace("-", "").replace("+91", "")
        matching_patients = db.query(Patient).filter(
            (Patient.contact_number == identifier) | (Patient.contact_number == clean_phone)
        ).all()
        for mp in matching_patients:
            if mp.user_id:
                candidate = db.query(User).filter(User.id == mp.user_id).first()
                if candidate and verify_password(payload.password, candidate.hashed_password):
                    user = candidate
                    linked_patient = mp
                    break
        if not user and matching_patients and matching_patients[0].user_id:
            linked_patient = matching_patients[0]
            user = db.query(User).filter(User.id == linked_patient.user_id).first()
    else:
        linked_patient = db.query(Patient).filter(Patient.user_id == user.id).first()

    if not linked_patient and user:
        linked_patient = db.query(Patient).filter(Patient.user_id == user.id).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive. Please contact the administrator.",
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
            "patient_pseudo_id": linked_patient.pseudo_id if linked_patient else None,
            "patient_id": str(linked_patient.id) if linked_patient else None,
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
        must_change_password=bool(getattr(user, "must_change_password", False)),
        patient_pseudo_id=linked_patient.pseudo_id if linked_patient else None,
        patient_id=linked_patient.id if linked_patient else None,
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
    db: Session = Depends(get_db),
) -> UserResponse:
    """Return profile data of the currently authenticated user."""
    from app.models.patient import Patient

    role_name = current_user.role.name if current_user.role else "UNKNOWN"
    linked_patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=role_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        must_change_password=bool(getattr(current_user, "must_change_password", False)),
        patient_pseudo_id=linked_patient.pseudo_id if linked_patient else None,
        patient_id=linked_patient.id if linked_patient else None,
    )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change or reset user password",
    description="Allows authenticated user to change their password (required after first login).",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    """Authenticate current password and update to new password. Resets must_change_password flag to False."""
    from app.models.patient import Patient

    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current temporary/registration password is incorrect.",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as your current temporary password.",
        )

    if len(payload.new_password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters.",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)

    logger.info(f"Password changed successfully for user: {current_user.email}")

    role_name = current_user.role.name if current_user.role else "UNKNOWN"
    linked_patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()

    user_resp = UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=role_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        must_change_password=False,
        patient_pseudo_id=linked_patient.pseudo_id if linked_patient else None,
        patient_id=linked_patient.id if linked_patient else None,
    )

    return ChangePasswordResponse(
        message="Password updated successfully. You can now use your new password for all future logins.",
        user=user_resp,
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
