import datetime
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from loguru import logger

from app.api.deps import get_current_user
from app.core.config import settings
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
    AuditLogResponse,
    ConsentGrantRequest,
    ConsentResponse,
    ConsentRevokeRequest,
    LocationHistoryItem,
    LocationHistoryListResponse,
    LocationObservationResponse,
    LocationObservationSubmit,
    PatientMonitoringStatusResponse,
    SessionResponse,
    SessionStartRequest,
    SessionStopRequest,
)
from app.schemas.roadmap import (
    PatientRoadmapResponse,
    RoadmapObservationItem,
    RoadmapPoint,
    RoadmapStatistics,
)

router = APIRouter()

EXPLANATION_NOTICE = "HealthWatch will collect your location approximately every 15 minutes during the authorized monitoring period."


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


def get_patient_for_user(current_user: User, db: Session, target_patient_id: Optional[uuid.UUID] = None) -> Patient:
    """Resolve patient entity with strict RBAC ownership checks."""
    user_role = current_user.role.name if current_user.role else ""

    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patient profile found linked to this patient user account",
            )
        if target_patient_id and patient.id != target_patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access or manage another patient's monitoring records",
            )
        return patient

    # Health Worker flow: must be assigned to the requested patient
    if user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
        if target_patient_id:
            patient = db.query(Patient).filter(Patient.id == target_patient_id).first()
            if not patient:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Patient ID '{target_patient_id}' not found",
                )
            if patient.assigned_worker_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Patient is not assigned to this health worker",
                )
            return patient

        # Default to first assigned patient for health worker
        patient = db.query(Patient).filter(Patient.assigned_worker_id == current_user.id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patients currently assigned to this health worker",
            )
        return patient

    # Officer / Admin flow
    if target_patient_id:
        patient = db.query(Patient).filter(Patient.id == target_patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient ID '{target_patient_id}' not found",
            )
        return patient

    # Fallback for administrative exploration
    patient = db.query(Patient).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No patients exist in database")
    return patient


# ==============================================================================
# 1. Monitoring & Consent Status
# ==============================================================================

