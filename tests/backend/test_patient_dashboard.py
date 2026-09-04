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
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.models.disease import DiseaseCase

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic data exist."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# HealthWatch Step 13: Patient Dashboard & Security Enforcement Tests
# ==============================================================================

def test_patient_dashboard_welcome_and_profile():
    """
    Verify authenticated patient retrieves their own profile with 'Welcome, [Patient]'
    demographic and geographic data (pseudo_id, age, gender, contact, ward, district).
    """
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/patients/me", headers=headers)
    assert res.status_code == 200, f"Profile request failed: {res.text}"
    data = res.json()

    assert data["pseudo_id"] == "PAT-SYNTH-101"
    assert "Synthetic Patient 101" in data["full_name"]
    assert data["age"] > 0
    assert data["gender"] in ["MALE", "FEMALE", "OTHER"]
    assert "contact_number" in data
    assert "address" in data
    assert "district_name" in data
    assert "local_body_name" in data
    assert "ward_number" in data


def test_patient_dashboard_my_disease_case():
    """
    Verify patient can access their own diagnosed disease cases.
    """
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    # Test /cases/me endpoint
    res = client.get("/api/v1/cases/me", headers=headers)
    assert res.status_code == 200, f"Cases request failed: {res.text}"
    data = res.json()

    assert data["total"] >= 1
    first_case = data["items"][0]
    assert first_case["case_status"] in ["SUSPECTED", "CONFIRMED", "RECOVERED", "DECEASED"]
    assert first_case["severity"] in ["MILD", "MODERATE", "SEVERE", "CRITICAL"]
    assert "diagnosis_date" in first_case
    assert "clinical_notes" in first_case

    # Test /cases/ with role filtering
    res_list = client.get("/api/v1/cases/", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1


def test_patient_dashboard_monitoring_card():
    """
    Verify Monitoring Card displays:
    - Monitoring Status: ACTIVE / STOPPED / EXPIRED
    - Monitoring Period: Start -> End
    - Location Sampling: Approximately 15 minutes
    """
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}
    init_db()  # Ensure consent state machine is reset to ACTIVE

    res = client.get("/api/v1/monitoring/status", headers=headers)
    assert res.status_code == 200, f"Monitoring status failed: {res.text}"
    data = res.json()

    assert data["patient_pseudo_id"] == "PAT-SYNTH-101"
    assert data["has_active_consent"] is True
    assert data["sampling_interval_description"] == "Approximately 15 minutes"
    assert data["sampling_interval_minutes"] == 15
    assert "explanation_notice" in data
    assert "approximately every 15 minutes" in data["explanation_notice"].lower()

    # Verify active consent monitoring period
    assert data["active_consent"] is not None
    assert "monitoring_start" in data["active_consent"]
    assert "monitoring_end" in data["active_consent"]
    assert data["active_consent"]["consent_status"] in ["ACTIVE", "STOPPED", "EXPIRED"]


def test_patient_dashboard_location_history_table():
    """
    Verify Location History table returns tabular records with:
    - Timestamp (recorded_at)
    - Latitude
    - Longitude
    - Accuracy
    - Source
    """
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/locations/history", headers=headers)
    assert res.status_code == 200, f"Location history failed: {res.text}"
    data = res.json()

    assert data["patient_pseudo_id"] == "PAT-SYNTH-101"
    assert data["total"] > 0
    assert len(data["items"]) > 0

    first_obs = data["items"][0]
    assert "recorded_at" in first_obs
    assert isinstance(first_obs["latitude"], (int, float))
    assert isinstance(first_obs["longitude"], (int, float))
    assert "accuracy" in first_obs
    assert "source" in first_obs
    assert first_obs["source"] in ["PATIENT_GPS", "HEALTH_WORKER", "APPROXIMATE", "SIMULATED"]


def test_patient_dashboard_movement_roadmap():
    """
    Verify Movement Roadmap returns discrete observations, statistics, and limitation disclaimer.
    """
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap?date=2026-09-05", headers=headers)
    assert res.status_code == 200, f"Roadmap failed: {res.text}"
    data = res.json()

    assert data["patient_pseudo_id"] == "PAT-SYNTH-101"
    assert len(data["observations"]) >= 4
    assert data["statistics"]["total_observations"] >= 4
    assert "disclaimer" in data


# ==============================================================================
# SECURITY TESTS: Cross-Patient Data Access Strictly Denied (Backend RBAC)
# ==============================================================================

