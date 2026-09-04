import datetime
import uuid
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
def setup_test_environment():
    """Seed synthetic entities for testing."""
    init_db()


def get_token(email: str, password: str = "Worker@HealthWatch2026") -> str:
    """Helper to obtain JWT access token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# Disease Catalog Tests
# ==============================================================================

def test_list_and_filter_diseases():
    """Verify listing and filtering diseases by contagion type."""
    worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
    headers = {"Authorization": f"Bearer {worker_token}"}

    # 1. List all
    res = client.get("/api/v1/diseases/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 5

    # 2. Filter CONTAGIOUS
    res_contagious = client.get("/api/v1/diseases/?contagion_type=CONTAGIOUS", headers=headers)
    assert res_contagious.status_code == 200
    for item in res_contagious.json()["items"]:
        assert item["contagion_type"] == "CONTAGIOUS"

    # 3. Filter NON_CONTAGIOUS
    res_non_contagious = client.get("/api/v1/diseases/?contagion_type=NON_CONTAGIOUS", headers=headers)
    assert res_non_contagious.status_code == 200
    for item in res_non_contagious.json()["items"]:
        assert item["contagion_type"] == "NON_CONTAGIOUS"

    # 4. Search query
    res_search = client.get("/api/v1/diseases/?q=Dengue", headers=headers)
    assert res_search.status_code == 200
    assert any("DENGUE" in item["code"] for item in res_search.json()["items"])


def test_create_and_update_disease():
    """Verify Public Health Officer can create and update disease entries."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    new_disease = {
        "code": f"MALARIA-{uuid.uuid4().hex[:4].upper()}",
        "name": "Malaria Surveillance Strain",
        "contagion_type": "CONTAGIOUS",
        "category": "Vector-Borne",
        "incubation_period_days": 10,
        "r0_estimate": 1.4,
        "description": "Plasmodium parasite transmitted by Anopheles mosquitoes.",
    }

    create_res = client.post("/api/v1/diseases/", json=new_disease, headers=headers)
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # Update
    update_res = client.put(
        f"/api/v1/diseases/{created_id}",
        json={"r0_estimate": 1.6, "description": "Updated epidemiological profile"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["r0_estimate"] == 1.6


# ==============================================================================
# Patient Management Tests & Data Privacy Isolation
# ==============================================================================

def test_health_worker_patient_crud():
    """Verify Health Worker can create, list, search, and update patients."""
    worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
    headers = {"Authorization": f"Bearer {worker_token}"}

    test_pseudo = f"PAT-TEST-{uuid.uuid4().hex[:4].upper()}"
    new_patient = {
        "pseudo_id": test_pseudo,
        "full_name": "Synthetic Test Subject Alpha",
        "age": 42,
        "gender": "MALE",
        "contact_number": "+1-555-8899",
        "address": "15 Healthway Drive, Ward 3",
        "district_name": "Northern District",
        "local_body_name": "North Municipality",
        "ward_number": 3,
    }

    create_res = client.post("/api/v1/patients/", json=new_patient, headers=headers)
    assert create_res.status_code == 201
    pat_data = create_res.json()
    assert pat_data["pseudo_id"] == test_pseudo
    patient_id = pat_data["id"]

    # Search
    search_res = client.get(f"/api/v1/patients/?q={test_pseudo}", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1

    # Update
    update_res = client.put(
        f"/api/v1/patients/{patient_id}",
        json={"age": 43, "address": "17 Healthway Drive, Ward 3"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["age"] == 43


def test_patient_data_privacy_isolation():
    """Verify that a Patient user can ONLY view their own record and is blocked from other patients."""
    patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")

    # 1. Patient list query should return ONLY their 1 own patient record
    pat_res = client.get("/api/v1/patients/", headers={"Authorization": f"Bearer {patient_token}"})
    assert pat_res.status_code == 200
    items = pat_res.json()["items"]
    assert len(items) == 1
    assert items[0]["pseudo_id"] == "PAT-SYNTH-101"

    # 2. Find ID of another patient (e.g. PAT-SYNTH-102) via worker
    worker_res = client.get("/api/v1/patients/?q=PAT-SYNTH-102", headers={"Authorization": f"Bearer {worker_token}"})
    other_patient_id = worker_res.json()["items"][0]["id"]

    # 3. Patient trying to access other patient's record directly must receive 403 Forbidden
    forbidden_res = client.get(
        f"/api/v1/patients/{other_patient_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert forbidden_res.status_code == 403
    assert "You can only view your own patient record" in forbidden_res.json()["error"]["message"]


# ==============================================================================
# Disease Case Surveillance Tests
# ==============================================================================

def test_disease_case_lifecycle():
    """Verify creating, filtering, and updating disease case status."""
    worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
    headers = {"Authorization": f"Bearer {worker_token}"}

    # Fetch patient PAT-SYNTH-102 & disease COVID-19
    pat_res = client.get("/api/v1/patients/?q=PAT-SYNTH-102", headers=headers)
    patient_id = pat_res.json()["items"][0]["id"]

    dis_res = client.get("/api/v1/diseases/?q=COVID-19", headers=headers)
    disease_id = dis_res.json()["items"][0]["id"]

    # 1. Create Suspected Case
    case_payload = {
        "patient_id": patient_id,
        "disease_id": disease_id,
        "case_status": "SUSPECTED",
        "severity": "MILD",
        "diagnosis_date": str(datetime.date.today()),
        "clinical_notes": "Self-reported symptoms under field observation",
    }
    create_res = client.post("/api/v1/cases/", json=case_payload, headers=headers)
    assert create_res.status_code == 201
    case_id = create_res.json()["id"]

    # 2. Update to CONFIRMED
    update_res = client.put(
        f"/api/v1/cases/{case_id}",
        json={"case_status": "CONFIRMED", "severity": "MODERATE", "clinical_notes": "RT-PCR positive result confirmed"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["case_status"] == "CONFIRMED"
    assert update_res.json()["severity"] == "MODERATE"

    # 3. Update to RECOVERED
    recover_res = client.put(
        f"/api/v1/cases/{case_id}",
        json={"case_status": "RECOVERED", "recovery_date": str(datetime.date.today())},
        headers=headers,
    )
    assert recover_res.status_code == 200
    assert recover_res.json()["case_status"] == "RECOVERED"


def test_disease_case_status_filtering():
    """Verify filtering disease cases by SUSPECTED, CONFIRMED, RECOVERED, DECEASED."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Filter CONFIRMED
    res_confirmed = client.get("/api/v1/cases/?case_status=CONFIRMED", headers=headers)
    assert res_confirmed.status_code == 200
    for item in res_confirmed.json()["items"]:
        assert item["case_status"] == "CONFIRMED"

    # Filter RECOVERED
    res_recovered = client.get("/api/v1/cases/?case_status=RECOVERED", headers=headers)
    assert res_recovered.status_code == 200
    for item in res_recovered.json()["items"]:
        assert item["case_status"] == "RECOVERED"
