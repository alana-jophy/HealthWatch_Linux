import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_gis_test_environment():
    """Seed spatial hierarchy and disease case points."""
    init_db()


def get_token(email: str, password: str = "Worker@HealthWatch2026") -> str:
    """Obtain JWT access token for role."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


# ==============================================================================
# GIS Administrative Hierarchy Tests (Kerala -> District -> LocalBody -> Ward)
# ==============================================================================

def test_gis_districts_list_and_geojson():
    """Verify districts listing and GeoJSON generation."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # 1. Standard List
    res = client.get("/api/v1/gis/districts", headers=headers)
    assert res.status_code == 200
    districts = res.json()
    assert len(districts) >= 3
    assert any(d["name"] == "Thiruvananthapuram" for d in districts)
    assert any(d["code"] == "KL-TVM" for d in districts)
    assert all(d["source"] == "SIMULATED" for d in districts)

    # 2. GeoJSON FeatureCollection
    res_geojson = client.get("/api/v1/gis/districts/geojson", headers=headers)
    assert res_geojson.status_code == 200
    fc = res_geojson.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 3
    assert fc["features"][0]["geometry"]["type"] in ["Polygon", "MultiPolygon"]


def test_gis_local_bodies_and_filtering():
    """Verify local bodies listing and district_id filtering."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Fetch districts
    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    tvm_district = next(d for d in dist_res.json() if d["code"] == "KL-TVM")

    # Filter local bodies by district
    lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={tvm_district['id']}", headers=headers)
    assert lb_res.status_code == 200
    lbs = lb_res.json()
    assert len(lbs) >= 1
    assert any("Corporation" in lb["name"] for lb in lbs)


def test_gis_wards_and_filtering():
    """Verify wards listing and local_body_id filtering."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Fetch local bodies
    lb_res = client.get("/api/v1/gis/local-bodies", headers=headers)
    assert lb_res.status_code == 200
    first_lb = lb_res.json()[0]

    # Filter wards by local body
    ward_res = client.get(f"/api/v1/gis/wards?local_body_id={first_lb['id']}", headers=headers)
    assert ward_res.status_code == 200
    wards = ward_res.json()
    assert len(wards) >= 1
    assert "ward_number" in wards[0]


# ==============================================================================
# Disease Case Spatial Telemetry & RBAC Privacy Tests
# ==============================================================================

def test_gis_cases_point_locations():
    """Verify disease case point coordinates and GeoJSON properties."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    res = client.get("/api/v1/gis/cases", headers=headers)
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) >= 3

    first_case = cases[0]
    assert "latitude" in first_case and "longitude" in first_case
    # Kerala latitude bounds ~8.0 - 13.0, longitude ~75.0 - 78.0
    assert 8.0 <= first_case["latitude"] <= 13.0
    assert 75.0 <= first_case["longitude"] <= 78.0
    assert first_case["source"] == "SIMULATED"


def test_gis_cases_geojson_feature_collection():
    """Verify GeoJSON FeatureCollection format and [Lng, Lat] order."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    res = client.get("/api/v1/gis/cases/geojson", headers=headers)
    assert res.status_code == 200
    fc = res.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 3

    first_feature = fc["features"][0]
    assert first_feature["type"] == "Feature"
    assert first_feature["geometry"]["type"] == "Point"
    coords = first_feature["geometry"]["coordinates"]
    # In GeoJSON: coordinates are [Longitude, Latitude]
    assert len(coords) == 2
    assert 75.0 <= coords[0] <= 78.0  # Longitude
    assert 8.0 <= coords[1] <= 13.0   # Latitude


def test_gis_cases_filtering():
    """Verify filtering GIS case markers by status and contagion type."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Filter CONFIRMED
    res_confirmed = client.get("/api/v1/gis/cases?case_status=CONFIRMED", headers=headers)
    assert res_confirmed.status_code == 200
    for c in res_confirmed.json():
        assert c["case_status"] == "CONFIRMED"

    # Filter CONTAGIOUS
    res_contagious = client.get("/api/v1/gis/cases?contagion_type=CONTAGIOUS", headers=headers)
    assert res_contagious.status_code == 200
    for c in res_contagious.json():
        assert c["contagion_type"] == "CONTAGIOUS"


def test_gis_cases_patient_privacy_isolation():
    """Verify that a Patient user only receives case points belonging to their own record."""
    patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {patient_token}"}

    res = client.get("/api/v1/gis/cases", headers=headers)
    assert res.status_code == 200
    cases = res.json()
    # Patient 101 has exactly 1 case
    assert len(cases) == 1
    assert cases[0]["patient_pseudo_id"] == "PAT-SYNTH-101"