def test_security_patient_cannot_access_another_patient_roadmap_route():
    """
    SECURITY REQUIREMENT: A patient must NEVER be able to retrieve another patient's
    data. Attempting to query another patient's movement roadmap route MUST fail with 403 Forbidden.
    """
    db = SessionLocal()
    try:
        # Find another patient (PAT-SYNTH-102)
        patient_102 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        assert patient_102 is not None, "PAT-SYNTH-102 must exist for cross-testing"
        other_patient_id = patient_102.id
    finally:
        db.close()

    # Authenticated as Patient 101
    patient_101_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {patient_101_token}"}

    # Attempt 1: Via query param ?patient_id=...
    res1 = client.get(f"/api/v1/monitoring/roadmap?patient_id={other_patient_id}", headers=headers)
    assert res1.status_code == 403, f"Expected 403 Forbidden, got {res1.status_code}: {res1.text}"
    assert "denied" in res1.text.lower() or "cannot" in res1.text.lower()

    # Attempt 2: Via path param /patients/{patient_id}/roadmap
    res2 = client.get(f"/api/v1/monitoring/patients/{other_patient_id}/roadmap", headers=headers)
    assert res2.status_code == 403, f"Expected 403 Forbidden, got {res2.status_code}: {res2.text}"

    # Attempt 3: Via query param ?pseudo_id=PAT-SYNTH-102
    res3 = client.get("/api/v1/monitoring/roadmap?pseudo_id=PAT-SYNTH-102", headers=headers)
    assert res3.status_code == 403, f"Expected 403 Forbidden, got {res3.status_code}: {res3.text}"


def test_security_patient_cannot_access_another_patient_location_history():
    """
    SECURITY REQUIREMENT: Patient 101 attempting to retrieve Patient 102's
    location history table records MUST fail with 403 Forbidden.
    """
    db = SessionLocal()
    try:
        patient_102 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        other_patient_id = patient_102.id
    finally:
        db.close()

    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/monitoring/locations/history?patient_id={other_patient_id}", headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_security_patient_cannot_access_another_patient_health_profile():
    """
    SECURITY REQUIREMENT: Patient 101 attempting to access Patient 102's
    demographic record via /patients/{id} MUST fail with 403 Forbidden.
    """
    db = SessionLocal()
    try:
        patient_102 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        other_patient_id = patient_102.id
    finally:
        db.close()

    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/patients/{other_patient_id}", headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_security_patient_cannot_access_another_patient_disease_cases():
    """
    SECURITY REQUIREMENT: Patient 101 attempting to access or filter Patient 102's
    disease cases MUST fail with 403 Forbidden.
    """
    db = SessionLocal()
    try:
        patient_102 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        other_patient_id = patient_102.id
        case_102 = db.query(DiseaseCase).filter(DiseaseCase.patient_id == other_patient_id).first()
        case_102_id = case_102.id if case_102 else None
    finally:
        db.close()

    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt 1: Filter query param ?patient_id=...
    res1 = client.get(f"/api/v1/cases/?patient_id={other_patient_id}", headers=headers)
    assert res1.status_code == 403, f"Expected 403 Forbidden, got {res1.status_code}: {res1.text}"

    # Attempt 2: Direct lookup by case_id of other patient
    if case_102_id:
        res2 = client.get(f"/api/v1/cases/{case_102_id}", headers=headers)
        assert res2.status_code == 403, f"Expected 403 Forbidden, got {res2.status_code}: {res2.text}"


def test_officer_authorized_access_to_patient_data():
    """
    Verify public health officers with legitimate authority CAN access patient records,
    distinguishing officer surveillance authority from unauthorized patient cross-access.
    """
    db = SessionLocal()
    try:
        patient_101 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
        patient_101_id = patient_101.id
    finally:
        db.close()

    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    res_roadmap = client.get(f"/api/v1/monitoring/roadmap?patient_id={patient_101_id}&date=2026-09-05", headers=headers)
    assert res_roadmap.status_code == 200, f"Officer roadmap access failed: {res_roadmap.text}"

    res_history = client.get(f"/api/v1/monitoring/locations/history?patient_id={patient_101_id}", headers=headers)
    assert res_history.status_code == 200, f"Officer location history access failed: {res_history.text}"

    res_profile = client.get(f"/api/v1/patients/{patient_101_id}", headers=headers)
    assert res_profile.status_code == 200, f"Officer patient record access failed: {res_profile.text}"
