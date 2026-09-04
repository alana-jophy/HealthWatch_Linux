import datetime
import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.monitoring import LocationConsent, MonitoringSession, ConsentStatus, SessionStatus
from app.models.patient import Patient

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic accounts exist."""
    init_db()


def get_patient_token(email: str = "patient.synth101@healthwatch.org", password: str = "Patient@HealthWatch2026") -> str:
    """Helper to authenticate as patient."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def get_officer_token() -> str:
    """Helper to authenticate as health officer."""
    res = client.post("/api/auth/login", json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"})
    assert res.status_code == 200
    return res.json()["access_token"]


# ==============================================================================
# Step 9: Monitoring Session Management Tests
# ==============================================================================

def test_sampling_interval_configuration():
    """Verify location sampling interval is configured to ~15 minutes (900 seconds), NOT 10 seconds."""
    assert settings.LOCATION_SAMPLING_INTERVAL_SECONDS == 900
    assert settings.LOCATION_SAMPLING_INTERVAL_MINUTES == 15

    token = get_patient_token()
    res = client.get("/api/v1/monitoring/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["sampling_interval_minutes"] == 15
    assert data["sampling_interval_seconds"] == 900
    assert "15 minutes" in data["sampling_interval_description"]


def test_custom_monitoring_period_session():
    """Verify starting monitoring session with explicit start/end dates."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Grant 30-day consent
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 30}, headers=headers)

    now = datetime.datetime.now(datetime.timezone.utc)
    custom_start = (now - datetime.timedelta(hours=1)).isoformat()
    custom_end = (now + datetime.timedelta(days=5)).isoformat()

    session_res = client.post(
        "/api/v1/monitoring/sessions/start",
        json={"start_time": custom_start, "end_time": custom_end},
        headers=headers,
    )
    assert session_res.status_code == 201
    data = session_res.json()
    assert data["status"] == "ACTIVE"
    assert data["sampling_interval_seconds"] == 900


def test_location_observation_submission_and_postgis_storage():
    """Verify: Location submission during active session is accepted and stored in PostGIS."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure active consent and session exist
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_res = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers)
    session_id = session_res.json()["id"]

    # Submit valid observation
    now = datetime.datetime.now(datetime.timezone.utc)
    obs_payload = {
        "session_id": session_id,
        "latitude": 8.5241,
        "longitude": 76.9366,
        "recorded_at": now.isoformat(),
        "accuracy_meters": 4.5,
        "speed_mps": 1.2,
        "altitude": 15.0,
    }

    sub_res = client.post("/api/v1/monitoring/locations/submit", json=obs_payload, headers=headers)
    assert sub_res.status_code == 201
    data = sub_res.json()
    assert data["status"] == "ACCEPTED"
    assert data["latitude"] == 8.5241
    assert data["longitude"] == 76.9366
    assert data["session_id"] == session_id


def test_location_submission_rejected_after_consent_revoked():
    """Verify: Location submission is rejected (400) when consent is revoked."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Grant consent and start session
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_res = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers)
    session_id = session_res.json()["id"]

    # 2. Revoke consent
    client.post("/api/v1/monitoring/consent/revoke", json={"reason": "User opt out"}, headers=headers)

    # 3. Location submission MUST BE REJECTED
    sub_res = client.post(
        "/api/v1/monitoring/locations/submit",
        json={"session_id": session_id, "latitude": 8.5241, "longitude": 76.9366},
        headers=headers,
    )
    assert sub_res.status_code == 400
    assert "rejected" in sub_res.json()["error"]["message"].lower()


def test_location_submission_rejected_when_session_stopped():
    """Verify: Location submission is rejected (400) when session is stopped."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Active consent & session
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_res = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers)
    session_id = session_res.json()["id"]

    # 2. Stop session
    client.post("/api/v1/monitoring/sessions/stop", json={"session_id": session_id}, headers=headers)

    # 3. Location submission MUST BE REJECTED
    sub_res = client.post(
        "/api/v1/monitoring/locations/submit",
        json={"session_id": session_id, "latitude": 8.5241, "longitude": 76.9366},
        headers=headers,
    )
    assert sub_res.status_code == 400
    assert "is stopped" in sub_res.json()["error"]["message"].lower() or "rejected" in sub_res.json()["error"]["message"].lower()


def test_location_submission_cross_patient_rejection():
    """Verify: Patient A cannot submit locations for Patient B's session (403 Forbidden)."""
    patient_token = get_patient_token()
    officer_token = get_officer_token()

    db = SessionLocal()
    try:
        # Create a session for a different synthetic patient (PAT-SYNTH-102)
        p2 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        now = datetime.datetime.now(datetime.timezone.utc)
        c2 = LocationConsent(
            patient_id=p2.id,
            consent_status=ConsentStatus.ACTIVE.value,
            consent_given_at=now,
            monitoring_start=now,
            monitoring_end=now + datetime.timedelta(days=14),
            purpose="Other patient observation",
        )
        db.add(c2)
        db.flush()

        s2 = MonitoringSession(
            patient_id=p2.id,
            consent_id=c2.id,
            start_time=now,
            end_time=now + datetime.timedelta(days=1),
            status=SessionStatus.ACTIVE.value,
        )
        db.add(s2)
        db.commit()
        p2_session_id = str(s2.id)
    finally:
        db.close()

    # Patient 101 attempting to submit for Patient 102's session MUST BE REJECTED with 403 Forbidden
    sub_res = client.post(
        "/api/v1/monitoring/locations/submit",
        json={"session_id": p2_session_id, "latitude": 8.5241, "longitude": 76.9366},
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert sub_res.status_code == 403
    assert "cannot submit location observations for another patient" in sub_res.json()["error"]["message"].lower()


def test_audit_logging_compliance():
    """Verify compliance audit logs are generated for consent and monitoring actions."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Execute a full lifecycle
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_res = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 12}, headers=headers)
    session_id = session_res.json()["id"]
    client.post("/api/v1/monitoring/locations/submit", json={"session_id": session_id, "latitude": 8.5241, "longitude": 76.9366}, headers=headers)
    client.post("/api/v1/monitoring/sessions/stop", json={"session_id": session_id}, headers=headers)
    client.post("/api/v1/monitoring/consent/revoke", json={"reason": "Test finished"}, headers=headers)

    # Check audit logs endpoint
    audit_res = client.get("/api/v1/monitoring/audit-logs?limit=20", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    action_types = [log["action"] for log in logs]

    assert "CONSENT_GRANTED" in action_types
    assert "MONITORING_STARTED" in action_types
    assert "LOCATION_SUBMITTED" in action_types
    assert "MONITORING_STOPPED" in action_types
    assert "CONSENT_REVOKED" in action_types
