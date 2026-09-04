"""Verification test suite for Step 22: Safe Demonstration Data."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.user import User
from app.models.patient import Patient
from app.models.disease import Disease, ContagionType
from app.models.spatial import District, LocalBody, Ward
from app.models.monitoring import LocationConsent, MonitoringSession, PatientLocation
from app.models.exposure import ExposureEvent, ExposureStatus
from app.schemas.auth import RoleEnum

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session", autouse=True)
def setup_demo_db():
    """Ensure database tables and synthetic demonstration data are fully initialized."""
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


def get_token(email: str, password: str) -> str:
    """Helper to authenticate and retrieve JWT access token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_demo_users_exist():
    """Verify demonstration synthetic users exist across all required roles."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@healthwatch.org").first()
        officer = db.query(User).filter(User.email == "officer.surveillance@healthwatch.org").first()
        worker = db.query(User).filter(User.email == "worker.field01@healthwatch.org").first()
        patient_user = db.query(User).filter(User.email == "patient.synth101@healthwatch.org").first()

        assert admin is not None
        assert officer is not None
        assert worker is not None
        assert patient_user is not None

        assert admin.role.name == RoleEnum.ADMIN.value
        assert officer.role.name == RoleEnum.PUBLIC_HEALTH_OFFICER.value
        assert worker.role.name == RoleEnum.HEALTH_WORKER.value
        assert patient_user.role.name == RoleEnum.PATIENT.value
    finally:
        db.close()


def test_demo_patients_exist():
    """Verify synthetic patient cohort exists with non-sensitive pseudo IDs."""
    db = SessionLocal()
    try:
        patients = db.query(Patient).all()
        assert len(patients) >= 10

        for p in patients:
            assert p.pseudo_id.startswith("PAT-")
    finally:
        db.close()


def test_demo_diseases_contagious_and_non_contagious():
    """Verify disease catalog contains both CONTAGIOUS and NON_CONTAGIOUS strains."""
    db = SessionLocal()
    try:
        diseases = db.query(Disease).all()
        assert len(diseases) >= 5

        contagious_list = [d for d in diseases if d.contagion_type == ContagionType.CONTAGIOUS.value]
        non_contagious_list = [d for d in diseases if d.contagion_type == ContagionType.NON_CONTAGIOUS.value]

        assert len(contagious_list) >= 3  # Dengue, Covid, Cholera
        assert len(non_contagious_list) >= 2  # Diabetes, Hypertension
    finally:
        db.close()


def test_demo_gis_demonstration_data():
    """Verify Kerala spatial hierarchy is present and marked as SIMULATED / DEMONSTRATION DATA."""
    db = SessionLocal()
    try:
        districts = db.query(District).all()
        local_bodies = db.query(LocalBody).all()
        wards = db.query(Ward).all()

        assert len(districts) >= 3
        assert len(local_bodies) >= 3
        assert len(wards) >= 5

        for d in districts:
            assert d.source in ["SIMULATED", "SIMULATED / DEMONSTRATION DATA"]
        for lb in local_bodies:
            assert lb.source in ["SIMULATED", "SIMULATED / DEMONSTRATION DATA"]
        for w in wards:
            assert w.source in ["SIMULATED", "SIMULATED / DEMONSTRATION DATA"]
    finally:
        db.close()


def test_demo_consent_and_monitoring_sessions():
    """Verify synthetic location consents and active monitoring sessions exist."""
    db = SessionLocal()
    try:
        consents = db.query(LocationConsent).filter(LocationConsent.consent_status == "ACTIVE").all()
        sessions = db.query(MonitoringSession).filter(MonitoringSession.status == "ACTIVE").all()

        assert len(consents) >= 1
        assert len(sessions) >= 1
    finally:
        db.close()


def test_demo_patient_gps_movement_routes():
    """Verify 15-minute sample routes marked with source = SIMULATED."""
    db = SessionLocal()
    try:
        locations = db.query(PatientLocation).filter(PatientLocation.source == "SIMULATED").all()
        assert len(locations) >= 5

        # Check 15-minute interval sequence for synthetic roadmap
        obs_a = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-A").first()
        obs_b = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-B").first()
        obs_c = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-C").first()
        obs_d = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-D").first()
        obs_e = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-E").first()

        assert obs_a is not None and obs_b is not None and obs_c is not None and obs_d is not None and obs_e is not None
        assert obs_a.source == "SIMULATED"
        assert obs_b.source == "SIMULATED"
        assert obs_c.source == "SIMULATED"
        assert obs_d.source == "SIMULATED"
        assert obs_e.source == "SIMULATED"

        # Time difference check: 15 minutes between sequential observations
        diff_ab = (obs_b.recorded_at - obs_a.recorded_at).total_seconds() / 60.0
        diff_bc = (obs_c.recorded_at - obs_b.recorded_at).total_seconds() / 60.0
        assert abs(diff_ab - 15.0) < 0.1
        assert abs(diff_bc - 15.0) < 0.1
    finally:
        db.close()


def test_demo_exposure_events_potential():
    """Verify synthetic spatial-temporal overlap events with status = POTENTIAL exist."""
    db = SessionLocal()
    try:
        potential_exposures = db.query(ExposureEvent).filter(ExposureEvent.status == ExposureStatus.POTENTIAL.value).all()
        assert len(potential_exposures) >= 1

        ev = potential_exposures[0]
        assert ev.distance <= 50.0
        assert ev.time_difference <= 15.0
    finally:
        db.close()


def test_demo_ai_prediction_disclaimer():
    """Verify AI outbreak risk predictions clearly label results as based on simulated data."""
    token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/v1/predictions/outbreak-risk",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "disclaimer" in data
    assert "simulated / demonstration data" in data["disclaimer"].lower() or "decision support" in data["disclaimer"].lower()
