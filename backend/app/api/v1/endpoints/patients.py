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
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.disease import CaseStatus, Disease, DiseaseCase
from app.models.patient import Patient
from app.models.user import Role, User
from app.models.spatial import District, LocalBody, Ward
from app.models.monitoring import PatientLocation
from app.schemas.auth import RoleEnum
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

router = APIRouter()


def build_patient_response(patient: Patient, db: Session) -> PatientResponse:
    """Build detailed PatientResponse with linked user account, disease info, and latest GPS observation."""
    latest_loc = (
        db.query(PatientLocation)
        .filter(PatientLocation.patient_id == patient.id)
        .order_by(PatientLocation.recorded_at.desc())
        .first()
    )

    account_email = patient.user.email if patient.user else None
    ward_name = patient.ward.name if patient.ward else None
    ward_code = patient.ward.ward_code if patient.ward else None

    disease_id = patient.disease_id
    disease_name = patient.disease_name
    if not disease_name and patient.disease:
        disease_name = patient.disease.name

    return PatientResponse(
        id=patient.id,
        user_id=patient.user_id,
        assigned_worker_id=patient.assigned_worker_id,
        pseudo_id=patient.pseudo_id,
        full_name=patient.full_name,
        age=patient.age,
        gender=patient.gender,
        has_phone=patient.has_phone,
        contact_number=patient.contact_number,
        disease_id=disease_id,
        disease_name=disease_name,
        address=patient.address,
        district_name=patient.district_name,
        local_body_name=patient.local_body_name,
        ward_number=patient.ward_number,
        ward_name=ward_name,
        ward_code=ward_code,
        district_id=patient.district_id,
        local_body_id=patient.local_body_id,
        ward_id=patient.ward_id,
        is_active=patient.is_active,
        account_email=account_email,
        account_id=patient.pseudo_id,
        latest_latitude=latest_loc.latitude if latest_loc else None,
        latest_longitude=latest_loc.longitude if latest_loc else None,
        latest_accuracy=latest_loc.accuracy or latest_loc.accuracy_meters if latest_loc else None,
        latest_recorded_at=latest_loc.recorded_at if latest_loc else None,
        latest_source=latest_loc.source if latest_loc else None,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient record with linked user account",
    description="Authorized health workers and officers can register new patient records. Creates linked user account.",
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_health_worker),
) -> PatientResponse:
    """Create a new patient record and corresponding User authentication account."""
    # 1. Validate pseudo_id uniqueness
    existing = db.query(Patient).filter(Patient.pseudo_id == payload.pseudo_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A patient with pseudo ID '{payload.pseudo_id}' already exists",
        )

    # 2. Resolve account email
    account_email = (
        payload.email.strip().lower()
        if payload.email and payload.email.strip()
        else f"{payload.pseudo_id.lower()}@patient.healthwatch.org"
    )

    # 3. Check for existing user with this email
    existing_user = db.query(User).filter(User.email == account_email).first()
    if existing_user and not payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account already exists for email '{account_email}'. Please choose a different email.",
        )

    # 4. Validate Administrative Hierarchy (District -> Local Body -> Ward)
    district_id = payload.district_id
    local_body_id = payload.local_body_id
    ward_id = payload.ward_id
    district_name = payload.district_name
    local_body_name = payload.local_body_name
    ward_number = payload.ward_number

    if district_id:
        d = db.query(District).filter(District.id == district_id).first()
        if not d:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid district ID specified")
        district_name = d.name

    if local_body_id:
        lb = db.query(LocalBody).filter(LocalBody.id == local_body_id).first()
        if not lb:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid local body ID specified")
        if district_id and lb.district_id != district_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referential integrity error: Selected local body does not belong to the selected district",
            )
        local_body_name = lb.name
        if not district_id:
            district_id = lb.district_id
            district_name = lb.district.name if lb.district else district_name

    if ward_id:
        w = db.query(Ward).filter(Ward.id == ward_id).first()
        if not w:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ward ID specified")
        if local_body_id and w.local_body_id != local_body_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referential integrity error: Selected ward does not belong to the selected local body",
            )
        ward_number = w.ward_number
        if not local_body_id:
            local_body_id = w.local_body_id
            local_body_name = w.local_body.name if w.local_body else local_body_name
            if w.local_body and not district_id:
                district_id = w.local_body.district_id
                district_name = w.local_body.district.name if w.local_body.district else district_name

    # 5. Create linked User account if not already provided
    user_id = payload.user_id
    if not user_id:
        role_patient = db.query(Role).filter(Role.name == RoleEnum.PATIENT.value).first()
        if not role_patient:
            role_patient = Role(name=RoleEnum.PATIENT.value, description="Monitored Patient Role")
            db.add(role_patient)
            db.flush()

        initial_pwd = payload.initial_password if payload.initial_password else f"Patient@{payload.pseudo_id}"
        new_user = User(
            email=account_email,
            hashed_password=get_password_hash(initial_pwd),
            full_name=payload.full_name,
            role_id=role_patient.id,
            is_active=payload.is_active,
            is_superuser=False,
        )
        db.add(new_user)
        db.flush()
        user_id = new_user.id
        logger.info(f"Created linked user account {new_user.email} for patient {payload.pseudo_id}")

    assigned_worker_id = getattr(payload, "assigned_worker_id", None)
    if not assigned_worker_id and current_user.role and current_user.role.name == RoleEnum.HEALTH_WORKER.value:
        assigned_worker_id = current_user.id

    # Resolve Disease Details
    disease_id = payload.disease_id
    disease_name = payload.disease_name
    if disease_id:
        d_rec = db.query(Disease).filter(Disease.id == disease_id).first()
        if not d_rec:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid disease ID specified")
        disease_name = d_rec.name

    has_phone = payload.has_phone
    contact_number = payload.contact_number if has_phone else None

    patient = Patient(
        pseudo_id=payload.pseudo_id,
        user_id=user_id,
        assigned_worker_id=assigned_worker_id,
        full_name=payload.full_name,
        age=payload.age,
        gender=payload.gender.upper(),
        has_phone=has_phone,
        contact_number=contact_number,
        disease_id=disease_id,
        disease_name=disease_name,
        address=payload.address,
        district_id=district_id,
        local_body_id=local_body_id,
        ward_id=ward_id,
        district_name=district_name,
        local_body_name=local_body_name,
        ward_number=ward_number,
        is_active=payload.is_active,
    )
    db.add(patient)
    db.flush()

    # Automatically create DiseaseCase for patient if disease assigned
    if disease_id:
        w_obj = db.query(Ward).filter(Ward.id == ward_id).first() if ward_id else None
        lat = w_obj.center_latitude if w_obj and w_obj.center_latitude else 10.5276
        lng = w_obj.center_longitude if w_obj and w_obj.center_longitude else 76.2144
        new_case = DiseaseCase(
            patient_id=patient.id,
            disease_id=disease_id,
            ward_id=ward_id,
            case_status=CaseStatus.CONFIRMED.value,
            severity="MODERATE",
            diagnosis_date=datetime.date.today(),
            latitude=lat,
            longitude=lng,
            source="SURVEILLANCE",
            clinical_notes=f"Clinical surveillance record for patient {patient.pseudo_id}",
        )
        db.add(new_case)
        db.flush()

    db.commit()
    db.refresh(patient)

    logger.info(f"Patient registered: {patient.pseudo_id} ({patient.full_name}) linked to user {user_id}, disease: {disease_name}")
    return build_patient_response(patient, db)


