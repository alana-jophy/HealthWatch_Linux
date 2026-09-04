import datetime
import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.monitoring import LocationConsent, MonitoringSession, PatientLocation, ConsentStatus, SessionStatus
from app.models.patient import Patient

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic accounts exist."""
    init_db()


def get_patient_token(email: str = "patient.synth101@healthwatch.org", password: str = "Patient@HealthWatch2026") -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def get_officer_token() -> str:
    res = client.post("/api/auth/login", json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"})
    assert res.status_code == 200
    return res.json()["access_token"]


# ==============================================================================
# Step 11: Patient Location Observation API Tests
# ==============================================================================

def test_api_locations_successful_submission_and_postgis_geography():
    """
    Verify POST /api/locations accepts valid observation, resolves patient strictly
    from JWT, and stores PostGIS Geography(Point, 4326) with correct coordinate order.
    """
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Ensure active consent & session exist
    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_res = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers)
    session_id = session_res.json()["id"]

    # 2. Submit location observation
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    client_obs_id = str(uuid.uuid4())
    payload = {
        "monitoring_session_id": session_id,
        "latitude": 8.5241,
        "longitude": 76.9366,
        "accuracy": 4.5,
        "recorded_at": now_utc,
        "source": "PATIENT_GPS",
        "client_observation_id": client_obs_id,
    }

    res = client.post("/api/locations", json=payload, headers=headers)
    assert res.status_code == 201, f"Submission failed: {res.text}"
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert data["source"] == "PATIENT_GPS"
    assert data["latitude"] == 8.5241
    assert data["longitude"] == 76.9366
    assert data["accuracy"] == 4.5
    assert data["is_duplicate"] is False
    location_id = data["location_id"]

    # 3. Direct PostGIS Database Verification
    db = SessionLocal()
    try:
        # Verify coordinates and PostGIS Geography(Point, 4326)
        query = text("""
            SELECT id, patient_id, monitoring_session_id, latitude, longitude, accuracy, source,
                   ST_AsText(location_geography) as geo_wkt,
                   ST_X(location_geography::geometry) as geo_lng,
                   ST_Y(location_geography::geometry) as geo_lat
            FROM patient_locations
            WHERE id = :id
        """)
        row = db.execute(query, {"id": location_id}).fetchone()
        assert row is not None
        assert row.latitude == 8.5241
        assert row.longitude == 76.9366
        assert row.accuracy == 4.5
        assert row.source == "PATIENT_GPS"
        assert str(row.monitoring_session_id) == session_id
        # Strict (Longitude, Latitude) order check in PostGIS
        assert abs(row.geo_lng - 76.9366) < 0.0001
        assert abs(row.geo_lat - 8.5241) < 0.0001
    finally:
        db.close()


def test_anti_duplication_idempotency():
    """Verify that retrying with the same client_observation_id does not insert duplicate rows."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_id = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers).json()["id"]

    client_obs_id = f"MOBILE-RETRY-{uuid.uuid4()}"
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "monitoring_session_id": session_id,
        "latitude": 8.5020,
        "longitude": 76.9510,
        "accuracy": 3.8,
        "recorded_at": now_utc,
        "client_observation_id": client_obs_id,
    }

    # First attempt: Created
    res1 = client.post("/api/locations", json=payload, headers=headers)
    assert res1.status_code == 201
    assert res1.json()["is_duplicate"] is False
    first_loc_id = res1.json()["location_id"]

    # Second attempt (network retry simulation with same idempotency key)
    res2 = client.post("/api/locations", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.json()["is_duplicate"] is True
    assert res2.json()["location_id"] == first_loc_id

    # Verify only 1 row exists in database
    db = SessionLocal()
    try:
        count = db.query(PatientLocation).filter(PatientLocation.client_observation_id == client_obs_id).count()
        assert count == 1
    finally:
        db.close()


def test_validation_bounds_and_accuracy():
    """Verify validation: latitude [-90, 90], longitude [-180, 180], and reasonable accuracy."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_id = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers).json()["id"]
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Invalid latitude > 90
    bad_lat = client.post(
        "/api/locations",
        json={"monitoring_session_id": session_id, "latitude": 95.0, "longitude": 76.9, "recorded_at": now_utc},
        headers=headers,
    )
    assert bad_lat.status_code == 422

    # Invalid longitude < -180
    bad_lng = client.post(
        "/api/locations",
        json={"monitoring_session_id": session_id, "latitude": 8.5, "longitude": -195.0, "recorded_at": now_utc},
        headers=headers,
    )
    assert bad_lng.status_code == 422

    # Unreasonable accuracy (e.g. negative or > 5000m)
    bad_acc = client.post(
        "/api/locations",
        json={"monitoring_session_id": session_id, "latitude": 8.5, "longitude": 76.9, "accuracy": -5.0, "recorded_at": now_utc},
        headers=headers,
    )
    assert bad_acc.status_code == 422 or bad_acc.status_code == 400


def test_validation_future_timestamp_rejected():
    """Verify that fabricated future timestamps are strictly rejected."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_id = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers).json()["id"]

    # Fabricated timestamp 2 hours in the future
    future_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)).isoformat()
    res = client.post(
        "/api/locations",
        json={"monitoring_session_id": session_id, "latitude": 8.5, "longitude": 76.9, "accuracy": 5.0, "recorded_at": future_time},
        headers=headers,
    )
    assert res.status_code == 400
    assert "future" in res.json()["error"]["message"].lower()


def test_security_patient_cross_submission_blocked():
    """Verify: Patient A CANNOT submit location data for Patient B (403 Forbidden)."""
    patient_token = get_patient_token()
    officer_token = get_officer_token()

    db = SessionLocal()
    try:
        # Create a session for PAT-SYNTH-102
        p2 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        now = datetime.datetime.now(datetime.timezone.utc)
        c2 = LocationConsent(
            patient_id=p2.id,
            consent_status=ConsentStatus.ACTIVE.value,
            consent_given_at=now,
            monitoring_start=now,
            monitoring_end=now + datetime.timedelta(days=14),
            purpose="Quarantine observation PAT-102",
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

    # Authenticated Patient 101 attempts to submit location for Patient 102's session
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    res = client.post(
        "/api/locations",
        json={
            "monitoring_session_id": p2_session_id,
            "latitude": 8.5241,
            "longitude": 76.9366,
            "accuracy": 4.0,
            "recorded_at": now_utc,
        },
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert res.status_code == 403
    assert "cannot submit location data for another patient" in res.json()["error"]["message"].lower()


def test_inactive_or_stopped_session_rejected():
    """Verify: Location submission is rejected when session is stopped."""
    token = get_patient_token()
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/monitoring/consent/grant", json={"duration_days": 14}, headers=headers)
    session_id = client.post("/api/v1/monitoring/sessions/start", json={"duration_hours": 24}, headers=headers).json()["id"]
    client.post("/api/v1/monitoring/sessions/stop", json={"session_id": session_id}, headers=headers)

    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    res = client.post(
        "/api/locations",
        json={"monitoring_session_id": session_id, "latitude": 8.5241, "longitude": 76.9366, "accuracy": 5.0, "recorded_at": now_utc},
        headers=headers,
    )
    assert res.status_code == 400
    assert "stopped" in res.json()["error"]["message"].lower()
