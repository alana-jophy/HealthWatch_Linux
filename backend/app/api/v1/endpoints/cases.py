import datetime
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
from app.models.disease import CaseStatus, Disease, DiseaseCase
from app.models.patient import Patient
from app.models.user import User
from app.schemas.auth import RoleEnum
from app.schemas.case import (
    CaseStatusEnum,
    DiseaseCaseCreate,
    DiseaseCaseListResponse,
    DiseaseCaseResponse,
    DiseaseCaseUpdate,
    SeverityEnum,
)

router = APIRouter()


@router.post(
    "/",
    response_model=DiseaseCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new disease case incident",
    description="Authorized Health Workers and Public Health Officers log suspected or confirmed disease incidents.",
)
def create_case(
    payload: DiseaseCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_health_worker),
) -> DiseaseCaseResponse:
    """Create a new disease surveillance case record."""
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced patient ID does not exist",
        )

    # Verify disease exists
    disease = db.query(Disease).filter(Disease.id == payload.disease_id).first()
    if not disease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced disease ID does not exist in the catalog",
        )

    case = DiseaseCase(
        patient_id=payload.patient_id,
        disease_id=payload.disease_id,
        reported_by_id=current_user.id,
        case_status=payload.case_status.value,
        severity=payload.severity.value,
        diagnosis_date=payload.diagnosis_date,
        recovery_date=payload.recovery_date,
        clinical_notes=payload.clinical_notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    logger.info(f"Disease Case logged: Patient={patient.pseudo_id}, Disease={disease.code}, Status={case.case_status} by {current_user.email}")
    return case


@router.get(
    "/",
    response_model=DiseaseCaseListResponse,
    summary="List, search and filter disease cases",
    description="Supports filtering by case status (SUSPECTED, CONFIRMED, RECOVERED, DECEASED), severity, disease, and dates.",
)
def list_cases(
    case_status: Optional[CaseStatusEnum] = Query(None, description="Filter by status (SUSPECTED, CONFIRMED, RECOVERED, DECEASED)"),
    severity: Optional[SeverityEnum] = Query(None, description="Filter by clinical severity (MILD, MODERATE, SEVERE, CRITICAL)"),
    disease_id: Optional[uuid.UUID] = Query(None, description="Filter by disease ID"),
    patient_id: Optional[uuid.UUID] = Query(None, description="Filter by patient ID"),
    start_date: Optional[datetime.date] = Query(None, description="Filter diagnosis date on or after"),
    end_date: Optional[datetime.date] = Query(None, description="Filter diagnosis date on or before"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiseaseCaseListResponse:
    """Retrieve disease case incidents with RBAC restrictions."""
    query = db.query(DiseaseCase).join(DiseaseCase.patient)

    user_role = current_user.role.name if current_user.role else ""

    # Patient role restriction: only cases belonging to current patient user
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patient profile found linked to this user account",
            )
        if patient_id and patient.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view another patient's disease case records",
            )
        query = query.filter(Patient.user_id == current_user.id)
    elif user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        # Health Worker restriction: only assigned patients
        query = query.filter(Patient.assigned_worker_id == current_user.id)
        if patient_id:
            assigned_patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not assigned_patient or assigned_patient.assigned_worker_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Patient is not assigned to this health worker",
                )
            query = query.filter(DiseaseCase.patient_id == patient_id)
        if case_status:
            query = query.filter(DiseaseCase.case_status == case_status.value)
        if severity:
            query = query.filter(DiseaseCase.severity == severity.value)
        if disease_id:
            query = query.filter(DiseaseCase.disease_id == disease_id)
        if start_date:
            query = query.filter(DiseaseCase.diagnosis_date >= start_date)
        if end_date:
            query = query.filter(DiseaseCase.diagnosis_date <= end_date)
    else:
        if case_status:
            query = query.filter(DiseaseCase.case_status == case_status.value)
        if severity:
            query = query.filter(DiseaseCase.severity == severity.value)
        if disease_id:
            query = query.filter(DiseaseCase.disease_id == disease_id)
        if patient_id:
            query = query.filter(DiseaseCase.patient_id == patient_id)
        if start_date:
            query = query.filter(DiseaseCase.diagnosis_date >= start_date)
        if end_date:
            query = query.filter(DiseaseCase.diagnosis_date <= end_date)

    total = query.count()
    items = query.order_by(DiseaseCase.diagnosis_date.desc(), DiseaseCase.created_at.desc()).offset(skip).limit(limit).all()

    return DiseaseCaseListResponse(total=total, items=items)


@router.get(
    "/me",
    response_model=DiseaseCaseListResponse,
    summary="Get authenticated patient disease cases",
    description="Returns list of disease case incidents linked to the current logged-in patient.",
)
def get_my_disease_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiseaseCaseListResponse:
    """Get all disease cases for the authenticated patient."""
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        # Administrative fallback
        if current_user.is_superuser or (current_user.role and current_user.role.name != RoleEnum.PATIENT.value):
            patient = db.query(Patient).first()
        if not patient:
            return DiseaseCaseListResponse(total=0, items=[])

    query = db.query(DiseaseCase).filter(DiseaseCase.patient_id == patient.id)
    total = query.count()
    items = query.order_by(DiseaseCase.diagnosis_date.desc()).all()
    return DiseaseCaseListResponse(total=total, items=items)


@router.get(
    "/{case_id}",
    response_model=DiseaseCaseResponse,
    summary="Get case details by ID",
)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiseaseCaseResponse:
    """Get single disease case record."""
    case = db.query(DiseaseCase).filter(DiseaseCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disease case record not found",
        )

    user_role = current_user.role.name if current_user.role else ""
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        if not case.patient or case.patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own disease case records",
            )
    elif user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        if not case.patient or case.patient.assigned_worker_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Case belongs to a patient not assigned to this health worker",
            )

    return case


@router.put(
    "/{case_id}",
    response_model=DiseaseCaseResponse,
    summary="Update case status and clinical trajectory",
    description="Health Workers and Officers can transition cases (e.g. SUSPECTED -> CONFIRMED -> RECOVERED).",
)
def update_case(
    case_id: uuid.UUID,
    payload: DiseaseCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_health_worker),
) -> DiseaseCaseResponse:
    """Update disease case status and observations."""
    case = db.query(DiseaseCase).filter(DiseaseCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disease case record not found",
        )

    user_role = current_user.role.name if current_user.role else ""
    if user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        if not case.patient or case.patient.assigned_worker_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Case belongs to a patient not assigned to this health worker",
            )

    update_data = payload.model_dump(exclude_unset=True)
    if "case_status" in update_data and update_data["case_status"] is not None:
        update_data["case_status"] = update_data["case_status"].value
    if "severity" in update_data and update_data["severity"] is not None:
        update_data["severity"] = update_data["severity"].value

    for field, value in update_data.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)
    logger.info(f"Disease Case {case.id} updated by {current_user.email} (Status: {case.case_status})")
    return case


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete case record",
    description="Requires Public Health Officer or Admin role.",
)
def delete_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_public_health_officer),
):
    """Delete disease case record."""
    case = db.query(DiseaseCase).filter(DiseaseCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disease case record not found",
        )

    db.delete(case)
    db.commit()
    logger.info(f"Disease Case {case_id} deleted by {current_user.email}")
    return {"status": "success", "message": f"Disease case {case_id} removed"}