@router.get(
    "/status",
    response_model=PatientMonitoringStatusResponse,
    summary="Get complete monitoring and consent status for patient",
    description="Returns current consent status, active session, sampling frequency, and whether telemetry collection is authorized.",
)
def get_monitoring_status(
    patient_id: Optional[uuid.UUID] = Query(None, description="Patient ID (optional for authenticated patient)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientMonitoringStatusResponse:
    """Retrieve full location surveillance consent & session telemetry status."""
    patient = get_patient_for_user(current_user, db, patient_id)
    now = datetime.datetime.now(datetime.timezone.utc)

    # Check for Active Consent
    active_consent = (
        db.query(LocationConsent)
        .filter(
            LocationConsent.patient_id == patient.id,
            LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
            LocationConsent.monitoring_end > now,
        )
        .order_by(LocationConsent.created_at.desc())
        .first()
    )

    # Check for Active Monitoring Session
    active_session = None
    if active_consent:
        active_session = (
            db.query(MonitoringSession)
            .filter(
                MonitoringSession.patient_id == patient.id,
                MonitoringSession.status == SessionStatus.ACTIVE.value,
                MonitoringSession.end_time > now,
            )
            .order_by(MonitoringSession.created_at.desc())
            .first()
        )

    can_collect = bool(active_consent and active_session and active_session.status == SessionStatus.ACTIVE.value)

    # Resolve latest historical consent and session for baseline audit display
    latest_consent = active_consent or (
        db.query(LocationConsent)
        .filter(LocationConsent.patient_id == patient.id)
        .order_by(LocationConsent.created_at.desc())
        .first()
    )
    latest_session = active_session or (
        db.query(MonitoringSession)
        .filter(MonitoringSession.patient_id == patient.id)
        .order_by(MonitoringSession.created_at.desc())
        .first()
    )

    effective_interval = (
        (active_session.sampling_interval_minutes if active_session and active_session.sampling_interval_minutes else None)
        or (latest_session.sampling_interval_minutes if latest_session and latest_session.sampling_interval_minutes else None)
        or settings.LOCATION_SAMPLING_INTERVAL_MINUTES
    )

    return PatientMonitoringStatusResponse(
        patient_id=patient.id,
        patient_pseudo_id=patient.pseudo_id,
        has_active_consent=bool(active_consent),
        active_consent=active_consent,
        latest_consent=latest_consent,
        has_active_session=bool(active_session),
        active_session=active_session,
        latest_session=latest_session,
        can_collect_location=can_collect,
        sampling_interval_minutes=effective_interval,
        sampling_interval_seconds=effective_interval * 60,
        sampling_interval_description=f"Approximately {effective_interval} minutes",
        explanation_notice=f"HealthWatch will collect your location approximately every {effective_interval} minutes during the authorized monitoring period.",
    )


# ==============================================================================
# 2. Location Consent Agreement Management
# ==============================================================================

@router.get(
    "/consent",
    response_model=List[ConsentResponse],
    summary="List patient location consent history",
)
def list_consents(
    patient_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ConsentResponse]:
    """List all consent agreements for the patient."""
    patient = get_patient_for_user(current_user, db, patient_id)
    consents = (
        db.query(LocationConsent)
        .filter(LocationConsent.patient_id == patient.id)
        .order_by(LocationConsent.created_at.desc())
        .all()
    )
    return consents


@router.post(
    "/consent/grant",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Explicitly grant location monitoring consent",
    description="Patient explicitly grants consent for location telemetry over an authorized monitoring period.",
)
def grant_consent(
    payload: ConsentGrantRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentResponse:
    """Patient grants explicit location telemetry consent."""
    patient = get_patient_for_user(current_user, db, payload.patient_id)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    monitoring_start = payload.monitoring_start or now
    monitoring_end = payload.monitoring_end or (monitoring_start + datetime.timedelta(days=payload.duration_days))

    # Supersede previous active consent
    db.query(LocationConsent).filter(
        LocationConsent.patient_id == patient.id,
        LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
    ).update({"consent_status": ConsentStatus.EXPIRED.value})

    consent = LocationConsent(
        patient_id=patient.id,
        consent_status=ConsentStatus.ACTIVE.value,
        consent_given_at=now,
        consent_version=payload.consent_version,
        monitoring_start=monitoring_start,
        monitoring_end=monitoring_end,
        purpose=payload.purpose,
    )
    db.add(consent)
    db.flush()

    # Record Audit Log
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="CONSENT_GRANTED",
        entity_name="LocationConsent",
        entity_id=str(consent.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "patient_pseudo_id": patient.pseudo_id,
            "version": payload.consent_version,
            "monitoring_start": monitoring_start.isoformat(),
            "monitoring_end": monitoring_end.isoformat(),
        },
    )

    db.commit()
    db.refresh(consent)

    logger.info(f"Location Consent granted by Patient {patient.pseudo_id} (ID: {consent.id}) valid until {monitoring_end}")
    return consent


@router.post(
    "/consent/revoke",
    response_model=ConsentResponse,
    summary="Explicitly revoke location monitoring consent",
    description="Patient revokes consent. Automatically terminates all active monitoring sessions.",
)
def revoke_consent(
    payload: ConsentRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentResponse:
    """Revoke active location consent and immediately stop active monitoring."""
    patient = get_patient_for_user(current_user, db)
    now = datetime.datetime.now(datetime.timezone.utc)

    query = db.query(LocationConsent).filter(
        LocationConsent.patient_id == patient.id,
        LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
    )
    if payload.consent_id:
        query = query.filter(LocationConsent.id == payload.consent_id)

    consent = query.first()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active location consent found to revoke",
        )

    # 1. Mark consent revoked
    consent.consent_status = ConsentStatus.REVOKED.value
    consent.revoked_at = now

    # 2. Immediately stop any active monitoring sessions
    db.query(MonitoringSession).filter(
        MonitoringSession.patient_id == patient.id,
        MonitoringSession.status == SessionStatus.ACTIVE.value,
    ).update({
        "status": SessionStatus.STOPPED.value,
        "stopped_at": now,
    })

    # Record Audit Log
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="CONSENT_REVOKED",
        entity_name="LocationConsent",
        entity_id=str(consent.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "patient_pseudo_id": patient.pseudo_id,
            "reason": payload.reason,
            "revoked_at": now.isoformat(),
        },
    )

    db.commit()
    db.refresh(consent)

    logger.info(f"Location Consent revoked by Patient {patient.pseudo_id} (Reason: {payload.reason})")
    return consent


# ==============================================================================
# 3. Monitoring Session Management
# ==============================================================================

@router.post(
    "/sessions/start",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an authorized location monitoring session",
    description="Starts location monitoring. Fails if no valid, active, and unexpired consent exists.",
)
def start_monitoring_session(
    payload: SessionStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Start location monitoring session after verifying active consent."""
    patient = get_patient_for_user(current_user, db)
    now = datetime.datetime.now(datetime.timezone.utc)

    # Backend Verification: Check active, unexpired consent exists
    consent_query = db.query(LocationConsent).filter(
        LocationConsent.patient_id == patient.id,
        LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
        LocationConsent.monitoring_end > now,
    )
    if payload.consent_id:
        consent_query = consent_query.filter(LocationConsent.id == payload.consent_id)

    consent = consent_query.order_by(LocationConsent.created_at.desc()).first()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start monitoring session: No active, unexpired location consent found. Please grant explicit consent first.",
        )

    start_time = payload.start_time or now
    session_end = payload.end_time or (start_time + datetime.timedelta(hours=payload.duration_hours))
    
    # Cap session end time at consent expiration
    if session_end > consent.monitoring_end:
        session_end = consent.monitoring_end

    # Stop any prior active sessions
    db.query(MonitoringSession).filter(
        MonitoringSession.patient_id == patient.id,
        MonitoringSession.status == SessionStatus.ACTIVE.value,
    ).update({
        "status": SessionStatus.STOPPED.value,
        "stopped_at": now,
    })

    interval_mins = payload.sampling_interval_minutes or settings.LOCATION_SAMPLING_INTERVAL_MINUTES

    # Create new active monitoring session
    session = MonitoringSession(
        patient_id=patient.id,
        consent_id=consent.id,
        start_time=start_time,
        end_time=session_end,
        status=SessionStatus.ACTIVE.value,
        sampling_interval_minutes=interval_mins,
    )
    db.add(session)
    db.flush()

    # Record Audit Log
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="MONITORING_STARTED",
        entity_name="MonitoringSession",
        entity_id=str(session.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "patient_pseudo_id": patient.pseudo_id,
            "consent_id": str(consent.id),
            "start_time": start_time.isoformat(),
            "end_time": session_end.isoformat(),
            "sampling_interval": f"{interval_mins} mins",
        },
    )

    db.commit()
    db.refresh(session)

    logger.info(f"Active Monitoring Session started for Patient {patient.pseudo_id} (Session: {session.id}) until {session_end}")
    return session


@router.post(
    "/sessions/stop",
    response_model=SessionResponse,
    summary="Stop an active location monitoring session",
)
def stop_monitoring_session(
    payload: SessionStopRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Stop active monitoring session."""
    patient = get_patient_for_user(current_user, db)
    now = datetime.datetime.now(datetime.timezone.utc)

    query = db.query(MonitoringSession).filter(
        MonitoringSession.patient_id == patient.id,
        MonitoringSession.status == SessionStatus.ACTIVE.value,
    )
    if payload.session_id:
        query = query.filter(MonitoringSession.id == payload.session_id)

    session = query.first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active monitoring session found to stop",
        )

    session.status = SessionStatus.STOPPED.value
    session.stopped_at = now

    # Record Audit Log
    create_audit_entry(
        db=db,
        user_id=current_user.id,
        action="MONITORING_STOPPED",
        entity_name="MonitoringSession",
        entity_id=str(session.id),
        ip_address=request.client.host if request.client else None,
        metadata={
            "patient_pseudo_id": patient.pseudo_id,
            "stopped_at": now.isoformat(),
        },
    )

    db.commit()
    db.refresh(session)

    logger.info(f"Monitoring Session {session.id} stopped for Patient {patient.pseudo_id}")
    return session


@router.get(
    "/sessions/current",
    response_model=Optional[SessionResponse],
    summary="Get current active monitoring session",
)
def get_current_session(
    patient_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[SessionResponse]:
    """Retrieve active monitoring session if running."""
    patient = get_patient_for_user(current_user, db, patient_id)
    now = datetime.datetime.now(datetime.timezone.utc)

    session = (
        db.query(MonitoringSession)
        .filter(
            MonitoringSession.patient_id == patient.id,
            MonitoringSession.status == SessionStatus.ACTIVE.value,
            MonitoringSession.end_time > now,
        )
        .order_by(MonitoringSession.created_at.desc())
        .first()
    )
    return session


# ==============================================================================
# 4. Location Observation Ingestion & Strict Verification
# ==============================================================================

@router.post(
    "/locations/submit",
    response_model=LocationObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit periodic location observation from mobile client/agent",
    description="Strictly verifies: authenticated patient + active consent + active session + correct ownership + valid timestamp.",
)
def submit_location_observation(
    payload: LocationObservationSubmit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationObservationResponse:
    """Ingest location observation with strict multi-layer consent and session validation."""
    patient = get_patient_for_user(current_user, db)
    now = datetime.datetime.now(datetime.timezone.utc)
    obs_time = payload.recorded_at or now

    # 1. Verification: Find session
    target_session_id = payload.effective_session_id
    session = db.query(MonitoringSession).filter(MonitoringSession.id == target_session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referenced monitoring session ID '{target_session_id}' does not exist",
        )

    # 2. Verification: Patient Ownership
    if session.patient_id != patient.id:
        create_audit_entry(
            db=db,
            user_id=current_user.id,
            action="LOCATION_REJECTED",
            entity_name="MonitoringSession",
            entity_id=str(session.id),
            ip_address=request.client.host if request.client else None,
            metadata={"reason": "Session does not belong to submitting patient", "submitting_patient": patient.pseudo_id},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot submit location observations for another patient's monitoring session",
        )

    # 3. Verification: Session Status
    if session.status != SessionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location submission rejected: Monitoring session is {session.status}, not ACTIVE",
        )

    # 4. Verification: Active Consent Check
    consent = db.query(LocationConsent).filter(
        LocationConsent.id == session.consent_id,
        LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
    ).first()

    if not consent or consent.monitoring_end < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location submission rejected: Underlying location consent is revoked, expired, or missing",
        )

    # 5. Verification: Timestamp Bounds Check
    if obs_time > session.end_time or (session.stopped_at and obs_time > session.stopped_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location submission rejected: Observation timestamp falls outside the active session window",
        )

    # 6. Store location telemetry in PostGIS
    loc_id = uuid.uuid4()
    wkt_point = f"POINT({payload.longitude} {payload.latitude})"
    eff_accuracy = payload.effective_accuracy
    loc_source = payload.source or "PATIENT_GPS"

    loc_record = PatientLocation(
        id=loc_id,
        session_id=session.id,
        patient_id=patient.id,
        recorded_at=obs_time,
        location=WKTElement(wkt_point, srid=4326),
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=eff_accuracy,
        speed_mps=payload.speed_mps,
        altitude=payload.altitude,
        is_mock_provider=payload.is_mock_provider,
        source=loc_source,
    )
    db.add(loc_record)
    db.flush()

    # 7. Record Audit Log
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
            "accuracy": eff_accuracy,
            "source": loc_source,
        },
    )

    db.commit()
    logger.info(f"Location observation accepted for Patient {patient.pseudo_id} @ ({payload.latitude}, {payload.longitude}) [Source: {loc_source}]")

    return LocationObservationResponse(
        id=loc_id,
        session_id=session.id,
        patient_id=patient.id,
        recorded_at=obs_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=eff_accuracy,
        source=loc_source,
        status="ACCEPTED",
        message="Location observation verified under active consent and recorded successfully.",
    )


