import datetime
import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))
sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.user import User, Role
from app.models.patient import Patient
from app.models.monitoring import PatientLocation, MonitoringSession, LocationConsent
from app.core.security import get_password_hash

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database is initialized and seeded."""
    init_db()


def get_token(email_or_id: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email_or_id, "password": password})
    assert res.status_code == 200, f"Login failed for {email_or_id}: {res.text}"
    return res.json()["access_token"]


@pytest.fixture
def transient_patient():
    """Create a temporary secondary patient to verify dynamic multi-patient scalability without demo seeding."""
    db = SessionLocal()
    role_pat = db.query(Role).filter(Role.name == "PATIENT").first()
    test_email = f"transient.{uuid.uuid4().hex[:8]}@healthwatch.org"
    pseudo = f"PAT-TRN-{uuid.uuid4().hex[:4].upper()}"

    user = User(
        email=test_email,
        hashed_password=get_password_hash("Patient@HealthWatch2026"),
        full_name="Transient Test Patient",
        role_id=role_pat.id if role_pat else None,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    patient = Patient(
        pseudo_id=pseudo,
        user_id=user.id,
        full_name="Transient Test Patient",
        age=30,
        gender="FEMALE",
        has_phone=True,
        is_active=True,
    )
    db.add(patient)
    db.flush()

    consent = LocationConsent(
        patient_id=patient.id,
        consent_status="ACTIVE",
        consent_given_at=datetime.datetime.now(datetime.timezone.utc),
        monitoring_start=datetime.datetime.now(datetime.timezone.utc),
        monitoring_end=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30),
        purpose="Dynamic Testing",
    )
    db.add(consent)
    db.flush()

    session = MonitoringSession(
        patient_id=patient.id,
        consent_id=consent.id,
        start_time=datetime.datetime.now(datetime.timezone.utc),
        status="ACTIVE",
    )
    db.add(session)
    db.flush()

    # Add 1 observation for this transient patient
    loc = PatientLocation(
        patient_id=patient.id,
        session_id=session.id,
        monitoring_session_id=session.id,
        recorded_at=datetime.datetime.now(datetime.timezone.utc),
        latitude=10.0123,
        longitude=76.3456,
        source="PATIENT_GPS",
    )
    db.add(loc)
    db.commit()

    patient_id = patient.id
    user_id = user.id
    db.close()

    yield {
        "email": test_email,
        "password": "Patient@HealthWatch2026",
        "pseudo_id": pseudo,
        "patient_id": patient_id,
        "user_id": user_id,
    }

    # Cleanup
    db = SessionLocal()
    db.query(PatientLocation).filter(PatientLocation.patient_id == patient_id).delete()
    db.query(MonitoringSession).filter(MonitoringSession.patient_id == patient_id).delete()
    db.query(LocationConsent).filter(LocationConsent.patient_id == patient_id).delete()
    db.query(Patient).filter(Patient.id == patient_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


def test_scenario_1_pat_111_authenticated_roadmap():
    """Scenario 1: Authenticate as alanapj161@gmail.com / PAT-111 -> returns PAT-111 observations dynamically."""
    token = get_token("alanapj161@gmail.com", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    # Calling without query params resolves identity from JWT
    res = client.get("/api/v1/monitoring/roadmap", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["patient_pseudo_id"] == "PAT-111"
    assert len(data["observations"]) == 49  # 5 on Sept 6, 39 on Sept 7, 5 on Sept 8

    # Check September 8 observations are in Thrissur
    res_sept8 = client.get("/api/v1/monitoring/roadmap?date=2026-09-08", headers=headers)
    assert res_sept8.status_code == 200
    sept8_data = res_sept8.json()
    assert len(sept8_data["observations"]) == 5
    for obs in sept8_data["observations"]:
        assert obs["latitude"] == pytest.approx(10.57, abs=0.02)
        assert obs["longitude"] == pytest.approx(76.07, abs=0.02)
        assert obs["source"] == "PATIENT_GPS"


def test_scenario_2_dynamic_secondary_patient_authenticated_roadmap(transient_patient):
    """Scenario 2: Authenticate as any secondary patient -> dynamic resolution without hardcoding."""
    token = get_token(transient_patient["email"], transient_patient["password"])
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["patient_pseudo_id"] == transient_patient["pseudo_id"]
    assert len(data["observations"]) == 1
    assert data["observations"][0]["latitude"] == pytest.approx(10.0123, abs=1e-3)


def test_scenario_3_cross_patient_access_rejection(transient_patient):
    """Scenario 3: PAT-111 attempts to pass another patient's identifier -> 403 Forbidden."""
    token = get_token("alanapj161@gmail.com", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    # 3a. With another pseudo_id
    res_pseudo = client.get(f"/api/v1/monitoring/roadmap?pseudo_id={transient_patient['pseudo_id']}", headers=headers)
    assert res_pseudo.status_code == 403, res_pseudo.text
    err_detail = res_pseudo.json().get("error", {}).get("message") or res_pseudo.json().get("detail", "")
    assert "own movement roadmap" in err_detail.lower() or "denied" in err_detail.lower()

    # 3b. With another patient_id
    res_id = client.get(f"/api/v1/monitoring/roadmap?patient_id={transient_patient['patient_id']}", headers=headers)
    assert res_id.status_code == 403, res_id.text


def test_scenario_4_officer_without_patient_param():
    """Scenario 4: Officer queries roadmap without patient_id or pseudo_id -> 400 Bad Request."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    res = client.get("/api/v1/monitoring/roadmap", headers=headers)
    assert res.status_code == 400, res.text
    err_detail = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "select or specify a patient" in err_detail.lower()


def test_scenario_5_officer_explicit_pat_111():
    """Scenario 5: Officer explicitly requests PAT-111 -> returns PAT-111 roadmap."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    res = client.get("/api/v1/monitoring/roadmap?pseudo_id=PAT-111", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["patient_pseudo_id"] == "PAT-111"
    assert len(data["observations"]) == 49


def test_scenario_6_officer_explicit_nonexistent_patient():
    """Scenario 6: Officer requests non-existent patient -> returns 404 Not Found."""
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {officer_token}"}

    res = client.get("/api/v1/monitoring/roadmap?pseudo_id=NON-EXISTENT-999", headers=headers)
    assert res.status_code == 404, res.text


def test_scenario_6b_patient_with_zero_observations():
    """Scenario 6b: Patient with zero observations returns empty list without fabricated coordinates."""
    db = SessionLocal()
    zero_pat = Patient(
        pseudo_id=f"PAT-ZERO-{uuid.uuid4().hex[:4].upper()}",
        full_name="Zero Obs Patient",
        age=45,
        gender="MALE",
        has_phone=True,
        is_active=True,
    )
    db.add(zero_pat)
    db.commit()
    zero_pseudo = zero_pat.pseudo_id
    zero_id = zero_pat.id
    db.close()

    try:
        officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {officer_token}"}

        res = client.get(f"/api/v1/monitoring/roadmap?pseudo_id={zero_pseudo}", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["patient_pseudo_id"] == zero_pseudo
        assert data["observations"] == []
        assert data["statistics"]["total_observations"] == 0
    finally:
        db = SessionLocal()
        db.query(Patient).filter(Patient.id == zero_id).delete()
        db.commit()
        db.close()


def test_scenario_7_patients_me_endpoint_isolation():
    """Scenario 7: /patients/me for patient returns own record; for admin returns 404."""
    pat_token = get_token("alanapj161@gmail.com", "Patient@HealthWatch2026")
    res_pat = client.get("/api/v1/patients/me", headers={"Authorization": f"Bearer {pat_token}"})
    assert res_pat.status_code == 200, res_pat.text
    assert res_pat.json()["pseudo_id"] == "PAT-111"

    # Admin without linked patient profile gets 404
    admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
    res_admin = client.get("/api/v1/patients/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 404, res_admin.text


def test_scenario_8_cases_me_endpoint_isolation():
    """Scenario 8: /cases/me for patient returns own cases; for admin without patient returns 0 cases."""
    pat_token = get_token("alanapj161@gmail.com", "Patient@HealthWatch2026")
    res_pat = client.get("/api/v1/cases/me", headers={"Authorization": f"Bearer {pat_token}"})
    assert res_pat.status_code == 200, res_pat.text

    admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
    res_admin = client.get("/api/v1/cases/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200, res_admin.text
    assert res_admin.json()["total"] == 0
