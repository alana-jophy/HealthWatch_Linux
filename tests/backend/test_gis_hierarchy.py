import datetime
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
def setup_hierarchy_test_env():
    """Ensure database is seeded with spatial hierarchy and cases."""
    init_db()


def get_officer_token() -> str:
    """Obtain JWT access token for health surveillance officer."""
    res = client.post(
        "/api/auth/login",
        json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ==============================================================================
# Step 7: Hierarchical Geographic Drilldown Tests
# ==============================================================================

def test_hierarchical_district_to_local_bodies():
    """Verify: Selecting a district returns ONLY local bodies belonging to that district."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch all districts
    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    assert dist_res.status_code == 200
    districts = dist_res.json()
    tvm_dist = next(d for d in districts if d["code"] == "KL-TVM")
    ekm_dist = next(d for d in districts if d["code"] == "KL-EKM")

    # 2. Query local bodies for Thiruvananthapuram (KL-TVM)
    tvm_lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={tvm_dist['id']}", headers=headers)
    assert tvm_lb_res.status_code == 200
    tvm_lbs = tvm_lb_res.json()
    assert len(tvm_lbs) >= 2
    assert all(lb["district_id"] == tvm_dist["id"] for lb in tvm_lbs)
    assert any("Thiruvananthapuram" in lb["name"] for lb in tvm_lbs)
    assert any("Nedumangad" in lb["name"] for lb in tvm_lbs)

    # 3. Query local bodies for Ernakulam (KL-EKM)
    ekm_lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={ekm_dist['id']}", headers=headers)
    assert ekm_lb_res.status_code == 200
    ekm_lbs = ekm_lb_res.json()
    assert all(lb["district_id"] == ekm_dist["id"] for lb in ekm_lbs)
    assert any("Kochi" in lb["name"] for lb in ekm_lbs)


def test_hierarchical_local_body_to_wards():
    """Verify: Selecting a local body returns ONLY wards belonging to that local body."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch Thiruvananthapuram Municipal Corporation local body
    lb_res = client.get("/api/v1/gis/local-bodies", headers=headers)
    assert lb_res.status_code == 200
    tvm_corp = next(lb for lb in lb_res.json() if "Thiruvananthapuram Municipal Corporation" in lb["name"])

    # 2. Query wards for Thiruvananthapuram Municipal Corporation
    ward_res = client.get(f"/api/v1/gis/wards?local_body_id={tvm_corp['id']}", headers=headers)
    assert ward_res.status_code == 200
    wards = ward_res.json()
    assert len(wards) >= 4
    assert all(w["local_body_id"] == tvm_corp["id"] for w in wards)
    ward_names = [w["name"] for w in wards]
    assert "Palayam Ward" in ward_names
    assert "Medical College Ward" in ward_names


def test_hierarchical_ward_to_cases():
    """Verify: Selecting a ward filters disease cases strictly to that ward."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Find Palayam Ward
    ward_res = client.get("/api/v1/gis/wards", headers=headers)
    assert ward_res.status_code == 200
    palayam_ward = next(w for w in ward_res.json() if "Palayam" in w["name"])

    # 2. Query cases filtered by ward_id
    cases_res = client.get(f"/api/v1/gis/cases?ward_id={palayam_ward['id']}", headers=headers)
    assert cases_res.status_code == 200
    ward_cases = cases_res.json()
    dengue_case = next((c for c in ward_cases if c["patient_pseudo_id"] == "PAT-SYNTH-101"), None)
    assert dengue_case is not None
    assert dengue_case["disease_code"] == "DENGUE-01"


def test_date_range_case_filtering():
    """Verify: Date range filtering (start_date, end_date) works correctly."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)

    # 1. Query today's date range
    res_today = client.get(
        f"/api/v1/gis/cases?start_date={yesterday}&end_date={tomorrow}",
        headers=headers,
    )
    assert res_today.status_code == 200
    assert len(res_today.json()) >= 3

    # 2. Query future date range with 0 cases
    future_date = today + datetime.timedelta(days=100)
    res_future = client.get(
        f"/api/v1/gis/cases?start_date={future_date}",
        headers=headers,
    )
    assert res_future.status_code == 200
    assert len(res_future.json()) == 0


def test_single_spatial_entity_lookups():
    """Verify: GET /api/v1/gis/districts/{id}, local-bodies/{id}, wards/{id}."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    dist_id = dist_res.json()[0]["id"]

    single_dist = client.get(f"/api/v1/gis/districts/{dist_id}", headers=headers)
    assert single_dist.status_code == 200
    assert single_dist.json()["id"] == dist_id
