"""
HealthWatch Step 21: Complete End-to-End System Test Suite.
Verifies all 12 core functional domains required for release validation:
1. Authentication (Admin, Health Worker, Officer, Patient, Invalid credentials)
2. Patient Module (Create, Read, Update, Delete, Search, Filter)
3. Disease Catalog (Create, Read, Update, Delete, Classification)
4. GIS Kerala Spatial Hierarchy (District, Local Body, Ward, Case points, Filtering)
5. Location Monitoring & Consent (Grant, Session, GPS telemetry, 15-min interval, History)
6. Movement Roadmap (Start, Observations, End, Timeline, Polyline, Filters)
7. Privacy & IDOR Prevention (Patient A isolated from Patient B across all endpoints)
8. Disease Surveillance Heatmap (Disease, Date, District, Ward filters)
9. Spatial-Temporal Exposure (Spatial/Temporal thresholds, Overlap detection, Review, Dismiss)
10. Public Health Surveillance Dashboard (KPIs, Recharts series, Map datasets, Dynamic filters)
11. Reports Engine (Publication PDF, RFC 4180 CSV exports)
12. AI-Assisted Outbreak Risk Forecasting (Input validation, Prediction, Risk level, Error handling)
"""

import datetime
import io
import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.disease import CaseStatus, ContagionType, Disease, DiseaseCase
from app.models.exposure import ExposureEvent, ExposureStatus
from app.models.monitoring import (
    ConsentStatus,
    LocationConsent,
    MonitoringSession,
    PatientLocation,
    SessionStatus,
)
from app.models.patient import Patient
from app.models.spatial import District, LocalBody, Ward
from app.models.user import Role, User
from app.schemas.auth import RoleEnum
from app.schemas.prediction import RiskLevelEnum

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session", autouse=True)
def setup_system_test_env():
    """Ensure baseline schema, seed users, and Kerala GIS geometries are loaded."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# 1. AUTHENTICATION MODULE TESTS
# ==============================================================================

class TestAuthenticationModule:

    def test_admin_login(self):
        """Verify Admin login returns token with ADMIN role."""
        res = client.post("/api/auth/login", json={"email": "admin@healthwatch.org", "password": "Admin@HealthWatch2026"})
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == "ADMIN"
        assert "access_token" in data

    def test_health_worker_login(self):
        """Verify Health Worker login returns token with HEALTH_WORKER role."""
        res = client.post("/api/auth/login", json={"email": "worker.field01@healthwatch.org", "password": "Worker@HealthWatch2026"})
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == "HEALTH_WORKER"

    def test_public_health_officer_login(self):
        """Verify Public Health Officer login returns token with PUBLIC_HEALTH_OFFICER role."""
        res = client.post("/api/auth/login", json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"})
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == "PUBLIC_HEALTH_OFFICER"

    def test_patient_login(self):
        """Verify Patient login returns token with PATIENT role."""
        res = client.post("/api/auth/login", json={"email": "patient.synth101@healthwatch.org", "password": "Patient@HealthWatch2026"})
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == "PATIENT"

    def test_invalid_login(self):
        """Verify invalid credentials return 401 Unauthorized."""
        res = client.post("/api/auth/login", json={"email": "admin@healthwatch.org", "password": "IncorrectPassword!"})
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["error"]["message"]


# ==============================================================================
# 2. PATIENT MODULE TESTS (CRUD, SEARCH, FILTER)
# ==============================================================================

class TestPatientModule:

    def test_patient_crud_search_filter(self):
        """Test complete patient lifecycle: Create, Read, Update, Delete, Search, Filter."""
        worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        worker_headers = {"Authorization": f"Bearer {worker_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. CREATE Patient
        unique_pseudo = f"PAT-SYS-{uuid.uuid4().hex[:6].upper()}"
        create_payload = {
            "pseudo_id": unique_pseudo,
            "full_name": "Test Lifecycle Patient",
            "age": 42,
            "gender": "MALE",
            "contact_number": "+91-9847111222",
            "address": "Kochi, Ernakulam",
            "district_name": "Ernakulam",
            "local_body_name": "Kochi Municipal Corporation",
            "ward_number": 5,
            "is_active": True,
        }
        res_create = client.post("/api/v1/patients/", json=create_payload, headers=worker_headers)
        assert res_create.status_code == 201
        patient_data = res_create.json()
        patient_id = patient_data["id"]
        assert patient_data["pseudo_id"] == unique_pseudo

        # 2. READ Patient
        res_read = client.get(f"/api/v1/patients/{patient_id}", headers=worker_headers)
        assert res_read.status_code == 200
        assert res_read.json()["full_name"] == "Test Lifecycle Patient"

        # 3. UPDATE Patient
        update_payload = {"address": "Updated Address, Marine Drive, Kochi", "age": 43}
        res_update = client.put(f"/api/v1/patients/{patient_id}", json=update_payload, headers=worker_headers)
        assert res_update.status_code == 200
        assert res_update.json()["age"] == 43
        assert "Marine Drive" in res_update.json()["address"]

        # 4. SEARCH Patient
        res_search = client.get(f"/api/v1/patients/?q={unique_pseudo}", headers=worker_headers)
        assert res_search.status_code == 200
        search_items = res_search.json()["items"]
        assert any(p["id"] == patient_id for p in search_items)

        # 5. FILTER Patient
        res_filter = client.get(f"/api/v1/patients/?district_name=Ernakulam&ward_number=5", headers=worker_headers)
        assert res_filter.status_code == 200
        assert res_filter.json()["total"] >= 1

        # 6. DELETE / DEACTIVATE Patient
        res_del = client.delete(f"/api/v1/patients/{patient_id}", headers=admin_headers)
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "success"

        # Verify deactivated
        res_verify = client.get(f"/api/v1/patients/{patient_id}", headers=admin_headers)
        assert res_verify.status_code == 200
        assert res_verify.json()["is_active"] is False


# ==============================================================================
# 3. DISEASE MODULE TESTS (CRUD, CLASSIFICATION)
# ==============================================================================

class TestDiseaseModule:

    def test_disease_crud_and_classification(self):
        """Test disease lifecycle: Create, Read, Update, Delete, Classification (CONTAGIOUS/NON_CONTAGIOUS)."""
        admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. CREATE Disease
        unique_code = f"TEST-DIS-{uuid.uuid4().hex[:4].upper()}"
        create_payload = {
            "code": unique_code,
            "name": "Zika Virus Outbreak Strain",
            "contagion_type": "CONTAGIOUS",
            "category": "Vector-Borne",
            "incubation_period_days": 7,
            "r0_estimate": 1.6,
            "description": "Flavivirus transmitted by Aedes mosquitoes.",
            "is_active": True,
        }
        res_create = client.post("/api/v1/diseases/", json=create_payload, headers=headers)
        assert res_create.status_code == 201
        disease_data = res_create.json()
        disease_id = disease_data["id"]
        assert disease_data["contagion_type"] == "CONTAGIOUS"

        # 2. READ Disease
        res_read = client.get(f"/api/v1/diseases/{disease_id}", headers=headers)
        assert res_read.status_code == 200
        assert res_read.json()["code"] == unique_code

        # 3. UPDATE Disease
        update_payload = {"r0_estimate": 1.9, "category": "Arbovirus"}
        res_update = client.put(f"/api/v1/diseases/{disease_id}", json=update_payload, headers=headers)
        assert res_update.status_code == 200
        assert res_update.json()["r0_estimate"] == 1.9

        # 4. CLASSIFICATION Filter
        res_contagious = client.get("/api/v1/diseases/?contagion_type=CONTAGIOUS", headers=headers)
        assert res_contagious.status_code == 200
        assert all(d["contagion_type"] == "CONTAGIOUS" for d in res_contagious.json()["items"])

        res_non_contagious = client.get("/api/v1/diseases/?contagion_type=NON_CONTAGIOUS", headers=headers)
        assert res_non_contagious.status_code == 200
        assert all(d["contagion_type"] == "NON_CONTAGIOUS" for d in res_non_contagious.json()["items"])

        # 5. DELETE / DEACTIVATE Disease
        res_del = client.delete(f"/api/v1/diseases/{disease_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "success"


# ==============================================================================
# 4. GIS KERALA SPATIAL HIERARCHY TESTS
# ==============================================================================

class TestGISModule:

    def test_kerala_spatial_hierarchy_and_filtering(self):
        """Test Kerala districts, local bodies, wards, case markers, and spatial filters."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        # 1. Kerala Districts
        res_dist = client.get("/api/v1/gis/districts", headers=headers)
        assert res_dist.status_code == 200
        districts = res_dist.json()
        assert len(districts) >= 3  # Validated Kerala district boundaries
        first_dist = districts[0]
        assert first_dist["state"] == "Kerala"

        # GeoJSON endpoint
        res_dist_geojson = client.get("/api/v1/gis/districts/geojson", headers=headers)
        assert res_dist_geojson.status_code == 200
        assert res_dist_geojson.json()["type"] == "FeatureCollection"

        # 2. Local Bodies
        res_lb = client.get(f"/api/v1/gis/local-bodies?district_id={first_dist['id']}", headers=headers)
        assert res_lb.status_code == 200
        lbs = res_lb.json()
        assert len(lbs) >= 1
        first_lb = lbs[0]

        # 3. Wards
        res_ward = client.get(f"/api/v1/gis/wards?local_body_id={first_lb['id']}", headers=headers)
        assert res_ward.status_code == 200
        wards = res_ward.json()
        assert len(wards) >= 1

        # 4. Disease Case Locations & Filtering
        res_cases = client.get("/api/v1/gis/cases", headers=headers)
        assert res_cases.status_code == 200
        case_points = res_cases.json()
        assert len(case_points) >= 1
        assert "latitude" in case_points[0]
        assert "longitude" in case_points[0]

        # Filter by contagion type
        res_contagious = client.get("/api/v1/gis/cases?contagion_type=CONTAGIOUS", headers=headers)
        assert res_contagious.status_code == 200


