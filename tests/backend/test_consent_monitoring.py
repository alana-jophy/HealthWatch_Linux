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
from app.models.monitoring import LocationConsent, MonitoringSession, ConsentStatus, SessionStatus
from app.models.patient import Patient

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_consent_test_env():
    """Ensure database tables and synthetic accounts exist."""
    init_db()


def get_patient_token(email: str = "patient.synth101@healthwatch.org", password: str = "Patient@HealthWatch2026") -> str:
    """Helper to authenticate as patient."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def get_officer_token() -> str:
    """Helper to authenticate as health officer."""
    res = client.post("/api/auth/login", json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"})
    assert res.status_code == 200
    return res.json()["access_token"]


# ==============================================================================
# Step 8: Patient Location Consent & Monitoring Tests
# ==============================================================================

def test_monitoring_status_explanation_notice():
    """Verify GET /api/v1/monitoring/status returns proper explanation notice."""
    token = get_patient_token()
    res = client.get("/api/v1/monitoring/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "HealthWatch will collect your location approximately every 15 minutes" in data["explanation_notice"]
    assert data["patient_pseudo_id"] == "PAT-SYNTH-101"


def test_grant_consent_and_start_session():
    """Verify: Active consent allows starting an authorized monitoring session."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Grant explicit consent for 14 days
    grant_res = client.post(
        "/api/v1/monitoring/consent/grant",
        json={"duration_days": 14, "purpose": "Quarantine Compliance Observation"},
        headers=headers,
    )
    assert grant_res.status_code == 201
    consent_data = grant_res.json()
    assert consent_data["consent_status"] == "ACTIVE"
    consent_id = consent_data["id"]

    # 2. Start monitoring session under active consent
    session_res = client.post(
        "/api/v1/monitoring/sessions/start",
        json={"consent_id": consent_id, "duration_hours": 24},
        headers=headers,
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    assert session_data["status"] == "ACTIVE"
    assert session_data["consent_id"] == consent_id

    # 3. Verify status shows active
    status_res = client.get("/api/v1/monitoring/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["has_active_consent"] is True
    assert status_res.json()["has_active_session"] is True
    assert status_res.json()["can_collect_location"] is True


def test_revoked_consent_terminates_sessions_and_denies_new_sessions():
    """Verify: Revoking consent terminates running sessions and blocks starting new sessions."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Ensure active consent & session exist
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_start = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 12}, headers=headers)
    session_id = session_start.json()["id"]

    # 2. Revoke consent
    revoke_res = client.post(
        "/api/v1/monitoring/consent/revoke",
        json={"reason": "User requested immediate revocation"},
        headers=headers,
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["consent_status"] == "REVOKED"

    # 3. Verify active session was automatically stopped
    status_res = client.get("/api/v1/monitoring/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["has_active_consent"] is False
    assert status_res.json()["has_active_session"] is False
    assert status_res.json()["can_collect_location"] is False

    # 4. Attempting to start a monitoring session without consent MUST BE DENIED (400 Bad Request)
    denied_res = client.post(
        "/api/v1/monitoring/sessions/start",
        json={"duration_hours": 24},
        headers=headers,
    )
    assert denied_res.status_code == 400
    assert "No active, unexpired location consent found" in denied_res.json()["error"]["message"]


def test_expired_consent_denied():
    """Verify: Expired consent cannot be used to start a monitoring session."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
        # Insert explicitly expired consent
        past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
        expired_consent = LocationConsent(
            patient_id=patient.id,
            consent_status=ConsentStatus.EXPIRED.value,
            consent_given_at=past_time,
            monitoring_start=past_time,
            monitoring_end=past_time + datetime.timedelta(days=14),
            purpose="Expired observation window",
        )
        db.add(expired_consent)
        db.commit()
        expired_consent_id = str(expired_consent.id)
    finally:
        db.close()

    # Attempt to start session with expired consent MUST BE DENIED
    res = client.post(
        "/api/v1/monitoring/sessions/start",
        json={"consent_id": expired_consent_id, "duration_hours": 12},
        headers=headers,
    )
    assert res.status_code == 400
    assert "No active, unexpired location consent found" in res.json()["error"]["message"]


def test_stopped_session_lifecycle():
    """Verify stopping an active session marks it as STOPPED."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Grant consent and start session
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_start = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 12}, headers=headers)
    session_id = session_start.json()["id"]

    # 2. Stop session
    stop_res = client.post("/api/v1/monitoring/sessions/stop", json={"session_id": session_id}, headers=headers)
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "STOPPED"
    assert stop_res.json()["stopped_at"] is not None


def test_patient_cross_access_isolation():
    """Verify: Patient A cannot access, grant, or revoke Patient B's consent/session (403 Forbidden)."""
    patient_token = get_patient_token()
    officer_token = get_officer_token()

    # Fetch other patient (e.g. PAT-SYNTH-102) via health officer
    other_res = client.get("/api/v1/patients/?q=PAT-SYNTH-102", headers={"Authorization": f"Bearer {officer_token}"})
    other_patient_id = other_res.json()["items"][0]["id"]

    # Patient 101 attempting to manage Patient 102's consent must receive 403 Forbidden
    forbidden_res = client.get(
        f"/api/v1/monitoring/status?patient_id={other_patient_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert forbidden_res.status_code == 403
    assert "cannot access or manage another patient's monitoring records" in forbidden_res.json()["error"]["message"]
