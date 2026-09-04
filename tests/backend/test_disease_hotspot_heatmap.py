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
from app.models.spatial import District, LocalBody, Ward
from app.models.disease import Disease, DiseaseCase

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
# HealthWatch Step 15: Disease Hotspot Heatmap Comprehensive Test Suite
# Tests:
# 1. Access Control & Authorization (Officer/Admin allowed, Patient forbidden 403)
# 2. Privacy-preserving Geographic Aggregation (Ward Centroids, No Exact Coords)
# 3. Four Concentration Tiers (LOW, MODERATE, HIGH, HOTSPOT)
# 4. Surveillance Dashboard Metrics (Total cases, selected area, distribution)
# 5. Cascading Multi-parameter Filters (Disease, District, Local Body, Ward, Status, Dates)
# 6. Synthetic Demo Data Verification
# ==============================================================================

class TestDiseaseHotspotHeatmap:

    @classmethod
    def setup_class(cls):
        cls.officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        cls.admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        cls.patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        cls.officer_headers = {"Authorization": f"Bearer {cls.officer_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.patient_headers = {"Authorization": f"Bearer {cls.patient_token}"}

        # Query database IDs for filters
        db = SessionLocal()
        try:
            cls.dengue = db.query(Disease).filter(Disease.code.like("%DENGUE%")).first()
            cls.cholera = db.query(Disease).filter(Disease.code.like("%CHOLERA%")).first()
            cls.tvm_district = db.query(District).filter(District.code == "KL-TVM").first()
            cls.ekm_district = db.query(District).filter(District.code == "KL-EKM").first()
            cls.palayam_ward = db.query(Ward).filter(Ward.name.like("%Palayam%")).first()
            cls.marine_drive_ward = db.query(Ward).filter(Ward.name.like("%Marine Drive%")).first()
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # 1. ACCESS CONTROL AND RBAC
    # --------------------------------------------------------------------------
    def test_heatmap_access_allowed_for_officer_and_admin(self):
        """Public Health Officers and Admins can access aggregated disease heatmaps."""
        res_officer = client.get("/api/v1/gis/heatmaps", headers=self.officer_headers)
        assert res_officer.status_code == 200
        data = res_officer.json()
        assert data["status"] == "success"
        assert data["total_cases_statewide"] >= 20

        res_admin = client.get("/api/v1/gis/heatmaps", headers=self.admin_headers)
        assert res_admin.status_code == 200
        assert res_admin.json()["status"] == "success"

    def test_heatmap_access_forbidden_for_patient(self):
        """Patients are strictly forbidden from viewing surveillance heatmaps (RBAC 403)."""
        res = client.get("/api/v1/gis/heatmaps", headers=self.patient_headers)
        assert res.status_code == 403
        err_msg = res.json().get("error", {}).get("message", "")
        assert "Access denied" in err_msg or "PATIENT" in err_msg or "forbidden" in err_msg.lower()

    def test_heatmap_access_requires_authentication(self):
        """Unauthenticated requests are rejected with 401."""
        res = client.get("/api/v1/gis/heatmaps")
        assert res.status_code == 401

    # --------------------------------------------------------------------------
    # 2. PRIVACY-PRESERVING GEOGRAPHIC AGGREGATION
    # --------------------------------------------------------------------------
    def test_patient_locations_aggregated_to_ward_centroids(self):
        """
        Privacy Guarantee: All heatmap coordinates must strictly match Ward centroids.
        No raw individual patient coordinates or patient identity identifiers are exposed.
        """
        res = client.get("/api/v1/gis/heatmaps", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()

        db = SessionLocal()
        try:
            wards = {w.id: (round(w.center_latitude, 5), round(w.center_longitude, 5)) for w in db.query(Ward).all()}
        finally:
            db.close()

        valid_centroids = list(wards.values()) + [(8.5241, 76.9366)]

        # density_points are [lat, lng, intensity] tuples for Leaflet canvas heat layer
        for pt in data["density_points"]:
            lat = round(pt[0], 5)
            lng = round(pt[1], 5)
            intensity = pt[2]
            # Must match one of the registered ward centroids or state centroid
            assert any(
                abs(lat - c_lat) < 0.002 and abs(lng - c_lng) < 0.002
                for c_lat, c_lng in valid_centroids
            ), f"Density point ({lat}, {lng}) does not correspond to an aggregated centroid"

            # Must have valid normalized intensity
            assert 0.0 < intensity <= 1.0

    # --------------------------------------------------------------------------
    # 3. FOUR CONCENTRATION TIERS
    # --------------------------------------------------------------------------
    def test_four_concentration_tiers_classification(self):
        """
        Verify the four required concentration tiers:
        - LOW (1-2 cases)
        - MODERATE (3-4 cases)
        - HIGH (5-9 cases)
        - HOTSPOT (10+ cases)
        """
        res = client.get("/api/v1/gis/heatmaps", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()

        concentration_summary = data["concentration_summary"]
        assert "low" in concentration_summary
        assert "moderate" in concentration_summary
        assert "high" in concentration_summary
        assert "hotspot" in concentration_summary

        # At least one area in each concentration tier must exist in our seed cohort
        assert concentration_summary["hotspot"] >= 1, "Expected at least 1 HOTSPOT area (Palayam Ward)"
        assert concentration_summary["high"] >= 1, "Expected at least 1 HIGH concentration area"
        assert concentration_summary["moderate"] >= 1, "Expected at least 1 MODERATE concentration area"
        assert concentration_summary["low"] >= 1, "Expected at least 1 LOW concentration area"

        # Check hotspot areas risk levels
        hotspot_areas = data["hotspot_areas"]
        risk_levels_found = {area.get("risk_tier") or area.get("risk_level") for area in hotspot_areas}
        assert "HOTSPOT" in risk_levels_found
        assert "HIGH" in risk_levels_found
        assert "MODERATE" in risk_levels_found
        assert "LOW" in risk_levels_found

        # Palayam should be identified as a HOTSPOT with >= 10 cases
        palayam_area = next((a for a in hotspot_areas if "Palayam" in (a.get("area_name") or a.get("ward_name") or "")), None)
        assert palayam_area is not None
        assert (palayam_area.get("total_cases") or palayam_area.get("case_count")) >= 10
        assert (palayam_area.get("risk_tier") or palayam_area.get("risk_level")) == "HOTSPOT"

    # --------------------------------------------------------------------------
    # 4. SURVEILLANCE DASHBOARD METRICS
    # --------------------------------------------------------------------------
    def test_surveillance_dashboard_metrics(self):
        """Verify total cases, selected area cases, disease distribution, and hotspot ranking."""
        res = client.get("/api/v1/gis/heatmaps", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()

        # 1. Total cases statewide vs cases in selected area
        assert data["total_cases_statewide"] >= 30
        assert data["cases_in_selected_area"] == data["total_cases_statewide"]  # unfiltered

        # 2. Disease distribution
        dist = data["disease_distribution"]
        assert len(dist) >= 2
        dengue_dist = next((d for d in dist if "Dengue" in d["disease_name"]), None)
        assert dengue_dist is not None
        assert dengue_dist["case_count"] >= 10
        assert dengue_dist["percentage"] > 0

        # Percentages sum to approx 100%
        total_pct = sum(d["percentage"] for d in dist)
        assert 98.0 <= total_pct <= 102.0

        # 3. Hotspot areas ordered descending by case count
        counts = [a.get("total_cases") or a.get("case_count") for a in data["hotspot_areas"]]
        assert counts == sorted(counts, reverse=True)

    # --------------------------------------------------------------------------
    # 5. CASCADING FILTER RESPONSIVENESS
    # --------------------------------------------------------------------------
    def test_filter_by_disease(self):
        """Filtering by Dengue restricts results to Dengue cases only."""
        if not self.dengue:
            pytest.skip("Dengue disease not in database")

        res = client.get(
            f"/api/v1/gis/heatmaps?disease_id={self.dengue.id}",
            headers=self.officer_headers
        )
        assert res.status_code == 200
        data = res.json()

        # All disease distribution items must be Dengue
        for d in data["disease_distribution"]:
            assert d["disease_name"] == self.dengue.name

        # Cases in selected area should be strictly Dengue cases
        assert data["cases_in_selected_area"] < data["total_cases_statewide"]
        assert data["cases_in_selected_area"] >= 15

    def test_filter_by_district(self):
        """Filtering by District restricts results to wards in that district."""
        if not self.tvm_district:
            pytest.skip("TVM district not found")

        res = client.get(
            f"/api/v1/gis/heatmaps?district_id={self.tvm_district.id}",
            headers=self.officer_headers
        )
        assert res.status_code == 200
        data = res.json()

        # Check that all hotspot areas belong to Thiruvananthapuram
        for area in data["hotspot_areas"]:
            assert area["district_name"] == self.tvm_district.name

        assert data["cases_in_selected_area"] < data["total_cases_statewide"]
        assert data["cases_in_selected_area"] >= 20

    def test_filter_by_ward(self):
        """Filtering by single Ward narrows results to that ward only."""
        if not self.palayam_ward:
            pytest.skip("Palayam ward not found")

        res = client.get(
            f"/api/v1/gis/heatmaps?ward_id={self.palayam_ward.id}",
            headers=self.officer_headers
        )
        assert res.status_code == 200
        data = res.json()

        assert len(data["hotspot_areas"]) == 1
        assert "Palayam" in (data["hotspot_areas"][0].get("area_name") or data["hotspot_areas"][0].get("ward_name") or "")
        assert data["cases_in_selected_area"] == (data["hotspot_areas"][0].get("total_cases") or data["hotspot_areas"][0].get("case_count"))

    def test_filter_by_case_status(self):
        """Filtering by case_status CONFIRMED returns only confirmed cases."""
        res_confirmed = client.get(
            "/api/v1/gis/heatmaps?case_status=CONFIRMED",
            headers=self.officer_headers
        )
        assert res_confirmed.status_code == 200
        data_confirmed = res_confirmed.json()

        res_suspected = client.get(
            "/api/v1/gis/heatmaps?case_status=SUSPECTED",
            headers=self.officer_headers
        )
        assert res_suspected.status_code == 200
        data_suspected = res_suspected.json()

        # Confirmed + Suspected should not exceed total
        assert data_confirmed["cases_in_selected_area"] + data_suspected["cases_in_selected_area"] <= data_confirmed["total_cases_statewide"]
        assert data_confirmed["cases_in_selected_area"] >= 10

    def test_filter_by_date_range(self):
        """Filtering by date range restricts cases to diagnosis date window."""
        today = datetime.date.today()
        start = (today - datetime.timedelta(days=7)).isoformat()
        end = (today + datetime.timedelta(days=1)).isoformat()

        res = client.get(
            f"/api/v1/gis/heatmaps?start_date={start}&end_date={end}",
            headers=self.officer_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["cases_in_selected_area"] >= 10

    # --------------------------------------------------------------------------
    # 6. DEMO DATA AND BACKWARDS COMPATIBILITY
    # --------------------------------------------------------------------------
    def test_synthetic_demo_data_notice(self):
        """Verifies synthetic demo data notice is present in response."""
        res = client.get("/api/v1/gis/heatmaps", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_synthetic_demo_data"] is True
        assert "SYNTHETIC" in data["demo_data_notice"]

    def test_backwards_compatibility_fields(self):
        """
        Verify backwards compatibility fields `hotspots` and `total_hotspots`
        are maintained for existing Step 14 checks and clients.
        """
        res = client.get("/api/v1/gis/heatmaps", headers=self.officer_headers)
        assert res.status_code == 200
        data = res.json()
        assert "hotspots" in data
        assert "total_hotspots" in data
        assert isinstance(data["hotspots"], list)
        assert data["total_hotspots"] == len(data["hotspots"])
