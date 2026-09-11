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
from app.models.patient import Patient
from app.models.monitoring import PatientLocation, MonitoringSession

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database is initialized and seeded."""
    init_db()


def get_token(email_or_id: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email_or_id, "password": password})
    assert res.status_code == 200, f"Login failed for {email_or_id}: {res.text}"
    return res.json()["access_token"]


def test_stationary_phone_gps_drift_classification():
    """
    Test Section 17 & 5: Stationary phone test.
    PAT-111 has 5 records collected on September 8 on the desk:
    - Point 1: 10.570435, 76.078665 (acc: 20m) - INITIAL Anchor
    - Point 2: 10.570435, 76.078665 (acc: 20m) - Stationary Drift (0m)
    - Point 3: 10.572313, 76.075994 (acc: 200m) - Stationary Drift (358m, within 2-sigma 400m error circle)
    - Point 4: 10.570791, 76.080344 (acc: 400m) - Stationary Drift (187m, within 400m error circle)
    - Point 5: 10.570435, 76.078665 (acc: 20m) - Stationary Drift (0m)

    Verify that:
    1. Raw coordinates and accuracy are 100% preserved.
    2. stationary_count is 4, confirmed_movement_count is 0.
    3. Points 2, 3, 4, 5 are flagged is_stationary_drift = True.
    4. Statutory disclaimer text matches specification.
    """
    token = get_token("alanapj161@gmail.com", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap?date=2026-09-08", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["patient_pseudo_id"] == "PAT-111"
    assert len(data["observations"]) == 5

    # Statistics check
    stats = data["statistics"]
    assert stats["total_observations"] == 5
    assert stats["stationary_count"] == 4
    assert stats["confirmed_movement_count"] == 0

    obs_list = data["observations"]

    # Point 1: Initial Anchor
    assert obs_list[0]["observation_number"] == 1
    assert obs_list[0]["movement_status"] == "INITIAL"
    assert obs_list[0]["is_stationary_drift"] is False
    assert obs_list[0]["latitude"] == pytest.approx(10.570435, abs=1e-5)
    assert obs_list[0]["longitude"] == pytest.approx(76.078665, abs=1e-5)
    assert obs_list[0]["accuracy"] == 20.0
    assert obs_list[0]["source"] == "PATIENT_GPS"

    # Point 2: Stationary (same spot)
    assert obs_list[1]["observation_number"] == 2
    assert obs_list[1]["movement_status"] == "STATIONARY_DRIFT"
    assert obs_list[1]["is_stationary_drift"] is True
    assert obs_list[1]["displacement_from_prev_meters"] == 0.0

    # Point 3: Stationary GPS drift with ±200m uncertainty
    assert obs_list[2]["observation_number"] == 3
    assert obs_list[2]["movement_status"] == "STATIONARY_DRIFT"
    assert obs_list[2]["is_stationary_drift"] is True
    assert obs_list[2]["latitude"] == pytest.approx(10.572313, abs=1e-5)
    assert obs_list[2]["accuracy"] == 200.0

    # Point 4: Stationary GPS drift with ±400m uncertainty
    assert obs_list[3]["observation_number"] == 4
    assert obs_list[3]["movement_status"] == "STATIONARY_DRIFT"
    assert obs_list[3]["is_stationary_drift"] is True
    assert obs_list[3]["latitude"] == pytest.approx(10.570791, abs=1e-5)
    assert obs_list[3]["accuracy"] == 400.0

    # Point 5: Stationary (back to desk origin)
    assert obs_list[4]["observation_number"] == 5
    assert obs_list[4]["movement_status"] == "STATIONARY_DRIFT"
    assert obs_list[4]["is_stationary_drift"] is True

    # Disclaimer wording check (Section 7)
    assert data["disclaimer_title"] == "Recorded GPS observations"
    assert "connecting line represents the connection between recorded observations and does not represent continuous gps tracking" in data["disclaimer"].lower()


def test_actual_physical_movement_classification():
    """
    Test Section 18: Actual movement test.
    Verify that when an observation significantly shifts beyond the uncertainty threshold,
    it is correctly classified as CONFIRMED_MOVEMENT.
    """
    token = get_token("alanapj161@gmail.com", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap?date=2026-09-06", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert len(data["observations"]) >= 4
    # Between Point A (8.5241, 76.9366) and Point B (8.5305, 76.9420) the distance is ~900m with accuracy 5m
    # This exceeds the uncertainty threshold and must be classified as CONFIRMED_MOVEMENT
    obs_b = data["observations"][1]
    assert obs_b["movement_status"] == "CONFIRMED_MOVEMENT"
    assert obs_b["is_stationary_drift"] is False
    assert obs_b["displacement_from_prev_meters"] > 500.0


def test_raw_gps_data_unaltered_in_database():
    """
    Test Section 6: IMPORTANT - DO NOT ALTER RAW GPS DATA.
    Verify that raw latitude, longitude, accuracy, recorded_at, and source in PostgreSQL
    have not been overwritten or altered.
    """
    db = SessionLocal()
    try:
        p = db.query(Patient).filter(Patient.pseudo_id == "PAT-111").first()
        assert p is not None

        locations = (
            db.query(PatientLocation)
            .filter(PatientLocation.patient_id == p.id)
            .order_by(PatientLocation.recorded_at.asc())
            .all()
        )
        sept8_locs = [l for l in locations if str(l.recorded_at.date()) == "2026-09-08"]
        assert len(sept8_locs) == 5

        # Check raw recorded values on September 8 observations
        assert pytest.approx(sept8_locs[0].latitude, abs=1e-5) == 10.570435
        assert pytest.approx(sept8_locs[0].longitude, abs=1e-5) == 76.078665
        assert sept8_locs[0].source == "PATIENT_GPS"

        assert pytest.approx(sept8_locs[2].latitude, abs=1e-5) == 10.572313
        assert pytest.approx(sept8_locs[2].longitude, abs=1e-5) == 76.075994
        assert sept8_locs[2].source == "PATIENT_GPS"

        assert pytest.approx(sept8_locs[3].latitude, abs=1e-5) == 10.570791
        assert pytest.approx(sept8_locs[3].longitude, abs=1e-5) == 76.080344
        assert sept8_locs[3].source == "PATIENT_GPS"
    finally:
        db.close()
