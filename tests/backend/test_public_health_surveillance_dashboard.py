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
from app.models.disease import Disease, DiseaseCase
from app.models.spatial import District, LocalBody, Ward
from app.models.patient import Patient

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
# HealthWatch Step 17: Public Health Surveillance Dashboard Test Suite
# ==============================================================================

class TestPublicHealthSurveillanceDashboard:

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
            cls.dengue = db.query(Disease).filter(Disease.code == "DENGUE-01").first()
            cls.covid = db.query(Disease).filter(Disease.code == "COVID-19").first()
            cls.tvm_district = db.query(District).filter(District.code == "KL-TVM").first()
            cls.ward_palayam = db.query(Ward).filter(Ward.name == "Palayam Ward").first()
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # 1. ACCESS CONTROL AND RBAC
    # --------------------------------------------------------------------------
    def test_officer_and_admin_authorized_for_surveillance_dashboard(self):
        """Public Health Officers and Admins have full access to surveillance aggregations."""
        res_officer = client.get("/api/v1/surveillance/dashboard", headers=self.officer_headers)
        assert res_officer.status_code == 200, f"Officer rejected: {res_officer.text}"
        data = res_officer.json()
        assert "kpi_summary" in data
        assert "charts" in data
        assert "map_data" in data

        res_admin = client.get("/api/v1/surveillance/dashboard", headers=self.admin_headers)
        assert res_admin.status_code == 200, f"Admin rejected: {res_admin.text}"

    def test_patient_forbidden_from_surveillance_dashboard(self):
        """Patients are forbidden from accessing high-level surveillance command center."""
        res = client.get("/api/v1/surveillance/dashboard", headers=self.patient_headers)
        assert res.status_code == 403
        msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
        assert "Access denied" in msg

    def test_health_worker_forbidden_from_surveillance_dashboard(self):
        """Field health workers are restricted to assigned patient operations."""
        res = client.get("/api/v1/surveillance/dashboard", headers=self.worker_headers)
        assert res.status_code == 403
        msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
        assert "Access denied" in msg

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated calls are denied with HTTP 401."""
        res = client.get("/api/v1/surveillance/dashboard")
        assert res.status_code == 401

    # --------------------------------------------------------------------------
    # 2. SEVEN KPI SUMMARY METRICS
    # --------------------------------------------------------------------------
    def test_all_seven_kpi_metrics_returned(self):
        """Dashboard must dynamically compute all 7 required KPI card metrics."""
        res = client.get("/api/v1/surveillance/dashboard", headers=self.officer_headers)
        assert res.status_code == 200
        kpi = res.json()["kpi_summary"]

        # Verify all 7 required KPI fields exist and are non-null integers
        assert isinstance(kpi["total_patients"], int) and kpi["total_patients"] > 0
        assert isinstance(kpi["active_cases"], int) and kpi["active_cases"] > 0
        assert isinstance(kpi["confirmed_cases"], int) and kpi["confirmed_cases"] > 0
        assert isinstance(kpi["suspected_cases"], int) and kpi["suspected_cases"] >= 0
        assert isinstance(kpi["recovered_cases"], int) and kpi["recovered_cases"] >= 0
        assert isinstance(kpi["active_monitoring_sessions"], int) and kpi["active_monitoring_sessions"] >= 0
        assert isinstance(kpi["potential_exposure_events"], int) and kpi["potential_exposure_events"] >= 0

        # Mathematical consistency: Active = Confirmed + Suspected
        assert kpi["active_cases"] == kpi["confirmed_cases"] + kpi["suspected_cases"]

    # --------------------------------------------------------------------------
    # 3. FIVE RECHARTS DATASETS
    # --------------------------------------------------------------------------
    def test_all_five_chart_datasets_populated(self):
        """Dashboard charts must include all 5 required categorical and time-series datasets."""
        res = client.get("/api/v1/surveillance/dashboard", headers=self.officer_headers)
        assert res.status_code == 200
        charts = res.json()["charts"]

        # 1. Cases over time
        assert "cases_over_time" in charts
        assert len(charts["cases_over_time"]) > 0
        sample_time = charts["cases_over_time"][0]
        assert "date" in sample_time
        assert "total" in sample_time
        assert "confirmed" in sample_time

        # 2. Cases by disease
        assert "cases_by_disease" in charts
        assert len(charts["cases_by_disease"]) > 0
        sample_disease = charts["cases_by_disease"][0]
        assert "disease_name" in sample_disease
        assert "count" in sample_disease
        assert "percentage" in sample_disease

        # 3. Cases by district
        assert "cases_by_district" in charts
        assert len(charts["cases_by_district"]) > 0
        sample_dist = charts["cases_by_district"][0]
        assert "district_name" in sample_dist
        assert "count" in sample_dist

        # 4. Cases by local body
        assert "cases_by_local_body" in charts
        assert len(charts["cases_by_local_body"]) > 0
        sample_lb = charts["cases_by_local_body"][0]
        assert "local_body_name" in sample_lb
        assert "count" in sample_lb

        # 5. Cases by ward
        assert "cases_by_ward" in charts
        assert len(charts["cases_by_ward"]) > 0
        sample_ward = charts["cases_by_ward"][0]
        assert "ward_name" in sample_ward
        assert "count" in sample_ward

    # --------------------------------------------------------------------------
    # 4. MAP DATASETS (CASE MAP, HEATMAP, DISTRICTS)
    # --------------------------------------------------------------------------
    def test_map_data_layers_included(self):
        """Map data must supply discrete cases, heatmap points, and district aggregates."""
        res = client.get("/api/v1/surveillance/dashboard", headers=self.officer_headers)
        assert res.status_code == 200
        map_data = res.json()["map_data"]

        # Disease Cases
        assert "disease_cases" in map_data
        assert len(map_data["disease_cases"]) > 0
        sample_case = map_data["disease_cases"][0]
        assert "latitude" in sample_case and "longitude" in sample_case
        assert "disease_name" in sample_case
        assert "case_status" in sample_case

        # Heatmap Points: [lat, lng, intensity]
        assert "heatmap_points" in map_data
        assert len(map_data["heatmap_points"]) > 0
        point = map_data["heatmap_points"][0]
        assert len(point) == 3
        assert 8.0 <= point[0] <= 13.0  # Latitude within Kerala bounds
        assert 74.0 <= point[1] <= 78.0  # Longitude within Kerala bounds

        # District Aggregates
        assert "districts" in map_data
        assert len(map_data["districts"]) > 0
        sample_dist = map_data["districts"][0]
        assert "name" in sample_dist
        assert "case_count" in sample_dist
        assert "active_count" in sample_dist

    # --------------------------------------------------------------------------
    # 5. DYNAMIC FILTERING
    # --------------------------------------------------------------------------
    def test_filter_by_disease(self):
        """Filtering by disease returns only cases for that specific disease."""
        if not self.dengue:
            pytest.skip("Dengue disease catalog item not found")

        res = client.get(
            f"/api/v1/surveillance/dashboard?disease_id={self.dengue.id}",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()

        # All cases by disease must only contain Dengue
        for item in data["charts"]["cases_by_disease"]:
            assert item["disease_id"] == str(self.dengue.id)

        # Active filters echoed
        assert data["active_filters"]["disease_id"] == str(self.dengue.id)

    def test_filter_by_district(self):
        """Filtering by district scopes cases to that administrative district."""
        if not self.tvm_district:
            pytest.skip("Thiruvananthapuram district not found")

        res = client.get(
            f"/api/v1/surveillance/dashboard?district_id={self.tvm_district.id}",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()

        # All cases by district must only be Thiruvananthapuram
        for item in data["charts"]["cases_by_district"]:
            assert item["district_id"] == str(self.tvm_district.id)

    def test_filter_by_case_status(self):
        """Filtering by CONFIRMED case status returns only confirmed cases."""
        res = client.get(
            "/api/v1/surveillance/dashboard?case_status=CONFIRMED",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()
        kpi = data["kpi_summary"]

        assert kpi["suspected_cases"] == 0
        assert kpi["active_cases"] == kpi["confirmed_cases"]
        assert data["active_filters"]["case_status"] == "CONFIRMED"

    def test_filter_by_date_range(self):
        """Filtering by date range limits cases to diagnosis date window."""
        today = datetime.date.today()
        start = today - datetime.timedelta(days=10)
        end = today + datetime.timedelta(days=10)

        res = client.get(
            f"/api/v1/surveillance/dashboard?start_date={start.isoformat()}&end_date={end.isoformat()}",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()

        for item in data["charts"]["cases_over_time"]:
            d = datetime.date.fromisoformat(item["date"])
            assert start <= d <= end
