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

    latest_lat = latest_loc.latitude if latest_loc else None
    latest_lng = latest_loc.longitude if latest_loc else None
    latest_acc = (latest_loc.accuracy or latest_loc.accuracy_meters) if latest_loc else None
    latest_rec = latest_loc.recorded_at if latest_loc else None
    latest_src = latest_loc.source if latest_loc else None

    # For patients without a smartphone or without GPS, provide official administrative location according to Ward -> Local Body (Panchayath) -> District
    if not patient.has_phone or latest_loc is None:
        ward = patient.ward or (db.query(Ward).filter(Ward.id == patient.ward_id).first() if patient.ward_id else None)
        local_body = patient.local_body or (db.query(LocalBody).filter(LocalBody.id == patient.local_body_id).first() if patient.local_body_id else None)
        district = patient.district or (db.query(District).filter(District.id == patient.district_id).first() if patient.district_id else None)

        if ward and ward.center_latitude is not None and ward.center_longitude is not None:
            latest_lat = ward.center_latitude
            latest_lng = ward.center_longitude
            latest_src = "STATIC_ADMIN_LOCATION"
            if not ward_name:
                ward_name = ward.name
            if not ward_code:
                ward_code = ward.ward_code
        elif local_body and local_body.center_latitude is not None and local_body.center_longitude is not None:
            latest_lat = local_body.center_latitude
            latest_lng = local_body.center_longitude
            latest_src = "STATIC_ADMIN_LOCATION"
        elif district and district.center_latitude is not None and district.center_longitude is not None:
            latest_lat = district.center_latitude
            latest_lng = district.center_longitude
            latest_src = "STATIC_ADMIN_LOCATION"

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
        date_of_birth=patient.date_of_birth,
        tracking_interval_minutes=patient.tracking_interval_minutes or 15,
        tracking_days=patient.tracking_days or "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday",
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
        latest_latitude=latest_lat,
        latest_longitude=latest_lng,
        latest_accuracy=latest_acc,
        latest_recorded_at=latest_rec,
        latest_source=latest_src,
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

    d_obj: Optional[District] = None
    lb_obj: Optional[LocalBody] = None
    w_obj: Optional[Ward] = None

    if ward_id:
        w_obj = db.query(Ward).filter(Ward.id == ward_id).first()
        if not w_obj:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ward ID specified")
        if local_body_id and w_obj.local_body_id != local_body_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referential integrity error: Selected ward does not belong to the selected local body",
            )
        ward_number = w_obj.ward_number
        if not local_body_id:
            local_body_id = w_obj.local_body_id
            local_body_name = w_obj.local_body.name if w_obj.local_body else local_body_name
            if w_obj.local_body and not district_id:
                district_id = w_obj.local_body.district_id
                district_name = w_obj.local_body.district.name if w_obj.local_body.district else district_name

    if local_body_id and not lb_obj:
        lb_obj = db.query(LocalBody).filter(LocalBody.id == local_body_id).first()
        if not lb_obj:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid local body ID specified")
        if district_id and lb_obj.district_id != district_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referential integrity error: Selected local body does not belong to the selected district",
            )
        local_body_name = lb_obj.name
        if not district_id:
            district_id = lb_obj.district_id
            district_name = lb_obj.district.name if lb_obj.district else district_name

    if district_id and not d_obj:
        d_obj = db.query(District).filter(District.id == district_id).first()
        if not d_obj:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid district ID specified")
        district_name = d_obj.name

    if w_obj and not lb_obj and w_obj.local_body:
        lb_obj = w_obj.local_body
    if lb_obj and not d_obj and lb_obj.district:
        d_obj = lb_obj.district

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
    contact_number = None
    if has_phone:
        if not payload.contact_number or not payload.contact_number.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required when mobile phone availability is YES",
            )
        contact_number = payload.contact_number.strip()

    tracking_interval_minutes = payload.tracking_interval_minutes or 15
    if tracking_interval_minutes not in (1, 5, 10, 15):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPS tracking interval must be one of: 1, 5, 10, or 15 minutes",
        )

    tracking_days = payload.tracking_days or "Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday"

    patient = Patient(
        pseudo_id=payload.pseudo_id,
        user_id=user_id,
        assigned_worker_id=assigned_worker_id,
        full_name=payload.full_name,
        age=payload.age,
        gender=payload.gender.upper(),
        has_phone=has_phone,
        contact_number=contact_number,
        date_of_birth=payload.date_of_birth,
        tracking_interval_minutes=tracking_interval_minutes,
        tracking_days=tracking_days,
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
        lat = None
        lng = None
        if w_obj and w_obj.center_latitude is not None and w_obj.center_longitude is not None:
            lat = float(w_obj.center_latitude)
            lng = float(w_obj.center_longitude)
        elif lb_obj and lb_obj.center_latitude is not None and lb_obj.center_longitude is not None:
            lat = float(lb_obj.center_latitude)
            lng = float(lb_obj.center_longitude)
        elif d_obj and d_obj.center_latitude is not None and d_obj.center_longitude is not None:
            lat = float(d_obj.center_latitude)
            lng = float(d_obj.center_longitude)
        else:
            lat = 10.5276
            lng = 76.2144

        new_case = DiseaseCase(
            patient_id=patient.id,
            disease_id=disease_id,
            ward_id=ward_id,
            case_status=CaseStatus.CONFIRMED.value,
            severity="MODERATE",
            diagnosis_date=datetime.date.today(),
            latitude=lat,
            longitude=lng,
            source="STATIC_ADMIN_LOCATION" if not has_phone else "SURVEILLANCE",
            clinical_notes=f"Clinical surveillance record for patient {patient.pseudo_id} ({'No Phone - Administrative Centroid' if not has_phone else 'GPS Active'})",
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
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientListResponse:
    """Retrieve patient records with role-based access filtering and administrative hierarchy."""
    query = db.query(Patient)

    user_role = current_user.role.name if current_user.role else ""

    # Strict RBAC Isolation: Patients can ONLY view their own record
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        query = query.filter(Patient.user_id == current_user.id)
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

    # Sync administrative hierarchy details
    d_obj = db.query(District).filter(District.id == district_id).first() if district_id else None
    lb_obj = db.query(LocalBody).filter(LocalBody.id == local_body_id).first() if local_body_id else None
    w_obj = db.query(Ward).filter(Ward.id == ward_id).first() if ward_id else None
    if d_obj:
        patient.district_name = d_obj.name
        patient.district_id = d_obj.id
    if lb_obj:
        patient.local_body_name = lb_obj.name
        patient.local_body_id = lb_obj.id
    if w_obj:
        patient.ward_number = w_obj.ward_number
        patient.ward_id = w_obj.id

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

    # If updating phone availability
    if "has_phone" in update_data:
        has_phone_val = update_data.pop("has_phone")
        patient.has_phone = has_phone_val
        if not has_phone_val:
            patient.contact_number = None

    # Resolve coordinates from administrative hierarchy for no-phone representation
    admin_lat = None
    admin_lng = None
    if w_obj and w_obj.center_latitude is not None and w_obj.center_longitude is not None:
        admin_lat = w_obj.center_latitude
        admin_lng = w_obj.center_longitude
    elif lb_obj and lb_obj.center_latitude is not None and lb_obj.center_longitude is not None:
        admin_lat = lb_obj.center_latitude
        admin_lng = lb_obj.center_longitude
    elif d_obj and d_obj.center_latitude is not None and d_obj.center_longitude is not None:
        admin_lat = d_obj.center_latitude
        admin_lng = d_obj.center_longitude

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
                    if not patient.has_phone and admin_lat is not None and admin_lng is not None:
                        existing_case.latitude = admin_lat
                        existing_case.longitude = admin_lng
                        existing_case.source = "STATIC_ADMIN_LOCATION"
                else:
                    lat = admin_lat or 10.5276
                    lng = admin_lng or 76.2144
                    new_case = DiseaseCase(
                        patient_id=patient.id,
                        disease_id=new_d_id,
                        ward_id=patient.ward_id,
                        case_status=CaseStatus.CONFIRMED.value,
                        severity="MODERATE",
                        diagnosis_date=datetime.date.today(),
                        latitude=lat,
                        longitude=lng,
                        source="STATIC_ADMIN_LOCATION" if not patient.has_phone else "SURVEILLANCE",
                        clinical_notes=f"Clinical surveillance record for patient {patient.pseudo_id} ({'No Phone - Administrative Centroid' if not patient.has_phone else 'GPS Active'})",
                    )
                    db.add(new_case)
        else:
            patient.disease_id = None
            patient.disease_name = None
    elif not patient.has_phone and admin_lat is not None and admin_lng is not None:
        # Sync existing DiseaseCase location if administrative hierarchy was modified
        existing_case = db.query(DiseaseCase).filter(DiseaseCase.patient_id == patient.id).first()
        if existing_case:
            existing_case.ward_id = patient.ward_id
            existing_case.latitude = admin_lat
            existing_case.longitude = admin_lng
            existing_case.source = "STATIC_ADMIN_LOCATION"


    if "tracking_interval_minutes" in update_data:
        new_int = update_data.pop("tracking_interval_minutes")
        if new_int in (1, 5, 10, 15):
            patient.tracking_interval_minutes = new_int
            from app.models.monitoring import MonitoringSession, SessionStatus
            active_sessions = db.query(MonitoringSession).filter(
                MonitoringSession.patient_id == patient.id,
                MonitoringSession.status == SessionStatus.ACTIVE.value
            ).all()
            for s in active_sessions:
                s.sampling_interval_minutes = new_int

    if "tracking_days" in update_data:
        new_days = update_data.pop("tracking_days")
        if new_days:
            patient.tracking_days = new_days
            from app.models.monitoring import MonitoringSession, SessionStatus
            active_sessions = db.query(MonitoringSession).filter(
                MonitoringSession.patient_id == patient.id,
                MonitoringSession.status == SessionStatus.ACTIVE.value
            ).all()
            for s in active_sessions:
                s.tracking_days = new_days

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
