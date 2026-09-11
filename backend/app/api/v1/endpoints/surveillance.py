"""Public Health Surveillance Dashboard Endpoint."""

import datetime
import uuid
from typing import List, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import require_admin_or_officer
from app.db.session import get_db
from app.models.disease import CaseStatus, Disease, DiseaseCase
from app.models.exposure import ExposureEvent, ExposureStatus
from app.models.monitoring import MonitoringSession, SessionStatus
from app.models.patient import Patient
from app.models.spatial import District, LocalBody, Ward
from app.models.user import User
from app.schemas.surveillance import (
    CaseByDiseaseItem,
    CaseByDistrictItem,
    CaseByLocalBodyItem,
    CaseByWardItem,
    CaseOverTimeItem,
    DashboardActiveFilters,
    DashboardChartData,
    DashboardDistrictMapItem,
    DashboardKPISummary,
    DashboardMapCaseItem,
    DashboardMapData,
    SurveillanceDashboardResponse,
)

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=SurveillanceDashboardResponse,
    summary="Get public health surveillance dashboard aggregations",
    description=(
        "Returns comprehensive real-time surveillance analytics, KPI metrics, "
        "Recharts categorical and time-series distributions, and spatial map datasets. "
        "Strictly accessible only to authorized Public Health Officers and Administrators."
    ),
)
def get_surveillance_dashboard(
    disease_id: Optional[uuid.UUID] = Query(None, description="Filter by disease catalog ID"),
    district_id: Optional[uuid.UUID] = Query(None, description="Filter by district ID"),
    local_body_id: Optional[uuid.UUID] = Query(None, description="Filter by local body ID"),
    ward_id: Optional[uuid.UUID] = Query(None, description="Filter by ward ID"),
    start_date: Optional[datetime.date] = Query(None, description="Filter cases on or after date"),
    end_date: Optional[datetime.date] = Query(None, description="Filter cases on or before date"),
    case_status: Optional[str] = Query(None, description="Filter by case status (CONFIRMED, SUSPECTED, RECOVERED, DECEASED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> SurveillanceDashboardResponse:
    """Dynamically aggregate real-time epidemiological metrics from the database."""

    # 1. Base Query for Disease Cases with Joins to Spatial and Disease entities
    query = (
        db.query(DiseaseCase)
        .join(Disease, DiseaseCase.disease_id == Disease.id)
        .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
        .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
        .outerjoin(District, LocalBody.district_id == District.id)
        .outerjoin(Patient, DiseaseCase.patient_id == Patient.id)
    )

    # 2. Apply Dynamic Filters
    if disease_id:
        query = query.filter(DiseaseCase.disease_id == disease_id)
    if district_id:
        query = query.filter(District.id == district_id)
    if local_body_id:
        query = query.filter(LocalBody.id == local_body_id)
    if ward_id:
        query = query.filter(Ward.id == ward_id)
    if start_date:
        query = query.filter(DiseaseCase.diagnosis_date >= start_date)
    if end_date:
        query = query.filter(DiseaseCase.diagnosis_date <= end_date)
    if case_status:
        query = query.filter(DiseaseCase.case_status == case_status.upper())

    filtered_cases: List[DiseaseCase] = query.all()
    total_filtered_cases = len(filtered_cases)

    # 3. Compute KPI Summary Metrics
    confirmed_count = sum(1 for c in filtered_cases if c.case_status == CaseStatus.CONFIRMED.value)
    suspected_count = sum(1 for c in filtered_cases if c.case_status == CaseStatus.SUSPECTED.value)
    recovered_count = sum(1 for c in filtered_cases if c.case_status == CaseStatus.RECOVERED.value)
    deceased_count = sum(1 for c in filtered_cases if c.case_status == CaseStatus.DECEASED.value)
    active_count = confirmed_count + suspected_count

    # Total Patients (Geographically scoped if filter active, else total in system)
    if ward_id:
        total_patients = db.query(func.count(Patient.id)).filter(Patient.ward_id == ward_id).scalar() or 0
    elif local_body_id:
        total_patients = db.query(func.count(Patient.id)).filter(Patient.local_body_id == local_body_id).scalar() or 0
    elif district_id:
        total_patients = db.query(func.count(Patient.id)).filter(Patient.district_id == district_id).scalar() or 0
    else:
        total_patients = db.query(func.count(Patient.id)).scalar() or 0

    # Ensure patient count is at least the number of distinct patients in filtered cases
    distinct_case_patients = len(set(c.patient_id for c in filtered_cases if c.patient_id))
    total_patients = max(total_patients, distinct_case_patients)

    # Active Monitoring Sessions
    active_monitoring_sessions = (
        db.query(func.count(MonitoringSession.id))
        .filter(MonitoringSession.status == SessionStatus.ACTIVE.value)
        .scalar()
        or 0
    )

    # Potential Exposure Events
    potential_exposure_events = (
        db.query(func.count(ExposureEvent.id))
        .filter(ExposureEvent.status == ExposureStatus.POTENTIAL.value)
        .scalar()
        or 0
    )

    kpi_summary = DashboardKPISummary(
        total_patients=total_patients,
        active_cases=active_count,
        confirmed_cases=confirmed_count,
        suspected_cases=suspected_count,
        recovered_cases=recovered_count,
        deceased_cases=deceased_count,
        active_monitoring_sessions=active_monitoring_sessions,
        potential_exposure_events=potential_exposure_events,
    )

    # 4. Compute Charts Data
    # 4a. Cases Over Time (Group by diagnosis date)
    date_buckets = defaultdict(lambda: {"total": 0, "confirmed": 0, "suspected": 0, "recovered": 0})
    for c in filtered_cases:
        d_str = c.diagnosis_date.isoformat() if c.diagnosis_date else datetime.date.today().isoformat()
        date_buckets[d_str]["total"] += 1
        if c.case_status == CaseStatus.CONFIRMED.value:
            date_buckets[d_str]["confirmed"] += 1
        elif c.case_status == CaseStatus.SUSPECTED.value:
            date_buckets[d_str]["suspected"] += 1
        elif c.case_status == CaseStatus.RECOVERED.value:
            date_buckets[d_str]["recovered"] += 1

    cases_over_time = [
        CaseOverTimeItem(
            date=d_key,
            total=counts["total"],
            confirmed=counts["confirmed"],
            suspected=counts["suspected"],
            recovered=counts["recovered"],
        )
        for d_key, counts in sorted(date_buckets.items(), key=lambda x: x[0])
    ]

    # 4b. Cases by Disease
    disease_counts = defaultdict(lambda: {"name": "", "code": "", "category": "", "count": 0})
    for c in filtered_cases:
        if c.disease:
            d_id = str(c.disease.id)
            disease_counts[d_id]["name"] = c.disease.name
            disease_counts[d_id]["code"] = c.disease.code
            disease_counts[d_id]["category"] = c.disease.category
            disease_counts[d_id]["count"] += 1

    cases_by_disease = [
        CaseByDiseaseItem(
            disease_id=d_id,
            disease_name=meta["name"],
            disease_code=meta["code"],
            category=meta["category"],
            count=meta["count"],
            percentage=round((meta["count"] / total_filtered_cases * 100), 1) if total_filtered_cases > 0 else 0.0,
        )
        for d_id, meta in sorted(disease_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # 4c. Cases by District
    district_counts = defaultdict(lambda: {"name": "", "count": 0})
    for c in filtered_cases:
        if c.ward and c.ward.local_body and c.ward.local_body.district:
            dist = c.ward.local_body.district
            dist_id = str(dist.id)
            district_counts[dist_id]["name"] = dist.name
            district_counts[dist_id]["count"] += 1
        elif c.patient and c.patient.district_name:
            dist_id = f"PAT-DIST-{c.patient.district_name}"
            district_counts[dist_id]["name"] = c.patient.district_name
            district_counts[dist_id]["count"] += 1

    cases_by_district = [
        CaseByDistrictItem(
            district_id=dist_id,
            district_name=meta["name"],
            count=meta["count"],
            percentage=round((meta["count"] / total_filtered_cases * 100), 1) if total_filtered_cases > 0 else 0.0,
        )
        for dist_id, meta in sorted(district_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # 4d. Cases by Local Body
    lb_counts = defaultdict(lambda: {"name": "", "district_name": "", "count": 0})
    for c in filtered_cases:
        if c.ward and c.ward.local_body:
            lb = c.ward.local_body
            lb_id = str(lb.id)
            lb_counts[lb_id]["name"] = lb.name
            lb_counts[lb_id]["district_name"] = lb.district.name if lb.district else "Kerala"
            lb_counts[lb_id]["count"] += 1
        elif c.patient and c.patient.local_body_name:
            lb_id = f"PAT-LB-{c.patient.local_body_name}"
            lb_counts[lb_id]["name"] = c.patient.local_body_name
            lb_counts[lb_id]["district_name"] = c.patient.district_name
            lb_counts[lb_id]["count"] += 1

    cases_by_local_body = [
        CaseByLocalBodyItem(
            local_body_id=lb_id,
            local_body_name=meta["name"],
            district_name=meta["district_name"],
            count=meta["count"],
            percentage=round((meta["count"] / total_filtered_cases * 100), 1) if total_filtered_cases > 0 else 0.0,
        )
        for lb_id, meta in sorted(lb_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # 4e. Cases by Ward
    ward_counts = defaultdict(lambda: {"name": "", "local_body_name": "", "count": 0})
    for c in filtered_cases:
        if c.ward:
            w = c.ward
            w_id = str(w.id)
            ward_counts[w_id]["name"] = w.name
            ward_counts[w_id]["local_body_name"] = w.local_body.name if w.local_body else ""
            ward_counts[w_id]["count"] += 1
        elif c.patient:
            w_id = f"PAT-WARD-{c.patient.ward_number}"
            ward_counts[w_id]["name"] = f"Ward {c.patient.ward_number}"
            ward_counts[w_id]["local_body_name"] = c.patient.local_body_name
            ward_counts[w_id]["count"] += 1

    cases_by_ward = [
        CaseByWardItem(
            ward_id=w_id,
            ward_name=meta["name"],
            local_body_name=meta["local_body_name"],
            count=meta["count"],
            percentage=round((meta["count"] / total_filtered_cases * 100), 1) if total_filtered_cases > 0 else 0.0,
        )
        for w_id, meta in sorted(ward_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    chart_data = DashboardChartData(
        cases_over_time=cases_over_time,
        cases_by_disease=cases_by_disease,
        cases_by_district=cases_by_district,
        cases_by_local_body=cases_by_local_body,
        cases_by_ward=cases_by_ward,
    )

    # 5. Compute Map Data
    # 5a. Discrete Map Cases
    disease_cases_map: List[DashboardMapCaseItem] = []
    heatmap_points: List[List[float]] = []

    for c in filtered_cases:
        lat = c.latitude
        lng = c.longitude

        # Fallback to ward centroid if coordinates are not on the case
        if (lat is None or lng is None) and c.ward:
            lat = c.ward.center_latitude
            lng = c.ward.center_longitude

        # Fallback to patient ward or district centroid if available
        if (lat is None or lng is None) and c.patient and c.patient.ward:
            lat = c.patient.ward.center_latitude
            lng = c.patient.ward.center_longitude

        # Do not fabricate Trivandrum coordinates for cases without spatial data
        if lat is None or lng is None:
            continue

        w_name = c.ward.name if c.ward else (f"Ward {c.patient.ward_number}" if c.patient else "Surveillance Ward")
        dist_name = (
            c.ward.local_body.district.name
            if (c.ward and c.ward.local_body and c.ward.local_body.district)
            else (c.patient.district_name if c.patient else "Kerala")
        )

        disease_cases_map.append(
            DashboardMapCaseItem(
                id=str(c.id),
                patient_pseudo_id=c.patient.pseudo_id if c.patient else "ANON",
                disease_name=c.disease.name if c.disease else "Under Investigation",
                case_status=c.case_status,
                severity=c.severity,
                latitude=round(float(lat), 6),
                longitude=round(float(lng), 6),
                ward_name=w_name,
                district_name=dist_name,
                diagnosis_date=c.diagnosis_date.isoformat() if c.diagnosis_date else datetime.date.today().isoformat(),
            )
        )

        # Build Heatmap Points: [lat, lng, weight]
        # Active cases have higher weight
        intensity = 1.0 if c.case_status == CaseStatus.CONFIRMED.value else (
            0.7 if c.case_status == CaseStatus.SUSPECTED.value else 0.3
        )
        heatmap_points.append([round(float(lat), 6), round(float(lng), 6), intensity])

    # 5b. District Visualizations
    all_districts = db.query(District).all()
    district_map_items: List[DashboardDistrictMapItem] = []
    for d in all_districts:
        d_cases = [c for c in filtered_cases if (c.ward and c.ward.local_body and c.ward.local_body.district_id == d.id)]
        d_active = sum(1 for c in d_cases if c.case_status in (CaseStatus.CONFIRMED.value, CaseStatus.SUSPECTED.value))
        district_map_items.append(
            DashboardDistrictMapItem(
                id=str(d.id),
                name=d.name,
                latitude=float(d.center_latitude) if d.center_latitude is not None else 0.0,
                longitude=float(d.center_longitude) if d.center_longitude is not None else 0.0,
                case_count=len(d_cases),
                active_count=d_active,
            )
        )

    map_data = DashboardMapData(
        disease_cases=disease_cases_map,
        heatmap_points=heatmap_points,
        districts=district_map_items,
    )

    # 6. Active Filters Echo
    active_filters = DashboardActiveFilters(
        disease_id=str(disease_id) if disease_id else None,
        district_id=str(district_id) if district_id else None,
        local_body_id=str(local_body_id) if local_body_id else None,
        ward_id=str(ward_id) if ward_id else None,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        case_status=case_status,
    )

    return SurveillanceDashboardResponse(
        kpi_summary=kpi_summary,
        charts=chart_data,
        map_data=map_data,
        active_filters=active_filters,
        generated_at=datetime.datetime.utcnow().isoformat(),
        disclaimer=(
            "DECISION SUPPORT ONLY: High-level disease surveillance metrics computed dynamically "
            "from registered case records and authorized telemetry."
        ),
    )
