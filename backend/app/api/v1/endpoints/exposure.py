import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import get_current_user, get_db, require_admin_or_officer
from app.models.disease import DiseaseCase
from app.models.exposure import ExposureEvent, ExposureStatus
from app.models.monitoring import PatientLocation
from app.models.patient import Patient
from app.models.user import User
from app.schemas.exposure import (
    ExposureAnalysisRequest,
    ExposureAnalysisSummaryResponse,
    ExposureEventResponse,
    ExposureEventUpdateRequest,
    ExposureListResponse,
    ExposureStatusEnum,
)

router = APIRouter()


def _build_event_response(ev: ExposureEvent, db: Session) -> ExposureEventResponse:
    """Helper to enrich ExposureEvent with patient pseudo IDs and approximate location."""
    p_a_pseudo = ev.patient_a.pseudo_id if ev.patient_a else "UNKNOWN"
    p_b_pseudo = ev.patient_b.pseudo_id if ev.patient_b else "UNKNOWN"

    # Fetch associated disease codes / names
    p_a_case = db.query(DiseaseCase).filter(DiseaseCase.patient_id == ev.patient_a_id).first() if ev.patient_a_id else None
    p_b_case = db.query(DiseaseCase).filter(DiseaseCase.patient_id == ev.patient_b_id).first() if ev.patient_b_id else None
    
    p_a_dis = p_a_case.disease.name if (p_a_case and p_a_case.disease) else (p_a_case.disease_code if p_a_case else "Monitored Contact")
    p_b_dis = p_b_case.disease.name if (p_b_case and p_b_case.disease) else (p_b_case.disease_code if p_b_case else "Monitored Contact")

    # Approximate location descriptor
    ward_name = None
    if ev.patient_a and ev.patient_a.local_body_name:
        ward_name = f"Ward #{ev.patient_a.ward_number} ({ev.patient_a.local_body_name}, {ev.patient_a.district_name})"
    
    lat = ev.latitude or 8.5242
    lng = ev.longitude or 76.9367
    approx_loc = ward_name or f"Coordinates ({lat:.4f}, {lng:.4f})"

    reviewed_by_name = ev.reviewed_by.full_name if ev.reviewed_by else None

    return ExposureEventResponse(
        id=ev.id,
        exposure_id=ev.id,
        patient_a_id=ev.patient_a_id,
        patient_b_id=ev.patient_b_id,
        patient_a_pseudo_id=p_a_pseudo,
        patient_b_pseudo_id=p_b_pseudo,
        patient_a_disease=p_a_dis,
        patient_b_disease=p_b_dis,
        observation_a_time=ev.observation_a_time,
        observation_b_time=ev.observation_b_time,
        latitude=lat,
        longitude=lng,
        approximate_location=approx_loc,
        distance=round(ev.distance or ev.distance_meters or 0.0, 1),
        time_difference=round(ev.time_difference or ev.duration_minutes or 0.0, 1),
        confidence_score=round(ev.confidence_score or ev.risk_score or 0.5, 2),
        status=ExposureStatusEnum(ev.status),
        review_notes=ev.review_notes,
        reviewed_by=reviewed_by_name,
        reviewed_at=ev.reviewed_at,
        detected_at=ev.detected_at,
    )


