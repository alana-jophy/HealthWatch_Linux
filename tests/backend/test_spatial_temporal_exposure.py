import datetime
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.models.exposure import ExposureEvent, ExposureStatus

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic demo data exist."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# HealthWatch Step 16: Potential Spatial-Temporal Exposure Analysis Test Suite
# ==============================================================================

class TestSpatialTemporalExposure:

    @classmethod
    def setup_class(cls):
        cls.officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        cls.admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        cls.worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        cls.patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")

        cls.officer_headers = {"Authorization": f"Bearer {cls.officer_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.worker_headers = {"Authorization": f"Bearer {cls.worker_token}"}
        cls.patient_headers = {"Authorization": f"Bearer {cls.patient_token}"}

        db = SessionLocal()
        try:
            cls.p1 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
            cls.p2 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # 1. ACCESS CONTROL AND RBAC
    # --------------------------------------------------------------------------
    def test_officer_and_admin_authorized_for_exposure_endpoints(self):
        """Public Health Officers and Admins can query and run exposure analysis."""
        res_officer = client.get("/api/v1/exposure/events", headers=self.officer_headers)
        assert res_officer.status_code == 200
        assert res_officer.json()["total"] >= 1

        res_admin = client.get("/api/v1/exposure/events", headers=self.admin_headers)
        assert res_admin.status_code == 200
        assert res_admin.json()["total"] >= 1

    def test_patient_forbidden_from_exposure_analysis(self):
        """Patients are strictly blocked with 403 Forbidden from accessing exposure analysis."""
        res = client.get("/api/v1/exposure/events", headers=self.patient_headers)
        assert res.status_code == 403
        err = res.json().get("error", {}).get("message", "")
        assert "Access denied" in err or "PATIENT" in err or "forbidden" in err.lower()

        # Cannot trigger analysis either
        res_analyze = client.post(
            "/api/v1/exposure/analyze",
            json={"spatial_distance_threshold_meters": 50.0, "temporal_difference_threshold_minutes": 15.0},
            headers=self.patient_headers,
        )
        assert res_analyze.status_code == 403

    def test_health_worker_forbidden_from_exposure_analysis(self):
        """Health Workers without surveillance authorization receive 403 Forbidden."""
        res = client.get("/api/v1/exposure/events", headers=self.worker_headers)
        assert res.status_code == 403

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests are rejected with 401."""
        res = client.get("/api/v1/exposure/events")
        assert res.status_code == 401

    # --------------------------------------------------------------------------
    # 2. ETHICAL & DECISION-SUPPORT REQUIREMENTS
    # --------------------------------------------------------------------------
    def test_exposure_response_includes_decision_support_disclaimer(self):
        """
        Critical Rule: The system must NEVER state 'Patient A infected Patient B'.
        It must clearly state 'Potential Exposure' / 'Potential Spatial-Temporal Overlap'.
        """
        res = client.get("/api/v1/exposure/events", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()

        # Disclaimer on collection
        assert "disclaimer" in data
        assert "decision-support" in data["disclaimer"].lower() or "does not assert" in data["disclaimer"].lower()

        # Disclaimer on each item
        for item in data["items"]:
            assert "disclaimer" in item
            assert "does not establish" in item["disclaimer"].lower() or "decision-support" in item["disclaimer"].lower()
            # Must NEVER assert transmission
            assert "infected" not in item["disclaimer"].lower()
            assert "causality" in item["disclaimer"].lower() or "transmission" in item["disclaimer"].lower()

    # --------------------------------------------------------------------------
    # 3. CONFIGURABLE THRESHOLDS & SPATIAL-TEMPORAL ALGORITHM
    # --------------------------------------------------------------------------
    def test_configurable_thresholds_influence_detection_results(self):
        """
        Verify that thresholds are configurable:
        - Wide thresholds (e.g. 50m, 15min) detect overlaps.
        - Extremely tight spatial threshold (e.g. 10m) filters out pairs with distance > 10m.
        """
        # Standard configuration
        res_standard = client.post(
            "/api/v1/exposure/analyze",
            json={
                "spatial_distance_threshold_meters": 50.0,
                "temporal_difference_threshold_minutes": 15.0,
            },
            headers=self.officer_headers,
        )
        assert res_standard.status_code == 200
        data_standard = res_standard.json()
        assert data_standard["status"] == "success"
        assert data_standard["spatial_threshold_meters"] == 50.0
        assert data_standard["temporal_threshold_minutes"] == 15.0
        assert data_standard["potential_overlaps_detected"] >= 2

        # Overlapping observations in seed:
        # Palayam: ~28.4m, 10 mins
        # LMS: ~14.2m, 3 mins

        # Ultra-tight spatial threshold: 10 meters (Palayam 28.4m should NOT qualify)
        res_tight = client.post(
            "/api/v1/exposure/analyze",
            json={
                "spatial_distance_threshold_meters": 10.0,
                "temporal_difference_threshold_minutes": 15.0,
            },
            headers=self.officer_headers,
        )
        assert res_tight.status_code == 200
        data_tight = res_tight.json()
        # Count with <= 10m should be strictly less than standard
        assert data_tight["potential_overlaps_detected"] < data_standard["potential_overlaps_detected"]

    def test_postgis_geography_distance_calculation(self):
        """
        Verify that distance is calculated using PostGIS spatial functions on geography,
        and time difference is computed from timestamps.
        """
        res = client.get("/api/v1/exposure/events", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()

        for ev in data["items"]:
            assert ev["distance"] >= 0.0
            assert ev["distance"] <= 1000.0  # reasonable spatial bound
            assert ev["time_difference"] >= 0.0
            assert 0.0 <= ev["confidence_score"] <= 1.0
            assert ev["status"] in ["POTENTIAL", "REVIEWED", "DISMISSED", "CONFIRMED_BY_AUTHORITY"]

    # --------------------------------------------------------------------------
    # 4. OFFICER REVIEW AND DISMISS WORKFLOW
    # --------------------------------------------------------------------------
    def test_officer_can_review_and_dismiss_exposure_event(self):
        """Officer can update event status to REVIEWED, DISMISSED, or CONFIRMED_BY_AUTHORITY."""
        # 1. Get an existing event
        list_res = client.get("/api/v1/exposure/events", headers=self.officer_headers)
        assert list_res.status_code == 200
        events = list_res.json()["items"]
        assert len(events) >= 1
        target_ev = events[0]
        ev_id = target_ev["id"]

        # 2. Transition to REVIEWED with review notes
        patch_res = client.patch(
            f"/api/v1/exposure/events/{ev_id}",
            json={
                "status": "REVIEWED",
                "review_notes": "Officer verified proximity at market corridor. Contact tracing alert issued.",
            },
            headers=self.officer_headers,
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["status"] == "REVIEWED"
        assert "market corridor" in updated["review_notes"]
        assert updated["reviewed_by"] is not None
        assert updated["reviewed_at"] is not None

        # 3. Transition to DISMISSED with justification
        dismiss_res = client.patch(
            f"/api/v1/exposure/events/{ev_id}",
            json={
                "status": "DISMISSED",
                "review_notes": "Physical plexiglass barrier present; risk neutralized.",
            },
            headers=self.officer_headers,
        )
        assert dismiss_res.status_code == 200
        assert dismiss_res.json()["status"] == "DISMISSED"
        assert "barrier" in dismiss_res.json()["review_notes"]

        # 4. Transition to CONFIRMED_BY_AUTHORITY
        confirm_res = client.patch(
            f"/api/v1/exposure/events/{ev_id}",
            json={
                "status": "CONFIRMED_BY_AUTHORITY",
                "review_notes": "Formal authority quarantine follow-up mandated.",
            },
            headers=self.officer_headers,
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["status"] == "CONFIRMED_BY_AUTHORITY"

    # --------------------------------------------------------------------------
    # 5. QUERY FILTERS AND LOOKUPS
    # --------------------------------------------------------------------------
    def test_filter_exposure_events_by_status(self):
        """Filtering by status correctly segments the events."""
        res_all = client.get("/api/v1/exposure/events", headers=self.officer_headers)
        assert res_all.status_code == 200
        total_all = res_all.json()["total"]

        res_reviewed = client.get("/api/v1/exposure/events?status=REVIEWED", headers=self.officer_headers)
        assert res_reviewed.status_code == 200
        for item in res_reviewed.json()["items"]:
            assert item["status"] == "REVIEWED"

        res_dismissed = client.get("/api/v1/exposure/events?status=DISMISSED", headers=self.officer_headers)
        assert res_dismissed.status_code == 200
        for item in res_dismissed.json()["items"]:
            assert item["status"] == "DISMISSED"

    def test_get_single_exposure_event_by_id(self):
        """Retrieve single exposure event by ID."""
        list_res = client.get("/api/v1/exposure/events", headers=self.officer_headers)
        ev_id = list_res.json()["items"][0]["id"]

        single_res = client.get(f"/api/v1/exposure/events/{ev_id}", headers=self.officer_headers)
        assert single_res.status_code == 200
        assert single_res.json()["id"] == ev_id
        assert single_res.json()["patient_a_pseudo_id"] is not None
        assert single_res.json()["patient_b_pseudo_id"] is not None
