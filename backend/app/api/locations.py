import datetime
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import text
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.monitoring import (
    ConsentStatus,
    LocationConsent,
    MonitoringSession,
    PatientLocation,
    SessionStatus,
)
from app.models.patient import Patient
from app.models.user import User
from app.schemas.auth import RoleEnum
from app.schemas.consent import (
    LocationObservationCreate,
    LocationObservationDetailResponse,
)

router = APIRouter()


def create_audit_entry(
    db: Session,
    user_id: Optional[uuid.UUID],
    action: str,
    entity_name: str,
    entity_id: str,
    ip_address: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditLog:
    """Record an immutable compliance and surveillance audit event."""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        entity_name=entity_name,
        entity_id=str(entity_id),
        ip_address=ip_address,
        metadata_json=metadata,
    )
    db.add(audit)
    db.flush()
    return audit


@router.post(
    "",
    response_model=LocationObservationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit patient GPS location observation",
    description="Secure endpoint for Android app: resolves patient from JWT, validates spatial bounds, timestamp, consent, session, anti-duplication, and stores PostGIS Geography(Point, 4326).",
)
def record_location_observation(
    payload: LocationObservationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationObservationDetailResponse:
    """Ingest location observation with strict backend validation and anti-duplication idempotency."""
    now = datetime.datetime.now(datetime.timezone.utc)
    user_role = current_user.role.name if current_user.role else ""

    # 1. Verification: Monitoring Session Existence
    session = (
        db.query(MonitoringSession)
        .filter(MonitoringSession.id == payload.monitoring_session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session ID '{payload.monitoring_session_id}' not found",
        )

    # 2. Security: Resolve Authenticated Patient from JWT (Do NOT trust arbitrary patient_id from client)
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patient profile found linked to this authenticated user account",
            )
        # Verify Session Ownership: A patient must not submit for another patient
        if session.patient_id != patient.id:
            create_audit_entry(
                db=db,
                user_id=current_user.id,
                action="LOCATION_REJECTED",
                entity_name="MonitoringSession",
                entity_id=str(session.id),
                ip_address=request.client.host if request.client else None,
                metadata={
                    "reason": "Patient attempted cross-patient telemetry submission",
                    "authenticated_patient": patient.pseudo_id,
                    "target_session_owner": str(session.patient_id),
                },
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot submit location data for another patient's monitoring session",
            )
    else:
        # Administrative / Health Officer testing context
        patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient linked to this session does not exist",
            )

    # 3. Validation: Spatial Bounds
    if not (-90.0 <= payload.latitude <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Latitude {payload.latitude} is invalid; must be between -90 and 90 degrees",
        )
    if not (-180.0 <= payload.longitude <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Longitude {payload.longitude} is invalid; must be between -180 and 180 degrees",
        )

    # 4. Validation: Accuracy Reasonableness (GPS horizontal accuracy in meters)
    if payload.accuracy is not None:
        if payload.accuracy <= 0.0 or payload.accuracy > 5000.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GPS accuracy of {payload.accuracy}m is unreasonable (must be > 0 and <= 5000m)",
            )

    # 5. Validation: Timestamp Validity (Actual timestamp, not fabricated; bounds check)
    rec_time = payload.recorded_at
    if rec_time.tzinfo is None:
        rec_time = rec_time.replace(tzinfo=datetime.timezone.utc)

    # Reject timestamps in the future (allowing max 5 min device clock drift)
    if rec_time > now + datetime.timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timestamp: recorded_at '{rec_time.isoformat()}' cannot be in the future",
        )

    # Reject timestamps older than 30 days
    if rec_time < now - datetime.timedelta(days=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timestamp: recorded_at '{rec_time.isoformat()}' is older than 30 days",
        )

    # 6. Validation: Session Active Status
    if session.status != SessionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location submission rejected: Monitoring session is {session.status}, not ACTIVE",
        )
    if session.end_time < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location submission rejected: Monitoring session has expired",
        )
    if session.stopped_at and rec_time > session.stopped_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location submission rejected: Observation was recorded after session was stopped",
        )

    # 7. Validation: Active Consent Check
    consent = (
        db.query(LocationConsent)
        .filter(
            LocationConsent.id == session.consent_id,
            LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
        )
        .first()
    )
    if not consent or consent.monitoring_end < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location submission rejected: Underlying location consent is revoked, expired, or missing",
        )

    # 8. Anti-Duplication / Idempotency Check
    # A. Check via client_observation_id
    if payload.client_observation_id:
        existing = (
            db.query(PatientLocation)
            .filter(PatientLocation.client_observation_id == payload.client_observation_id)
            .first()
        )
        if existing:
            logger.info(f"Duplicate observation recognized via client_observation_id '{payload.client_observation_id}'")
            return LocationObservationDetailResponse(
                location_id=existing.id,
                patient_id=existing.patient_id,
                monitoring_session_id=existing.session_id,
                latitude=existing.latitude,
                longitude=existing.longitude,
                accuracy=existing.accuracy,
                recorded_at=existing.recorded_at,
                source=existing.source,
                created_at=existing.created_at,
                status="ACCEPTED",
                message="Duplicate observation recognized; existing record returned without re-inserting.",
                is_duplicate=True,
            )

    # B. Check via exact timestamp + coordinate matching (network retry anti-duplication)
    duplicate_match = (
        db.query(PatientLocation)
        .filter(
            PatientLocation.session_id == session.id,
            PatientLocation.recorded_at == rec_time,
            PatientLocation.latitude == payload.latitude,
            PatientLocation.longitude == payload.longitude,
        )
        .first()
    )
    if duplicate_match:
        logger.info(f"Duplicate observation recognized via matching timestamp and coordinates for session {session.id}")
        return LocationObservationDetailResponse(
            location_id=duplicate_match.id,
            patient_id=duplicate_match.patient_id,
            monitoring_session_id=duplicate_match.session_id,
            latitude=duplicate_match.latitude,
            longitude=duplicate_match.longitude,
            accuracy=duplicate_match.accuracy,
            recorded_at=duplicate_match.recorded_at,
            source=duplicate_match.source,
            created_at=duplicate_match.created_at,
            status="ACCEPTED",
            message="Duplicate observation detected via identical timestamp and coordinates; existing record returned.",
            is_duplicate=True,
        )

    # 9. Store in PostGIS with Geography(Point, 4326) and strict (Longitude, Latitude) order
    loc_id = uuid.uuid4()
    wkt_point = f"POINT({payload.longitude} {payload.latitude})"
    loc_source = payload.source or "PATIENT_GPS"

    loc_record = PatientLocation(
        id=loc_id,
        session_id=session.id,
        monitoring_session_id=session.id,
        patient_id=patient.id,
        recorded_at=rec_time,
        location=WKTElement(wkt_point, srid=4326),
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        accuracy_meters=payload.accuracy,
        source=loc_source,
        client_observation_id=payload.client_observation_id,
    )
    db.add(loc_record)
    db.flush()

    # Explicitly set Geography(Point, 4326) with correct (Longitude, Latitude) order
    db.execute(
        text("UPDATE patient_locations SET location_geography = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography WHERE id = :id"),
        {"lng": payload.longitude, "lat": payload.latitude, "id": str(loc_id)},
    )

    # 10. Audit Logging
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="LOCATION_SUBMITTED",
        entity_name="PatientLocation",
        entity_id=str(loc_id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "patient_pseudo_id": patient.pseudo_id,
            "session_id": str(session.id),
            "lat": payload.latitude,
            "lng": payload.longitude,
            "accuracy": payload.accuracy,
            "recorded_at": rec_time.isoformat(),
            "source": loc_source,
        },
    )

    db.commit()
    logger.info(f"Location observation accepted for Patient {patient.pseudo_id} @ ({payload.latitude}, {payload.longitude}) [Source: {loc_source}]")

    return LocationObservationDetailResponse(
        location_id=loc_id,
        patient_id=patient.id,
        monitoring_session_id=session.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        recorded_at=rec_time,
        source=loc_source,
        created_at=loc_record.created_at,
        status="ACCEPTED",
        message="Location observation verified and recorded successfully.",
        is_duplicate=False,
    )