# ==============================================================================
# 1. Query Potential Exposure Events (Officer & Admin Only)
# ==============================================================================
@router.get(
    "/events",
    response_model=ExposureListResponse,
    summary="List identified potential spatial-temporal exposure events",
    description="Authorized exclusively for PUBLIC_HEALTH_OFFICER and ADMIN roles. Returns candidate overlap events with review status.",
)
def list_exposure_events(
    status: Optional[ExposureStatusEnum] = Query(None, description="Filter by event status"),
    patient_id: Optional[uuid.UUID] = Query(None, description="Filter by patient involved (A or B)"),
    start_date: Optional[datetime.date] = Query(None, description="Filter detected on or after"),
    end_date: Optional[datetime.date] = Query(None, description="Filter detected on or before"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> ExposureListResponse:
    """Retrieve filtered potential exposure intersection events."""
    query = db.query(ExposureEvent)

    if status:
        query = query.filter(ExposureEvent.status == status.value)
    if patient_id:
        query = query.filter(
            (ExposureEvent.patient_a_id == patient_id) | (ExposureEvent.patient_b_id == patient_id)
        )
    if start_date:
        query = query.filter(func.date(ExposureEvent.detected_at) >= start_date)
    if end_date:
        query = query.filter(func.date(ExposureEvent.detected_at) <= end_date)

    total = query.count()
    events = query.order_by(ExposureEvent.detected_at.desc()).offset(offset).limit(limit).all()

    # Calculate status breakdown
    all_events = db.query(ExposureEvent.status).all()
    summary_counts = {
        "POTENTIAL": 0,
        "REVIEWED": 0,
        "DISMISSED": 0,
        "CONFIRMED_BY_AUTHORITY": 0,
    }
    for (s,) in all_events:
        if s in summary_counts:
            summary_counts[s] += 1

    items = [_build_event_response(ev, db) for ev in events]

    return ExposureListResponse(
        total=total,
        items=items,
        summary_by_status=summary_counts,
    )


# ==============================================================================
# 2. Run Spatial-Temporal Overlap Detection Algorithm
# ==============================================================================
@router.post(
    "/analyze",
    response_model=ExposureAnalysisSummaryResponse,
    summary="Execute PostGIS spatial-temporal overlap detection with configurable thresholds",
    description="Authorized exclusively for PUBLIC_HEALTH_OFFICER and ADMIN roles. Compares recorded observations based on distance and timestamps.",
)
def analyze_spatial_temporal_exposures(
    payload: ExposureAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> ExposureAnalysisSummaryResponse:
    """
    Execute spatial-temporal overlap detection between recorded observations.
    
    Identifies situations where two distinct patients' recorded location points satisfy:
      1. Spatial Separation <= spatial_distance_threshold_meters (using ST_DWithin on PostGIS Geography)
      2. Temporal Separation <= temporal_difference_threshold_minutes (comparing actual recorded timestamps)
    
    IMPORTANT:
    Does NOT interpolate artificial points. Operates strictly on recorded observations.
    Does NOT assert clinical transmission; labels findings as 'POTENTIAL' overlap events.
    """
    dist_threshold = payload.spatial_distance_threshold_meters
    time_threshold_sec = payload.temporal_difference_threshold_minutes * 60.0

    # Ensure PostGIS geography column is populated for all patient locations
    db.execute(
        text("""
            UPDATE patient_locations 
            SET location_geography = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography 
            WHERE location_geography IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL;
        """)
    )
    db.commit()

    # PostGIS Spatial-Temporal Intersection Query
    # loc1.patient_id < loc2.patient_id enforces symmetry and eliminates self-comparison
    sql_query = text("""
        SELECT 
            loc1.id AS loc1_id,
            loc1.patient_id AS patient_a_id,
            loc1.latitude AS lat1,
            loc1.longitude AS lng1,
            loc1.recorded_at AS time1,
            loc2.id AS loc2_id,
            loc2.patient_id AS patient_b_id,
            loc2.latitude AS lat2,
            loc2.longitude AS lng2,
            loc2.recorded_at AS time2,
            ST_Distance(loc1.location_geography, loc2.location_geography) AS distance_meters,
            ABS(EXTRACT(EPOCH FROM (loc1.recorded_at - loc2.recorded_at))) AS time_diff_sec
        FROM patient_locations loc1
        JOIN patient_locations loc2 ON loc1.patient_id < loc2.patient_id
        WHERE 
            loc1.location_geography IS NOT NULL
            AND loc2.location_geography IS NOT NULL
            AND ST_DWithin(loc1.location_geography, loc2.location_geography, :dist_threshold)
            AND ABS(EXTRACT(EPOCH FROM (loc1.recorded_at - loc2.recorded_at))) <= :time_threshold_sec
        ORDER BY distance_meters ASC, time_diff_sec ASC;
    """)

    results = db.execute(
        sql_query,
        {
            "dist_threshold": dist_threshold,
            "time_threshold_sec": time_threshold_sec,
        },
    ).fetchall()

    candidate_count = len(results)
    newly_created = 0
    retained = 0
    detected_event_objects: List[ExposureEvent] = []

    for r in results:
        p_a = r.patient_a_id
        p_b = r.patient_b_id
        dist_m = float(r.distance_meters)
        time_diff_min = round(float(r.time_diff_sec) / 60.0, 1)

        # Midpoint coordinates for visual display
        mid_lat = round((float(r.lat1) + float(r.lat2)) / 2.0, 5)
        mid_lng = round((float(r.lng1) + float(r.lng2)) / 2.0, 5)

        # Compute normalized decision-support confidence score (0.0 - 1.0)
        dist_factor = max(0.0, 1.0 - (dist_m / dist_threshold)) if dist_threshold > 0 else 1.0
        time_factor = max(0.0, 1.0 - (float(r.time_diff_sec) / time_threshold_sec)) if time_threshold_sec > 0 else 1.0
        confidence = round(0.5 * dist_factor + 0.5 * time_factor, 2)

        # Check if an exposure event for this observation pair already exists
        existing = db.query(ExposureEvent).filter(
            ExposureEvent.patient_a_id == p_a,
            ExposureEvent.patient_b_id == p_b,
            (
                (ExposureEvent.observation_a_id == r.loc1_id)
                & (ExposureEvent.observation_b_id == r.loc2_id)
            ) | (
                (ExposureEvent.observation_a_time == r.time1)
                & (ExposureEvent.observation_b_time == r.time2)
            ),
        ).first()

        if existing:
            retained += 1
            detected_event_objects.append(existing)
        else:
            new_event = ExposureEvent(
                patient_a_id=p_a,
                patient_b_id=p_b,
                observation_a_id=r.loc1_id,
                observation_b_id=r.loc2_id,
                observation_a_time=r.time1,
                observation_b_time=r.time2,
                latitude=mid_lat,
                longitude=mid_lng,
                distance=dist_m,
                time_difference=time_diff_min,
                confidence_score=confidence,
                status=ExposureStatus.POTENTIAL.value,
                source_patient_id=p_a,
                exposed_entity_token=f"TOKEN-{str(p_b)[:8]}",
                distance_meters=dist_m,
                duration_minutes=time_diff_min,
                risk_score=confidence,
            )
            db.add(new_event)
            db.flush()
            db.execute(
                text("UPDATE exposure_events SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"),
                {"lng": mid_lng, "lat": mid_lat, "id": str(new_event.id)},
            )
            newly_created += 1
            detected_event_objects.append(new_event)

    db.commit()

    # Build response objects
    event_responses = [_build_event_response(ev, db) for ev in detected_event_objects]

    return ExposureAnalysisSummaryResponse(
        status="success",
        spatial_threshold_meters=dist_threshold,
        temporal_threshold_minutes=payload.temporal_difference_threshold_minutes,
        candidate_pairs_evaluated=candidate_count,
        potential_overlaps_detected=len(detected_event_objects),
        newly_created_events=newly_created,
        existing_events_retained=retained,
        events=event_responses,
    )


# ==============================================================================
# 3. Officer Review & Dismiss Workflow
# ==============================================================================
@router.patch(
    "/events/{exposure_id}",
    response_model=ExposureEventResponse,
    summary="Update exposure event status (Review, Dismiss, or Confirm)",
    description="Authorized exclusively for PUBLIC_HEALTH_OFFICER and ADMIN roles.",
)
def update_exposure_event_status(
    exposure_id: uuid.UUID,
    payload: ExposureEventUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> ExposureEventResponse:
    """Update review status and audit notes for an exposure event."""
    event = db.query(ExposureEvent).filter(ExposureEvent.id == exposure_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exposure event not found")

    event.status = payload.status.value
    if payload.review_notes is not None:
        event.review_notes = payload.review_notes
    event.reviewed_by_id = current_user.id
    event.reviewed_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(event)

    logger.info(
        f"Exposure event {event.id} status updated to {event.status} by officer {current_user.email}"
    )
    return _build_event_response(event, db)


# ==============================================================================
# 4. Get Single Exposure Event
# ==============================================================================
@router.get(
    "/events/{exposure_id}",
    response_model=ExposureEventResponse,
    summary="Get detailed record for single exposure event",
    description="Authorized exclusively for PUBLIC_HEALTH_OFFICER and ADMIN roles.",
)
def get_exposure_event(
    exposure_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> ExposureEventResponse:
    """Retrieve single exposure event details."""
    event = db.query(ExposureEvent).filter(ExposureEvent.id == exposure_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exposure event not found")

    return _build_event_response(event, db)
