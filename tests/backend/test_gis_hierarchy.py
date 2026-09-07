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
# Step 7 & 20: Hierarchical Geographic Drilldown & Official Kerala Wards Tests
# ==============================================================================

def test_hierarchical_district_to_local_bodies():
    """Verify: Selecting a district returns ONLY local bodies belonging to that district."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch all districts (All 14 Kerala districts)
    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    assert dist_res.status_code == 200
    districts = dist_res.json()
    assert len(districts) == 14
    tvm_dist = next(d for d in districts if d["code"] == "KL-TVM")
    ekm_dist = next(d for d in districts if d["code"] == "KL-EKM")
    alp_dist = next(d for d in districts if d["code"] == "KL-ALP")

    # 2. Query local bodies for Thiruvananthapuram (KL-TVM)
    tvm_lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={tvm_dist['id']}", headers=headers)
    assert tvm_lb_res.status_code == 200
    tvm_lbs = tvm_lb_res.json()
    assert len(tvm_lbs) == 90
    assert all(lb["district_id"] == tvm_dist["id"] for lb in tvm_lbs)
    assert any("Thiruvananthapuram" in lb["name"] for lb in tvm_lbs)
    assert any("Nedumangad" in lb["name"] for lb in tvm_lbs)

    # 3. Query local bodies for Ernakulam (KL-EKM)
    ekm_lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={ekm_dist['id']}", headers=headers)
    assert ekm_lb_res.status_code == 200
    ekm_lbs = ekm_lb_res.json()
    assert len(ekm_lbs) == 111
    assert all(lb["district_id"] == ekm_dist["id"] for lb in ekm_lbs)
    assert any("Kochi" in lb["name"] for lb in ekm_lbs)

    # 4. Query local bodies for Alappuzha (KL-ALP)
    alp_lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={alp_dist['id']}", headers=headers)
    assert alp_lb_res.status_code == 200
    alp_lbs = alp_lb_res.json()
    assert len(alp_lbs) == 91
    assert any(lb["code"] == "M04014" for lb in alp_lbs)


def test_hierarchical_official_kerala_wards():
    """Verify: Official SEC ward counts, codes, and names for Corporations and Municipalities."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Alappuzha Municipality (M04014) - MUST have all 53 official wards
    lb_res = client.get("/api/v1/gis/local-bodies", headers=headers)
    assert lb_res.status_code == 200
    alpy_muni = next(lb for lb in lb_res.json() if lb.get("code") == "M04014")
    assert alpy_muni is not None

    alpy_wards_res = client.get(f"/api/v1/gis/local-bodies/{alpy_muni['id']}/wards", headers=headers)
    assert alpy_wards_res.status_code == 200
    alpy_wards = alpy_wards_res.json()
    assert len(alpy_wards) == 53, f"Expected 53 wards for Alappuzha Municipality, got {len(alpy_wards)}"

    # Check first 3 official wards matching prompt exactly
    w1 = next(w for w in alpy_wards if w["ward_number"] == 1)
    assert w1["ward_code"] == "M04014001"
    assert w1["name"] == "THUMPOLY"

    w2 = next(w for w in alpy_wards if w["ward_number"] == 2)
    assert w2["ward_code"] == "M04014002"
    assert w2["name"] == "KOMMADY"

    w3 = next(w for w in alpy_wards if w["ward_number"] == 3)
    assert w3["ward_code"] == "M04014003"
    assert w3["name"] == "POONTHOPPU"

    # Test searchable ward query by name and code
    search_thumpoly = client.get(f"/api/v1/gis/local-bodies/{alpy_muni['id']}/wards?q=THUMPOLY", headers=headers)
    assert search_thumpoly.status_code == 200
    assert any(w["name"] == "THUMPOLY" for w in search_thumpoly.json())

    search_code = client.get(f"/api/v1/gis/local-bodies/{alpy_muni['id']}/wards?q=M04014002", headers=headers)
    assert search_code.status_code == 200
    assert len(search_code.json()) == 1
    assert search_code.json()[0]["name"] == "KOMMADY"

    # 2. Kochi Municipal Corporation (C07003) - MUST have all 76 official wards
    kochi_corp = next(lb for lb in lb_res.json() if lb.get("code") == "C07003")
    kochi_wards_res = client.get(f"/api/v1/gis/local-bodies/{kochi_corp['id']}/wards", headers=headers)
    assert kochi_wards_res.status_code == 200
    assert len(kochi_wards_res.json()) == 76, f"Expected 76 wards for Kochi Corp, got {len(kochi_wards_res.json())}"
    kw1 = next(w for w in kochi_wards_res.json() if w["ward_number"] == 1)
    assert kw1["ward_code"] == "C07003001"
    assert kw1["name"] == "FORT KOCHI"

    # 3. Thiruvananthapuram Municipal Corporation (C01001) - MUST have all 100 official wards
    tvm_corp = next(lb for lb in lb_res.json() if lb.get("code") == "C01001")
    tvm_wards_res = client.get(f"/api/v1/gis/local-bodies/{tvm_corp['id']}/wards", headers=headers)
    assert tvm_wards_res.status_code == 200
    assert len(tvm_wards_res.json()) == 100, f"Expected 100 wards for TVM Corp, got {len(tvm_wards_res.json())}"
    palayam = next(w for w in tvm_wards_res.json() if w["ward_code"] == "C01001039")
    assert palayam["name"] == "PALAYAM"


