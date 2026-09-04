import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure database tables and synthetic users are seeded before tests run."""
    try:
        init_db()
    except Exception as e:
        print(f"Test DB init notice: {e}")


def test_login_synthetic_admin():
    """Test login with synthetic ADMIN user."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@healthwatch.org", "password": "Admin@HealthWatch2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@healthwatch.org"
    assert data["user"]["role"] == "ADMIN"


def test_login_synthetic_officer():
    """Test login with synthetic PUBLIC_HEALTH_OFFICER."""
    response = client.post(
        "/api/auth/login",
        json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "PUBLIC_HEALTH_OFFICER"


def test_login_invalid_password():
    """Verify login failure with incorrect password."""
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@healthwatch.org", "password": "WrongPassword123"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["error"]["message"]


def test_unauthenticated_protected_route():
    """Verify 401 Unauthorized when accessing /api/auth/me without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_profile():
    """Verify /api/auth/me returns profile for valid JWT."""
    # 1. Login to get token
    login_res = client.post(
        "/api/auth/login",
        json={"email": "officer.surveillance@healthwatch.org", "password": "Officer@HealthWatch2026"},
    )
    token = login_res.json()["access_token"]

    # 2. Query /api/auth/me
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "officer.surveillance@healthwatch.org"
    assert user_data["role"] == "PUBLIC_HEALTH_OFFICER"


def test_register_new_user_and_authenticate():
    """Verify registration and immediate login flow."""
    unique_email = "synthetic.analyst99@healthwatch.org"
    reg_payload = {
        "email": unique_email,
        "password": "SecurePassword#2026",
        "full_name": "Synthetic Epidemiological Analyst",
        "role": "HEALTH_WORKER",
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    if reg_res.status_code == 201:
        data = reg_res.json()
        assert data["email"] == unique_email
        assert data["role"] == "HEALTH_WORKER"

    # Authenticate newly created user
    login_res = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "SecurePassword#2026"},
    )
    assert login_res.status_code == 200


def test_role_based_access_controls():
    """Test RBAC enforcement across roles."""
    # 1. Get tokens for Admin, Officer, Worker, and Patient
    def get_token(email, password):
        res = client.post("/api/auth/login", json={"email": email, "password": password})
        return res.json()["access_token"]

    admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
    officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
    worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
    patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")

    # Admin route: Admin OK, Officer 403, Worker 403, Patient 403
    assert client.get("/api/auth/protected/admin", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
    assert client.get("/api/auth/protected/admin", headers={"Authorization": f"Bearer {officer_token}"}).status_code == 403
    assert client.get("/api/auth/protected/admin", headers={"Authorization": f"Bearer {worker_token}"}).status_code == 403
    assert client.get("/api/auth/protected/admin", headers={"Authorization": f"Bearer {patient_token}"}).status_code == 403

    # Officer route: Admin OK, Officer OK, Worker 403, Patient 403
    assert client.get("/api/auth/protected/officer", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
    assert client.get("/api/auth/protected/officer", headers={"Authorization": f"Bearer {officer_token}"}).status_code == 200
    assert client.get("/api/auth/protected/officer", headers={"Authorization": f"Bearer {worker_token}"}).status_code == 403
    assert client.get("/api/auth/protected/officer", headers={"Authorization": f"Bearer {patient_token}"}).status_code == 403

    # Worker route: Admin OK, Officer OK, Worker OK, Patient 403
    assert client.get("/api/auth/protected/worker", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
    assert client.get("/api/auth/protected/worker", headers={"Authorization": f"Bearer {officer_token}"}).status_code == 200
    assert client.get("/api/auth/protected/worker", headers={"Authorization": f"Bearer {worker_token}"}).status_code == 200
    assert client.get("/api/auth/protected/worker", headers={"Authorization": f"Bearer {patient_token}"}).status_code == 403

    # Patient route: Patient OK, Admin OK, Worker 403
    assert client.get("/api/auth/protected/patient", headers={"Authorization": f"Bearer {patient_token}"}).status_code == 200
    assert client.get("/api/auth/protected/patient", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 200
    assert client.get("/api/auth/protected/patient", headers={"Authorization": f"Bearer {worker_token}"}).status_code == 403