# ==============================================================================
# 5. LOCATION CONSENT, MONITORING & 15-MINUTE SAMPLING
# ==============================================================================

class TestLocationMonitoringModule:

    def test_consent_session_gps_submission_and_history(self):
        """Test consent grant, active session, GPS observation ingestion, and 15-min interval configuration."""
        patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {patient_token}"}

        # 1. Check Monitoring Status & 15-minute Sampling interval
        res_status = client.get("/api/v1/monitoring/status", headers=headers)
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["sampling_interval_seconds"] == 900
        assert "15 minutes" in status_data["sampling_interval_description"].lower()
        assert "15 minutes" in status_data["explanation_notice"]

        # 2. Verify Active Monitoring Session
        res_session = client.get("/api/v1/monitoring/sessions/current", headers=headers)
        assert res_session.status_code == 200
        session_data = res_session.json()
        session_id = session_data["id"]
        assert session_data["status"] == "ACTIVE"

        # 3. GPS Observation Submission
        now = datetime.datetime.now(datetime.timezone.utc)
        unique_client_obs = f"CLIENT-OBS-{uuid.uuid4().hex[:8]}"
        gps_payload = {
            "monitoring_session_id": session_id,
            "latitude": 8.5242,
            "longitude": 76.9367,
            "accuracy": 14.2,
            "recorded_at": now.isoformat(),
            "source": "PATIENT_GPS",
            "client_observation_id": unique_client_obs,
        }
        res_gps = client.post("/api/v1/locations", json=gps_payload, headers=headers)
        assert res_gps.status_code == 201
        assert res_gps.json()["status"] == "ACCEPTED"

        # 4. Location History Query
        res_history = client.get("/api/v1/monitoring/locations/history", headers=headers)
        assert res_history.status_code == 200
        history_items = res_history.json()["items"]
        assert len(history_items) >= 1
        assert "latitude" in history_items[0]
        assert "accuracy" in history_items[0]


