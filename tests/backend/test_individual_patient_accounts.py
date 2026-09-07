import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.user import User, Role
from app.models.patient import Patient
from app.core.security import get_password_hash

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    init_db()


def get_officer_token() -> str:
    res = client.post(
        "/api/auth/login",
        json={"email": "officer@test.com", "password": "Officer@123"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_patient_login_with_email_and_pseudo_id():
    """Verify individual patient can authenticate using either Email OR Account ID (pseudo_id)."""
    # 1. Login with Email
    email_res = client.post(
        "/api/auth/login",
        json={"email": "alana@healthwatch.org", "password": "Patient@HealthWatch2026"},
    )
    assert email_res.status_code == 200, email_res.text
    data = email_res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "PATIENT"
    assert data["user"]["patient_pseudo_id"] == "PAT-USER-143"

    # 2. Login with Account ID (pseudo_id)
    pseudo_res = client.post(
        "/api/auth/login",
        json={"email": "PAT-USER-143", "password": "Patient@HealthWatch2026"},
    )
    assert pseudo_res.status_code == 200, pseudo_res.text
    data2 = pseudo_res.json()
    assert "access_token" in data2
    assert data2["user"]["email"] == "alana@healthwatch.org"
    assert data2["user"]["patient_pseudo_id"] == "PAT-USER-143"


def test_inactive_account_rejection():
    """Verify inactive account is rejected with 403 and the specific user-facing message."""
    db = SessionLocal()
    try:
        # Create or deactivate an inactive user
        test_email = "inactive.patient.test@healthwatch.org"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            role = db.query(Role).filter(Role.name == "PATIENT").first()
            user = User(
                email=test_email,
                hashed_password=get_password_hash("TestPassword123!"),
                full_name="Inactive Patient Test",
                role_id=role.id,
                is_active=False,
            )
            db.add(user)
        else:
            user.is_active = False
        db.commit()

        res = client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "TestPassword123!"},
        )
        assert res.status_code == 403, res.text
        # Check user-facing message
        err_detail = res.json().get("error", {}).get("message") or res.json().get("detail", "")
        assert "This account is inactive. Please contact the administrator." in err_detail
    finally:
        db.close()


def test_create_patient_creates_linked_user_account():
    """Verify creating a patient via /api/v1/patients/ creates a linked User account that can authenticate."""
    officer_token = get_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    import random
    rand_id = random.randint(1000, 9999)
    pseudo_id = f"PAT-AUTO-{rand_id}"
    patient_email = f"auto.patient.{rand_id}@healthwatch.kerala.gov.in"
    patient_pass = "SecurePass2026!"

    # Fetch valid district, local body, ward
    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    assert dist_res.status_code == 200
    dist = dist_res.json()[0]

    lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={dist['id']}", headers=headers)
    assert lb_res.status_code == 200
    lb = lb_res.json()[0]

    ward_res = client.get(f"/api/v1/gis/wards?local_body_id={lb['id']}", headers=headers)
    assert ward_res.status_code == 200
    ward = ward_res.json()[0]

    payload = {
        "pseudo_id": pseudo_id,
        "full_name": f"Auto Test Patient {rand_id}",
        "email": patient_email,
        "initial_password": patient_pass,
        "age": 32,
        "gender": "MALE",
        "contact_number": "+91-98470-99999",
        "address": "123 Auto Lane, Test Nagar",
        "district_id": dist["id"],
        "local_body_id": lb["id"],
        "ward_id": ward["id"],
        "ward_number": ward["ward_number"],
    }

    create_res = client.post("/api/v1/patients/", json=payload, headers=headers)
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    assert created["pseudo_id"] == pseudo_id
    assert created["account_email"] == patient_email
    assert created["district_name"] == dist["name"]

    # Now verify the patient can log in with their newly created credentials!
    login_res = client.post(
        "/api/auth/login",
        json={"email": patient_email, "password": patient_pass},
    )
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    assert token_data["user"]["patient_pseudo_id"] == pseudo_id

    # And verify login using the pseudo_id
    login_pseudo_res = client.post(
        "/api/auth/login",
        json={"email": pseudo_id, "password": patient_pass},
    )
    assert login_pseudo_res.status_code == 200, login_pseudo_res.text


def test_spatial_hierarchy_referential_validation():
    """Verify mismatched district_id and local_body_id returns 400 Bad Request."""
    officer_token = get_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    dist_res = client.get("/api/v1/gis/districts", headers=headers)
    districts = dist_res.json()
    dist_a = districts[0]
    dist_b = districts[1]

    # Get local body belonging to dist_b
    lb_res = client.get(f"/api/v1/gis/local-bodies?district_id={dist_b['id']}", headers=headers)
    lb_b = lb_res.json()[0]

    payload = {
        "pseudo_id": "PAT-MISMATCH-999",
        "full_name": "Mismatch Test",
        "age": 30,
        "gender": "FEMALE",
        "contact_number": "+91-98470-11111",
        "address": "Mismatch Street",
        "district_id": dist_a["id"],  # District A
        "local_body_id": lb_b["id"],  # Local body belonging to District B!
        "ward_number": 1,
    }

    res = client.post("/api/v1/patients/", json=payload, headers=headers)
    assert res.status_code == 400, res.text
    err_msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "does not belong to the selected district" in err_msg


def test_patient_cross_patient_isolation():
    """Verify patient cannot access another patient's profile or roadmap."""
    # Login as patient Alana
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alana@healthwatch.org", "password": "Patient@HealthWatch2026"},
    )
    assert login_res.status_code == 200
    alana_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {alana_token}"}

    # 1. Alana can access /patients/me
    me_res = client.get("/api/v1/patients/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["pseudo_id"] == "PAT-USER-143"

    # 2. Alana cannot access all patients list /patients/
    list_res = client.get("/api/v1/patients/", headers=headers)
    assert list_res.status_code == 403

    # 3. Alana querying another patient's roadmap (e.g. PAT-SYNTH-101) is denied or scoped to self
    roadmap_res = client.get("/api/v1/monitoring/roadmap?pseudo_id=PAT-SYNTH-101", headers=headers)
    # Role-based check: patient cannot query another patient's pseudo_id
    assert roadmap_res.status_code == 403