# ==============================================================================
# 5. Audit Inspection APIs
# ==============================================================================

@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="List location consent & monitoring compliance audit logs",
)
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AuditLogResponse]:
    """Inspect system audit records."""
    user_role = current_user.role.name if current_user.role else ""
    query = db.query(AuditLog)

    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        query = query.filter(AuditLog.user_id == current_user.id)

    logs = query.order_by(AuditLog.recorded_at.desc()).limit(limit).all()
    return logs


@router.get(
    "/locations/history",
    response_model=LocationHistoryListResponse,
    summary="Get patient location history table records",
    description="Returns chronological tabular list of location observations with timestamp, latitude, longitude, accuracy, and source. Strictly enforces patient ownership RBAC.",
)
def get_patient_location_history(
    patient_id: Optional[uuid.UUID] = Query(None, description="Patient ID (must match authenticated patient if role is PATIENT)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocationHistoryListResponse:
    """Retrieve patient location history with strict ownership RBAC."""
    patient = get_patient_for_user(current_user, db, patient_id)

    query = db.query(PatientLocation).filter(PatientLocation.patient_id == patient.id)
    total = query.count()
    items = query.order_by(PatientLocation.recorded_at.desc()).offset(skip).limit(limit).all()

    formatted_items = []
    for loc in items:
        eff_acc = loc.accuracy if loc.accuracy is not None else loc.accuracy_meters
        formatted_items.append(
            LocationHistoryItem(
                id=loc.id,
                recorded_at=loc.recorded_at,
                latitude=loc.latitude,
                longitude=loc.longitude,
                accuracy=eff_acc,
                source=loc.source or "PATIENT_GPS",
                session_id=loc.session_id or loc.monitoring_session_id,
            )
        )

    return LocationHistoryListResponse(
        total=total,
        items=formatted_items,
        patient_id=patient.id,
        patient_pseudo_id=patient.pseudo_id,
    )


# ==============================================================================
# 6. Movement Roadmap API (Step 12)
# ==============================================================================

@router.get(
    "/roadmap",
    response_model=PatientRoadmapResponse,
    summary="Get patient movement roadmap",
    description="Retrieve authorized discrete location observations, sequential visual timeline, statistics, and limitation disclaimer.",
)
@router.get(
    "/patients/{patient_id}/roadmap",
    response_model=PatientRoadmapResponse,
    summary="Get patient movement roadmap by patient ID",
)
def get_patient_movement_roadmap(
    patient_id: Optional[uuid.UUID] = None,
    pseudo_id: Optional[str] = None,
    session_id: Optional[uuid.UUID] = None,
    date: Optional[str] = Query(None, description="Date filter format YYYY-MM-DD"),
    start_time: Optional[str] = Query(None, description="Start time filter (HH:MM or ISO)"),
    end_time: Optional[str] = Query(None, description="End time filter (HH:MM or ISO)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatientRoadmapResponse:
    """Retrieve chronologically ordered discrete location observations for patient movement roadmap."""
    user_role = current_user.role.name if current_user.role else ""

    # 1. Resolve Patient with strict RBAC
    if user_role == RoleEnum.PATIENT.value and not current_user.is_superuser:
        auth_patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not auth_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patient profile found for this user account",
            )
        if patient_id and patient_id != auth_patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patients can only retrieve their own movement roadmap.",
            )
        if pseudo_id and pseudo_id != auth_patient.pseudo_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patients can only retrieve their own movement roadmap.",
            )
        target_patient = auth_patient
    else:
        # Public health officer, health worker, admin
        if patient_id:
            target_patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not target_patient:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Patient with ID '{patient_id}' not found",
                )
        elif pseudo_id:
            target_patient = db.query(Patient).filter(Patient.pseudo_id == pseudo_id).first()
            if not target_patient:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Patient with pseudo ID '{pseudo_id}' not found",
                )
        else:
            # Default to active synthetic patient or assigned patient for health worker
            if user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
                target_patient = db.query(Patient).filter(Patient.assigned_worker_id == current_user.id).first()
                if not target_patient:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No patients currently assigned to this health worker",
                    )
            else:
                target_patient = (
                    db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
                    or db.query(Patient).first()
                )
                if not target_patient:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No patient records found in database",
                    )

        # Enforce Health Worker assignment check
        if user_role == RoleEnum.HEALTH_WORKER.value and not current_user.is_superuser:
            if target_patient.assigned_worker_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Patient is not assigned to this health worker",
                )

    # 2. Build Query
    query = db.query(PatientLocation).filter(PatientLocation.patient_id == target_patient.id)

    if session_id:
        query = query.filter(
            or_(
                PatientLocation.session_id == session_id,
                PatientLocation.monitoring_session_id == session_id,
            )
        )

    # Date and Time filtering
    parsed_date = None
    if date:
        try:
            parsed_date = datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format '{date}', expected YYYY-MM-DD",
            )

    if parsed_date:
        day_start = datetime.datetime.combine(parsed_date, datetime.time.min, tzinfo=datetime.timezone.utc)
        day_end = datetime.datetime.combine(parsed_date, datetime.time.max, tzinfo=datetime.timezone.utc)

        if start_time and ":" in start_time:
            try:
                parts = [int(p) for p in start_time.split(":")[:2]]
                day_start = datetime.datetime.combine(
                    parsed_date,
                    datetime.time(parts[0], parts[1]),
                    tzinfo=datetime.timezone.utc,
                )
            except Exception:
                pass

        if end_time and ":" in end_time:
            try:
                parts = [int(p) for p in end_time.split(":")[:2]]
                day_end = datetime.datetime.combine(
                    parsed_date,
                    datetime.time(parts[0], parts[1], 59),
                    tzinfo=datetime.timezone.utc,
                )
            except Exception:
                pass

        query = query.filter(
            PatientLocation.recorded_at >= day_start,
            PatientLocation.recorded_at <= day_end,
        )
    else:
        # Direct ISO timestamps if no date passed
        if start_time:
            try:
                st = datetime.datetime.fromisoformat(start_time)
                if st.tzinfo is None:
                    st = st.replace(tzinfo=datetime.timezone.utc)
                query = query.filter(PatientLocation.recorded_at >= st)
            except Exception:
                pass
        if end_time:
            try:
                et = datetime.datetime.fromisoformat(end_time)
                if et.tzinfo is None:
                    et = et.replace(tzinfo=datetime.timezone.utc)
                query = query.filter(PatientLocation.recorded_at <= et)
            except Exception:
                pass

    # Order strictly chronologically
    observations_raw = query.order_by(PatientLocation.recorded_at.asc()).all()

    # Resolve administrative hierarchy and disease for roadmap
    res_district = target_patient.district.name if target_patient.district else target_patient.district_name
    res_local_body = target_patient.local_body.name if target_patient.local_body else target_patient.local_body_name
    res_ward_name = target_patient.ward.name if target_patient.ward else (f"Ward {target_patient.ward_number}" if target_patient.ward_number else None)
    res_ward_num = target_patient.ward.ward_number if (target_patient.ward and target_patient.ward.ward_number) else target_patient.ward_number
    res_disease = target_patient.disease_name or (target_patient.disease.disease_name if target_patient.disease else None)

    # 3. Construct Items
    observation_items = []
    for obs in observations_raw:
        eff_acc = obs.accuracy if obs.accuracy is not None else obs.accuracy_meters
        observation_items.append(
            RoadmapObservationItem(
                id=obs.id,
                recorded_at=obs.recorded_at,
                latitude=obs.latitude,
                longitude=obs.longitude,
                accuracy=eff_acc,
                source=obs.source or "PATIENT_GPS",
                session_id=obs.session_id or obs.monitoring_session_id,
                district_name=res_district,
                local_body_name=res_local_body,
                ward_name=res_ward_name,
                ward_number=res_ward_num,
            )
        )

    # 4. Calculate Statistics (do not calculate unsupported speculative information)
    total_obs = len(observation_items)
    if total_obs > 0:
        start_rec = observation_items[0].recorded_at
        end_rec = observation_items[-1].recorded_at
        first_pt = RoadmapPoint(
            latitude=observation_items[0].latitude,
            longitude=observation_items[0].longitude,
        )
        last_pt = RoadmapPoint(
            latitude=observation_items[-1].latitude,
            longitude=observation_items[-1].longitude,
        )
        accs = [
            o.accuracy for o in observation_items if o.accuracy is not None and o.accuracy > 0
        ]
        avg_acc = round(sum(accs) / len(accs), 2) if accs else None
    else:
        start_rec = None
        end_rec = None
        first_pt = None
        last_pt = None
        avg_acc = None

    stats = RoadmapStatistics(
        total_observations=total_obs,
        monitoring_start=start_rec,
        monitoring_end=end_rec,
        first_recorded_location=first_pt,
        last_recorded_location=last_pt,
        average_accuracy=avg_acc,
    )

    return PatientRoadmapResponse(
        patient_id=target_patient.id,
        patient_pseudo_id=target_patient.pseudo_id,
        patient_name=target_patient.full_name,
        disease_name=res_disease,
        session_id=session_id,
        filter_date=date,
        start_time=start_time,
        end_time=end_time,
        statistics=stats,
        observations=observation_items,
    )