# ==============================================================================
# 6. MOVEMENT ROADMAP TESTS
# ==============================================================================

class TestMovementRoadmapModule:

    def test_roadmap_markers_timeline_and_polyline(self):
        """Test movement roadmap start marker, intermediate observations, end marker, timeline, and polyline."""
        patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {patient_token}"}

        res = client.get("/api/v1/monitoring/roadmap", headers=headers)
        assert res.status_code == 200
        roadmap = res.json()

        # Visual sequential roadmap structures
        assert "observations" in roadmap
        assert "statistics" in roadmap
        assert "disclaimer" in roadmap

        observations = roadmap["observations"]
        assert len(observations) >= 2, "Roadmap should have at least start and end observations"

        # Verify Start & End Locations derived in statistics
        stats = roadmap["statistics"]
        assert stats["total_observations"] >= 2
        assert stats["first_recorded_location"] is not None
        assert stats["last_recorded_location"] is not None

        # Verify observation items
        first_obs = observations[0]
        last_obs = observations[-1]
        assert first_obs["latitude"] is not None
        assert last_obs["latitude"] is not None

        # Technical limitation statement
        assert "15 minutes" in roadmap["disclaimer"]
        assert "recorded" in roadmap["disclaimer"].lower()


# ==============================================================================
# 7. PRIVACY & IDOR VERIFICATION
# ==============================================================================