def test_referential_integrity_validation():
    """Verify: Rejecting invalid district -> local_body -> ward combinations (Requirement 15)."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    dist_res = client.get("/api/v1/gis/districts", headers=headers).json()
    alp_dist = next(d for d in dist_res if d["code"] == "KL-ALP")
    ekm_dist = next(d for d in dist_res if d["code"] == "KL-EKM")

    alp_lbs = client.get(f"/api/v1/gis/local-bodies?district_id={alp_dist['id']}", headers=headers).json()
    ekm_lbs = client.get(f"/api/v1/gis/local-bodies?district_id={ekm_dist['id']}", headers=headers).json()

    # Try creating patient with District Alappuzha + Local Body from Ernakulam
    bad_payload = {
        "pseudo_id": f"PAT-INVALID-{datetime.datetime.now().microsecond}",
        "full_name": "Invalid Location Subject",
        "district_id": alp_dist["id"],
        "local_body_id": ekm_lbs[0]["id"],  # Ernakulam LB with Alappuzha District!
        "age": 30,
        "gender": "FEMALE",
        "district_name": "Alappuzha",
        "local_body_name": ekm_lbs[0]["name"],
        "ward_number": 1,
    }

    res = client.post("/api/v1/patients/", json=bad_payload, headers=headers)
    assert res.status_code == 400
    assert "Referential integrity error" in res.json()["detail"]


def test_single_spatial_entity_lookups():
    """Verify: GET /api/v1/gis/districts/{id}, local-bodies/{id}, wards/{id}."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    dist_id = dist_res.json()[0]["id"]

    single_dist = client.get(f"/api/v1/gis/districts/{dist_id}", headers=headers)
    assert single_dist.status_code == 200
    assert single_dist.json()["id"] == dist_id

    lb_res = client.get("/api/v1/gis/local-bodies", headers=headers)
    lb_id = lb_res.json()[0]["id"]
    single_lb = client.get(f"/api/v1/gis/local-bodies/{lb_id}", headers=headers)
    assert single_lb.status_code == 200
    assert single_lb.json()["id"] == lb_id
    assert single_lb.json()["code"] is not None

    ward_res = client.get(f"/api/v1/gis/local-bodies/{lb_id}/wards", headers=headers)
    ward_id = ward_res.json()[0]["id"]
    single_ward = client.get(f"/api/v1/gis/wards/{ward_id}", headers=headers)
    assert single_ward.status_code == 200
    assert single_ward.json()["id"] == ward_id
    assert single_ward.json()["ward_code"] is not None
    assert single_ward.json()["ward_name"] is not None

