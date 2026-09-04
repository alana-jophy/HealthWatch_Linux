import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import (
    get_current_user,
    require_health_worker,
    require_public_health_officer,
)
from app.db.session import get_db
from app.models.patient import Patient
from app.models.user import User
from app.schemas.auth import RoleEnum
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

router = APIRouter()


@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient record",
    description="Authorized health workers and officers can register new synthetic patient records.",
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_health_worker),
) -> PatientResponse:
    """Create a new patient record."""
    # Check pseudo_id uniqueness
    existing = db.query(Patient).filter(Patient.pseudo_id == payload.pseudo_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A patient with pseudo ID '{payload.pseudo_id}' already exists",
        )

    assigned_worker_id = getattr(payload, "assigned_worker_id", None)
    if not assigned_worker_id and current_user.role and current_user.role.name == RoleEnum.HEALTH_WORKER.value:
        assigned_worker_id = current_user.id

    patient = Patient(
        pseudo_id=payload.pseudo_id,
        user_id=payload.user_id,
        assigned_worker_id=assigned_worker_id,
        full_name=payload.full_name,
        age=payload.age,
        gender=payload.gender.upper(),
        contact_number=payload.contact_number,
        address=payload.address,
        district_name=payload.district_name,
        local_body_name=payload.local_body_name,
        ward_number=payload.ward_number,
        is_active=payload.is_active,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    logger.info(f"Patient registered: {patient.pseudo_id} ({patient.full_name}) by {current_user.email}")
    return patient


@router.get(
    "/",
    response_model=PatientListResponse,
    summary="List, search and filter patient records",
    description="Health workers view all patients with search/filter; Patients only view their own record.",
)
def list_patients(
    q: Optional[str] = Query(None, description="Search term for pseudo_id, name, or address"),
    district_name: Optional[str] = Query(None, description="Filter by district name"),
    ward_number: Optional[int] = Query(None, description="Filter by ward number"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientListResponse:
    """Retrieve patient records with role-based access filtering."""
    query = db.query(Patient)

    user_role = current_user.role.name if current_user.role else ""

    # Patient role restriction: only own record
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        query = query.filter(Patient.user_id == current_user.id)
    elif user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        # Health Worker restriction: only assigned patients
        query = query.filter(Patient.assigned_worker_id == current_user.id)
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                (Patient.pseudo_id.ilike(search_pattern)) |
                (Patient.full_name.ilike(search_pattern)) |
                (Patient.address.ilike(search_pattern))
            )
        if district_name:
            query = query.filter(Patient.district_name.ilike(f"%{district_name}%"))
        if ward_number is not None:
            query = query.filter(Patient.ward_number == ward_number)
        if is_active is not None:
            query = query.filter(Patient.is_active == is_active)
    else:
        # Field search & filter for health workers/officers/admins
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                (Patient.pseudo_id.ilike(search_pattern)) |
                (Patient.full_name.ilike(search_pattern)) |
                (Patient.address.ilike(search_pattern))
            )
        if district_name:
            query = query.filter(Patient.district_name.ilike(f"%{district_name}%"))
        if ward_number is not None:
            query = query.filter(Patient.ward_number == ward_number)
        if is_active is not None:
            query = query.filter(Patient.is_active == is_active)

    total = query.count()
    items = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()

    return PatientListResponse(total=total, items=items)


@router.get(
    "/me",
    response_model=PatientResponse,
    summary="Get authenticated patient profile",
    description="Returns profile and health record for the currently logged-in patient.",
)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientResponse:
    """Get current authenticated patient's own profile."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        # Fallback for administrative users without linked patient
        if current_user.is_superuser or (current_user.role and current_user.role.name != RoleEnum.PATIENT.value):
            patient = db.query(Patient).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patient profile found linked to this user account",
            )
    return patient


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient details by ID",
    description="Returns detailed patient health record. Patients can only access their own record.",
)
def get_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientResponse:
    """Get single patient record."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found",
        )

    user_role = current_user.role.name if current_user.role else ""
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own patient record",
            )
    elif user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        if patient.assigned_worker_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patient is not assigned to this health worker",
            )

    return patient


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient record",
    description="Authorized health workers can update patient demographic and geographic information.",
)
def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_health_worker),
) -> PatientResponse:
    """Update patient details."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found",
        )

    user_role = current_user.role.name if current_user.role else ""
    if user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        if patient.assigned_worker_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patient is not assigned to this health worker",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    logger.info(f"Patient {patient.pseudo_id} updated by {current_user.email}")
    return patient


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate or remove patient record",
    description="Public health officers and admins can deactivate patient records.",
)
def delete_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_public_health_officer),
):
    """Deactivate patient record."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found",
        )

    patient.is_active = False
    db.commit()
    logger.info(f"Patient {patient.pseudo_id} deactivated by {current_user.email}")
    return {"status": "success", "message": f"Patient {patient.pseudo_id} deactivated"}