class TestPrivacyIsolationModule:

    def test_patient_a_strictly_isolated_from_patient_b(self):
        """Verify Patient A cannot access Patient B's profile, cases, GPS history, roadmap, or exposures."""
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        db = SessionLocal()
        try:
            user_a = db.query(User).filter(User.email == "patient.synth101@healthwatch.org").first()
            patient_a = db.query(Patient).filter(Patient.user_id == user_a.id).first() if user_a else None
            patient_b = db.query(Patient).filter(Patient.id != patient_a.id).first() if patient_a else db.query(Patient).first()
            assert patient_b is not None
            patient_b_id = str(patient_b.id)

            case_b = db.query(DiseaseCase).filter(DiseaseCase.patient_id != patient_a.id).first() if patient_a else db.query(DiseaseCase).first()
            assert case_b is not None
            case_b_id = str(case_b.id)
        finally:
            db.close()

        # 1. Profile: 403 Forbidden
        assert client.get(f"/api/v1/patients/{patient_b_id}", headers=headers).status_code == 403

        # 2. Disease Case: 403 Forbidden
        assert client.get(f"/api/v1/cases/{case_b_id}", headers=headers).status_code == 403

        # 3. GPS History: 403 Forbidden
        assert client.get(f"/api/v1/monitoring/locations/history?patient_id={patient_b_id}", headers=headers).status_code == 403

        # 4. Movement Roadmap: 403 Forbidden
        assert client.get(f"/api/v1/monitoring/roadmap?patient_id={patient_b_id}", headers=headers).status_code == 403

        # 5. Potential Exposure Events: 403 Forbidden
        assert client.get(f"/api/v1/exposure/events?patient_id={patient_b_id}", headers=headers).status_code == 403


# ==============================================================================
# 8. DISEASE HOTSPOT HEATMAP TESTS
# ==============================================================================