@router.get(
    "/",
    response_model=PatientListResponse,
    summary="List, search and filter patient records",
    description="Health workers view all patients with search/filter; Patients only view their own record.",
)
def list_patients(
    q: Optional[str] = Query(None, description="Search term for pseudo_id, name, or address"),
    district_name: Optional[str] = Query(None, description="Filter by district name"),
    district_id: Optional[uuid.UUID] = Query(None, description="Filter by district UUID"),
    local_body_id: Optional[uuid.UUID] = Query(None, description="Filter by local body UUID"),
    ward_id: Optional[uuid.UUID] = Query(None, description="Filter by ward UUID"),
    ward_number: Optional[int] = Query(None, description="Filter by ward number"),
    disease_id: Optional[uuid.UUID] = Query(None, description="Filter by disease catalog ID"),
    has_phone: Optional[bool] = Query(None, description="Filter by mobile phone availability"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientListResponse:
    """Retrieve patient records with role-based access filtering and administrative hierarchy."""
    query = db.query(Patient)

    user_role = current_user.role.name if current_user.role else ""

    # Patient role restriction: patients cannot query global registry
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Patients are not authorized to query the patient registry. Use /api/v1/patients/me.",
        )
    elif user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        query = query.filter(Patient.assigned_worker_id == current_user.id)
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                (Patient.pseudo_id.ilike(search_pattern)) |
                (Patient.full_name.ilike(search_pattern)) |
                (Patient.address.ilike(search_pattern))
            )
        if district_id:
            query = query.filter(Patient.district_id == district_id)
        elif district_name:
            query = query.filter(Patient.district_name.ilike(f"%{district_name}%"))
        if local_body_id:
            query = query.filter(Patient.local_body_id == local_body_id)
        if ward_id:
            query = query.filter(Patient.ward_id == ward_id)
        elif ward_number is not None:
            query = query.filter(Patient.ward_number == ward_number)
        if disease_id:
            query = query.filter(Patient.disease_id == disease_id)
        if has_phone is not None:
            query = query.filter(Patient.has_phone == has_phone)
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
        if district_id:
            query = query.filter(Patient.district_id == district_id)
        elif district_name:
            query = query.filter(Patient.district_name.ilike(f"%{district_name}%"))
        if local_body_id:
            query = query.filter(Patient.local_body_id == local_body_id)
        if ward_id:
            query = query.filter(Patient.ward_id == ward_id)
        elif ward_number is not None:
            query = query.filter(Patient.ward_number == ward_number)
        if disease_id:
            query = query.filter(Patient.disease_id == disease_id)
        if has_phone is not None:
            query = query.filter(Patient.has_phone == has_phone)
        if is_active is not None:
            query = query.filter(Patient.is_active == is_active)

    total = query.count()
    patients_raw = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()

    items = [build_patient_response(p, db) for p in patients_raw]
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
    """Get current authenticated patient's own profile strictly isolated."""
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
    return build_patient_response(patient, db)


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
    """Get single patient record with strict authorization checks."""
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

    return build_patient_response(patient, db)


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
    """Update patient details and linked user status."""
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

    # Validate Administrative Hierarchy if changing
    district_id = payload.district_id if payload.district_id is not None else patient.district_id
    local_body_id = payload.local_body_id if payload.local_body_id is not None else patient.local_body_id
    ward_id = payload.ward_id if payload.ward_id is not None else patient.ward_id

    if local_body_id and district_id:
        lb = db.query(LocalBody).filter(LocalBody.id == local_body_id).first()
        if lb and lb.district_id != district_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referential integrity error: Selected local body does not belong to the selected district",
            )

    if ward_id and local_body_id:
        w = db.query(Ward).filter(Ward.id == ward_id).first()
        if w and w.local_body_id != local_body_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referential integrity error: Selected ward does not belong to the selected local body",
            )

    update_data = payload.model_dump(exclude_unset=True)

    # If updating email or password, sync to linked User
    email_val = update_data.pop("email", None)
    password_val = update_data.pop("password", None)

    if (email_val or password_val) and patient.user:
        if email_val and email_val.strip():
            patient.user.email = email_val.strip().lower()
        if password_val and len(password_val) >= 6:
            patient.user.hashed_password = get_password_hash(password_val)

    # If updating active status, sync to linked User
    if "is_active" in update_data and patient.user:
        patient.user.is_active = update_data["is_active"]

    # If updating disease, sync disease_name and DiseaseCase
    if "disease_id" in update_data:
        new_d_id = update_data.pop("disease_id")
        if new_d_id:
            d_rec = db.query(Disease).filter(Disease.id == new_d_id).first()
            if d_rec:
                patient.disease_id = new_d_id
                patient.disease_name = d_rec.name
                # sync or create DiseaseCase
                existing_case = db.query(DiseaseCase).filter(DiseaseCase.patient_id == patient.id).first()
                if existing_case:
                    existing_case.disease_id = new_d_id
                    existing_case.ward_id = patient.ward_id
                else:
                    lat = patient.ward.center_latitude if patient.ward and patient.ward.center_latitude else 10.5276
                    lng = patient.ward.center_longitude if patient.ward and patient.ward.center_longitude else 76.2144
                    new_case = DiseaseCase(
                        patient_id=patient.id,
                        disease_id=new_d_id,
                        ward_id=patient.ward_id,
                        case_status=CaseStatus.CONFIRMED.value,
                        severity="MODERATE",
                        diagnosis_date=datetime.date.today(),
                        latitude=lat,
                        longitude=lng,
                        source="SURVEILLANCE",
                        clinical_notes=f"Clinical surveillance record for patient {patient.pseudo_id}",
                    )
                    db.add(new_case)
        else:
            patient.disease_id = None
            patient.disease_name = None

    # If updating phone availability
    if "has_phone" in update_data:
        has_phone_val = update_data.pop("has_phone")
        patient.has_phone = has_phone_val
        if not has_phone_val:
            patient.contact_number = None

    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    logger.info(f"Patient {patient.pseudo_id} updated by {current_user.email}")
    return build_patient_response(patient, db)


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
    """Deactivate patient record and corresponding login account (soft deactivation)."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found",
        )

    patient.is_active = False
    if patient.user:
        patient.user.is_active = False

    db.commit()
    logger.info(f"Patient {patient.pseudo_id} and user account deactivated by {current_user.email}")
    return {"status": "success", "message": f"Patient {patient.pseudo_id} and login account deactivated"}
