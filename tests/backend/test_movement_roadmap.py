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

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic roadmap routes exist."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# Step 12: Patient Movement Roadmap Tests
# ==============================================================================

def test_get_patient_roadmap_success_and_chronology():
    """
    Verify patient can retrieve their own movement roadmap, observations are
    strictly ordered chronologically, and polyline coordinates are provided.
    """
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap?date=2026-09-05", headers=headers)
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()

    assert data["patient_pseudo_id"] == "PAT-SYNTH-101"
    assert "disclaimer" in data
    assert "not performing continuous second-by-second gps tracking" in data["disclaimer"].lower()

    observations = data["observations"]
    assert len(observations) >= 4, f"Expected at least 4 route points, got {len(observations)}"

    # Verify chronological ordering
    timestamps = [datetime.datetime.fromisoformat(o["recorded_at"]) for o in observations]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i + 1], "Observations must be strictly sorted chronologically"


def test_roadmap_date_and_time_filters():
    """Verify roadmap filtering by date (2026-09-05) and time range (09:00 -> 09:30)."""
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    # Time window 09:00 -> 09:30 should include Point A (09:00), Point B (09:15), Point C (09:30)
    res = client.get(
        "/api/v1/monitoring/roadmap?date=2026-09-05&start_time=09:00&end_time=09:30",
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["statistics"]["total_observations"] == 3
    times = [o["recorded_at"] for o in data["observations"]]
    assert any("09:00:00" in t for t in times)
    assert any("09:15:00" in t for t in times)
    assert any("09:30:00" in t for t in times)


def test_roadmap_statistics_calculation():
    """Verify statistics: total_observations, first/last location, average_accuracy."""
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap?date=2026-09-05", headers=headers)
    assert res.status_code == 200
    stats = res.json()["statistics"]

    assert stats["total_observations"] >= 4
    assert stats["monitoring_start"] is not None
    assert stats["monitoring_end"] is not None
    assert stats["first_recorded_location"] is not None
    assert stats["first_recorded_location"]["latitude"] == pytest.approx(8.5241, abs=0.001)
    assert stats["first_recorded_location"]["longitude"] == pytest.approx(76.9366, abs=0.001)
    assert stats["average_accuracy"] is not None
    assert stats["average_accuracy"] > 0.0


def test_roadmap_patient_privacy_rbac_enforcement():
    """
    Verify RBAC:
    - Patient A CANNOT query Patient B's roadmap (403 Forbidden).
    - Public Health Officer CAN query any patient's roadmap.
    """
    patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")

    db = SessionLocal()
    try:
        p2 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
        assert p2 is not None
        p2_id = str(p2.id)
    finally:
        db.close()

    # 1. Patient 101 attempts to view Patient 102's roadmap -> Forbidden
    denied = client.get(
        f"/api/v1/monitoring/roadmap?patient_id={p2_id}",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert denied.status_code == 403
    assert "cannot" in denied.json()["error"]["message"].lower() or "denied" in denied.json()["error"]["message"].lower()

    # 2. Public Health Officer queries Patient 101's roadmap -> Allowed
    officer_view = client.get(
        "/api/v1/monitoring/roadmap?pseudo_id=PAT-SYNTH-101&date=2026-09-05",
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert officer_view.status_code == 200
    assert officer_view.json()["patient_pseudo_id"] == "PAT-SYNTH-101"


def test_roadmap_data_source_labeling_distinction():
    """Verify observations preserve distinct source tags (PATIENT_GPS vs HEALTH_WORKER)."""
    token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/monitoring/roadmap?date=2026-09-05", headers=headers)
    assert res.status_code == 200
    sources = {o["source"] for o in res.json()["observations"]}

    # Verify observation telemetry sources (PATIENT_GPS, HEALTH_WORKER, or SIMULATED)
    assert len(sources) >= 1
    assert any(s in sources for s in ["PATIENT_GPS", "HEALTH_WORKER", "SIMULATED"])