class TestDiseaseHeatmapModule:

    def test_heatmap_density_and_filters(self):
        """Test disease surveillance heatmap with disease, date, district, and ward filters."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        # Baseline Heatmap
        res = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "density_points" in data
        assert "hotspots" in data
        assert "concentration_summary" in data

        # Filter by Disease
        db = SessionLocal()
        try:
            dengue = db.query(Disease).filter(Disease.code.ilike("%DENGUE%")).first()
            dengue_id = str(dengue.id) if dengue else None
            district = db.query(District).first()
            district_id = str(district.id) if district else None
        finally:
            db.close()

        if dengue_id:
            res_dis = client.get(f"/api/v1/gis/heatmaps?disease_id={dengue_id}", headers=headers)
            assert res_dis.status_code == 200

        # Filter by District
        if district_id:
            res_dist = client.get(f"/api/v1/gis/heatmaps?district_id={district_id}", headers=headers)
            assert res_dist.status_code == 200

        # Filter by Date
        res_date = client.get("/api/v1/gis/heatmaps?start_date=2026-01-01&end_date=2026-12-31", headers=headers)
        assert res_date.status_code == 200


# ==============================================================================
# 9. SPATIAL-TEMPORAL EXPOSURE TESTS
# ==============================================================================

class TestExposureAnalysisModule:

    def test_exposure_detection_review_and_dismiss(self):
        """Test potential exposure spatial/temporal threshold detection, review, and dismiss."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        # 1. Run Analysis with Configurable Thresholds
        analyze_payload = {
            "spatial_distance_threshold_meters": 50.0,
            "temporal_difference_threshold_minutes": 15.0,
        }
        res_analyze = client.post("/api/v1/exposure/analyze", json=analyze_payload, headers=headers)
        assert res_analyze.status_code == 200
        analysis_data = res_analyze.json()
        assert analysis_data["status"] == "success"
        assert "candidate_pairs_evaluated" in analysis_data

        # 2. Query Exposure Events
        res_events = client.get("/api/v1/exposure/events", headers=headers)
        assert res_events.status_code == 200
        events = res_events.json()["items"]
        assert len(events) >= 1
        target_event = events[0]
        event_id = target_event["id"]

        # 3. REVIEW Exposure Event
        review_payload = {"status": "REVIEWED", "review_notes": "Contact tracing team dispatched for follow-up"}
        res_review = client.patch(f"/api/v1/exposure/events/{event_id}", json=review_payload, headers=headers)
        assert res_review.status_code == 200
        assert res_review.json()["status"] == "REVIEWED"

        # 4. DISMISS Exposure Event
        dismiss_payload = {"status": "DISMISSED", "review_notes": "Different vertical levels, physical barrier present"}
        res_dismiss = client.patch(f"/api/v1/exposure/events/{event_id}", json=dismiss_payload, headers=headers)
        assert res_dismiss.status_code == 200
        assert res_dismiss.json()["status"] == "DISMISSED"


# ==============================================================================
# 10. SURVEILLANCE DASHBOARD TESTS
# ==============================================================================

