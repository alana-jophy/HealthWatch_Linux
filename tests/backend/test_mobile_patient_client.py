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
from app.models.monitoring import LocationConsent, MonitoringSession, PatientLocation, ConsentStatus, SessionStatus

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_mobile_test_env():
    """Ensure database tables and synthetic accounts exist."""
    init_db()


def test_android_mobile_client_complete_workflow():
    """
    Simulate the exact Android Patient Application flow from Step 10:
    1. Patient Login
    2. Patient Dashboard (/api/auth/me & /api/v1/monitoring/status)
    3. My Profile (/api/v1/patients/)
    4. My Disease Case (/api/v1/cases/)
    5. Location Consent (/api/v1/monitoring/consent/grant)
    6. Monitoring Start (~15 min interval)
    7. Authorized Location Submission with source = PATIENT_GPS
    8. Offline queue simulation & batch upload
    9. Monitoring Stop & rejection verification
    """
    # 1. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "patient.synth101@healthwatch.org", "password": "Patient@HealthWatch2026"}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    auth_data = login_res.json()
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Patient Dashboard: Get Me & Monitoring Status
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "patient.synth101@healthwatch.org"

    status_res = client.get("/api/v1/monitoring/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "HealthWatch will collect your location approximately every 15 minutes" in status_data["explanation_notice"]
    assert status_data["sampling_interval_seconds"] == 900
    assert status_data["sampling_interval_minutes"] == 15

    # 3. My Profile: Query Patient
    patient_res = client.get("/api/v1/patients/?q=PAT-SYNTH-101", headers=headers)
    assert patient_res.status_code == 200
    patients = patient_res.json()["items"]
    assert len(patients) > 0
    patient_id = patients[0]["id"]
    assert patients[0]["pseudo_id"] == "PAT-SYNTH-101"
    assert patients[0]["district_name"] in ["Thiruvananthapuram", "Central District"]

    # 4. My Disease Case
    case_res = client.get("/api/v1/cases/", headers=headers)
    assert case_res.status_code == 200
    cases = case_res.json()["items"]
    assert len(cases) > 0
    assert cases[0]["patient_id"] == patient_id

    # 5. Location Consent: Grant 14 Days
    consent_res = client.post(
        "/api/v1/monitoring/consent/grant",
        json={
            "duration_days": 14,
            "purpose": "Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)"
        },
        headers=headers
    )
    assert consent_res.status_code == 201
    consent_id = consent_res.json()["id"]
    assert consent_res.json()["consent_status"] == "ACTIVE"

    # 6. Monitoring: Start Session
    session_res = client.post(
        "/api/v1/monitoring/sessions/start",
        json={"consent_id": consent_id, "duration_hours": 24},
        headers=headers
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    session_id = session_data["id"]
    assert session_data["status"] == "ACTIVE"
    assert session_data["sampling_interval_seconds"] == 900

    # 7. Authorized Location Submission with source = PATIENT_GPS
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    obs_payload = {
        "patient_id": patient_id,
        "monitoring_session_id": session_id,
        "latitude": 8.5241,
        "longitude": 76.9366,
        "accuracy": 4.8,
        "recorded_at": now_utc,
        "source": "PATIENT_GPS"
    }

    submit_res = client.post(
        "/api/v1/monitoring/locations/submit",
        json=obs_payload,
        headers=headers
    )
    assert submit_res.status_code == 201
    submit_data = submit_res.json()
    assert submit_data["status"] == "ACCEPTED"
    assert submit_data["source"] == "PATIENT_GPS"
    assert submit_data["latitude"] == 8.5241
    assert submit_data["longitude"] == 76.9366

    # 8. Simulate Network Failure -> Local Temporary Queue -> Flushed when online
    # Suppose device accumulated 3 points while offline:
    offline_queue = [
        {"monitoring_session_id": session_id, "latitude": 8.5245, "longitude": 76.9370, "accuracy": 5.0, "source": "PATIENT_GPS"},
        {"monitoring_session_id": session_id, "latitude": 8.5250, "longitude": 76.9375, "accuracy": 4.2, "source": "PATIENT_GPS"},
        {"monitoring_session_id": session_id, "latitude": 8.5255, "longitude": 76.9380, "accuracy": 3.9, "source": "PATIENT_GPS"},
    ]

    synced_count = 0
    for queued_point in offline_queue:
        q_res = client.post("/api/v1/monitoring/locations/submit", json=queued_point, headers=headers)
        assert q_res.status_code == 201
        assert q_res.json()["status"] == "ACCEPTED"
        assert q_res.json()["source"] == "PATIENT_GPS"
        synced_count += 1
    assert synced_count == 3

    # 9. Stop Monitoring Session
    stop_res = client.post(
        "/api/v1/monitoring/sessions/stop",
        json={"session_id": session_id},
        headers=headers
    )
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "STOPPED"

    # 10. Verify location submission is rejected when session is stopped
    rejected_res = client.post(
        "/api/v1/monitoring/locations/submit",
        json=obs_payload,
        headers=headers
    )
    assert rejected_res.status_code == 400
    assert "rejected" in rejected_res.json()["error"]["message"].lower()


def test_android_observation_source_persisted_in_database():
    """Verify that PATIENT_GPS source tag is strictly stored in the PostGIS database table."""
    token = client.post(
        "/api/auth/login",
        json={"email": "patient.synth101@healthwatch.org", "password": "Patient@HealthWatch2026"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start session
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 7}, headers=headers)
    session_id = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 12}, headers=headers).json()["id"]

    # Submit with explicit PATIENT_GPS
    res = client.post(
        "/api/v1/monitoring/locations/submit",
        json={
            "session_id": session_id,
            "latitude": 8.5020,
            "longitude": 76.9510,
            "accuracy": 3.5,
            "source": "PATIENT_GPS"
        },
        headers=headers
    )
    assert res.status_code == 201
    loc_id = res.json()["id"]

    # Verify directly in database
    db = SessionLocal()
    try:
        loc = db.query(PatientLocation).filter(PatientLocation.id == loc_id).first()
        assert loc is not None
        assert loc.source == "PATIENT_GPS"
        assert loc.latitude == 8.5020
        assert loc.longitude == 76.9510
    finally:
        db.close()