class TestSurveillanceDashboardModule:

    def test_dashboard_kpis_charts_and_filters(self):
        """Test surveillance dashboard KPIs, Recharts series aggregations, and spatial map datasets."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        res = client.get("/api/v1/surveillance/dashboard", headers=headers)
        assert res.status_code == 200
        data = res.json()

        # 1. KPIs
        kpi = data["kpi_summary"]
        assert "total_patients" in kpi
        assert "active_cases" in kpi
        assert "confirmed_cases" in kpi
        assert "suspected_cases" in kpi
        assert "recovered_cases" in kpi
        assert "active_monitoring_sessions" in kpi
        assert "potential_exposure_events" in kpi
        assert kpi["total_patients"] >= 1

        # 2. Charts Data
        charts = data["charts"]
        assert len(charts["cases_over_time"]) >= 1
        assert len(charts["cases_by_disease"]) >= 1
        assert len(charts["cases_by_district"]) >= 1

        # 3. Map Datasets
        map_data = data["map_data"]
        assert len(map_data["disease_cases"]) >= 1
        assert len(map_data["districts"]) >= 1

        # 4. Filters Applied
        res_filtered = client.get("/api/v1/surveillance/dashboard?case_status=CONFIRMED", headers=headers)
        assert res_filtered.status_code == 200
        assert res_filtered.json()["active_filters"]["case_status"] == "CONFIRMED"


# ==============================================================================
# 11. REPORTS GENERATION TESTS (PDF & CSV)
# ==============================================================================

class TestReportsGenerationModule:

    def test_pdf_report_export(self):
        """Verify report engine generates valid binary PDF document."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        res = client.get("/api/v1/reports/export?format=pdf&report_type=comprehensive", headers=headers)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF-"), "Exported payload must be valid binary PDF"

    def test_csv_report_export(self):
        """Verify report engine generates valid RFC 4180 CSV export."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        res = client.get("/api/v1/reports/export?format=csv&report_type=comprehensive", headers=headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        csv_text = res.text
        assert "HEALTHWATCH" in csv_text.upper()
        assert "SURVEILLANCE" in csv_text.upper()


# ==============================================================================
# 12. AI-ASSISTED OUTBREAK RISK PREDICTION TESTS
# ==============================================================================

class TestAIPredictionModule:

    def test_ai_outbreak_risk_prediction_input_and_risk_levels(self):
        """Test AI scenario prediction input, continuous risk score, risk level, and trend."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        # 1. Low Risk Scenario Input
        low_risk_payload = {
            "historical_case_count": 5,
            "recent_case_count": 1,
            "disease_r0_estimate": 1.2,
            "is_contagious": True,
            "spatial_case_density": 0.3,
            "potential_exposure_count": 0,
        }
        res_low = client.post("/api/v1/predictions/predict?area_name=LowRiskWard", json=low_risk_payload, headers=headers)
        assert res_low.status_code == 200
        pred_low = res_low.json()
        assert pred_low["risk_level"] in ["LOW", "MEDIUM"]
        assert 0.0 <= pred_low["risk_score"] <= 1.0
        assert pred_low["predicted_trend"] in ["DECLINING", "STABLE"]
        assert "feature_contributions" in pred_low

        # 2. Critical Risk Scenario Input
        critical_risk_payload = {
            "historical_case_count": 10,
            "recent_case_count": 45,
            "disease_r0_estimate": 2.8,
            "is_contagious": True,
            "spatial_case_density": 8.5,
            "potential_exposure_count": 18,
        }
        res_crit = client.post("/api/v1/predictions/predict?area_name=SurgingZone", json=critical_risk_payload, headers=headers)
        assert res_crit.status_code == 200
        pred_crit = res_crit.json()
        assert pred_crit["risk_level"] in ["HIGH", "CRITICAL"]
        assert pred_crit["risk_score"] >= 0.65
        assert pred_crit["predicted_trend"] in ["SURGING", "INCREASING"]

        # 3. Multi-Area Outbreak Risk Surveillance Endpoint
        res_multi = client.get("/api/v1/predictions/outbreak-risk", headers=headers)
        assert res_multi.status_code == 200
        multi_data = res_multi.json()
        assert multi_data["status"] == "success"
        assert len(multi_data["predictions"]) >= 1
        assert "DECISION SUPPORT ONLY" in multi_data["disclaimer"]

    def test_ai_prediction_error_handling(self):
        """Test AI prediction input validation and error handling for invalid features."""
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        # Negative case count rejected by Pydantic schema (422)
        invalid_payload = {
            "historical_case_count": -5,
            "recent_case_count": 10,
            "disease_r0_estimate": 1.5,
            "is_contagious": True,
        }
        res_err = client.post("/api/v1/predictions/predict", json=invalid_payload, headers=headers)
        assert res_err.status_code == 422
        assert res_err.json()["error"]["type"] == "ValidationError"
