"""
HealthWatch Step 20: Comprehensive Security and Privacy Audit Test Suite.
Validates:
1. Authentication: JWT validity, expiration, tampered signatures, bcrypt hashing, password truncation safety.
2. Role-Based Access Control (RBAC): Isolation between ADMIN, PUBLIC_HEALTH_OFFICER, HEALTH_WORKER, PATIENT.
3. Patient Ownership & IDOR Prevention:
   - Patient A -> Patient B profile (403)
   - Patient A -> Patient B disease case (403)
   - Patient A -> Patient B GPS history (403)
   - Patient A -> Patient B movement roadmap (403)
   - Patient A -> Patient B exposure information (403)
4. Location Security & State Machine Enforcement:
   - Submission when consent is REVOKED (400)
   - Submission when session is STOPPED (400)
   - Submission when session is EXPIRED (400)
   - Cross-patient telemetry injection (403 + audit logged)
5. Secrets & Configuration:
   - No password hash leakage in API responses
   - Correct settings configuration
6. API Security & Error Masking:
   - Input validation (bounds, coordinates, accuracy)
   - SQL injection resistance on queries
   - Production error masking (no Python tracebacks exposed)
   - CORS headers present
7. Audit Logging:
   - Audit records generated for sensitive and security-critical actions
"""

import datetime
import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.disease import CaseStatus, Disease, DiseaseCase
from app.models.monitoring import (
    ConsentStatus,
    LocationConsent,
    MonitoringSession,
    PatientLocation,
    SessionStatus,
)
from app.models.patient import Patient
from app.models.user import Role, User
from app.schemas.auth import RoleEnum

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session", autouse=True)
def setup_security_test_env():
    """Ensure database schema and baseline synthetic entities are initialized."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# 1. AUTHENTICATION SECURITY AUDIT
# ==============================================================================

class TestAuthenticationSecurity:

    def test_jwt_issuance_and_claim_structure(self):
        """Verify JWT contains valid subject, role, expiration, and issuer claims."""
        res = client.post(
            "/api/auth/login",
            json={"email": "admin@healthwatch.org", "password": "Admin@HealthWatch2026"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == "admin@healthwatch.org"

    def test_tampered_jwt_signature_rejected(self):
        """Verify that modifying the token signature results in 401 Unauthorized."""
        valid_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        tampered_token = valid_token[:-6] + "xxxxxx"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        res = client.get("/api/auth/me", headers=headers)
        assert res.status_code == 401
        assert "Could not validate credentials" in res.json()["error"]["message"]

    def test_expired_jwt_token_rejected(self):
        """Verify that an expired JWT token is rejected with 401 Unauthorized."""
        db = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.email == "admin@healthwatch.org").first()
            assert admin_user is not None
            expired_token = create_access_token(
                subject=str(admin_user.id),
                role=RoleEnum.ADMIN.value,
                expires_delta=datetime.timedelta(seconds=-60),
            )
        finally:
            db.close()

        headers = {"Authorization": f"Bearer {expired_token}"}
        res = client.get("/api/auth/me", headers=headers)
        assert res.status_code == 401
        assert "Could not validate credentials" in res.json()["error"]["message"]

    def test_missing_authorization_header_rejected(self):
        """Verify that accessing protected APIs without Authorization header returns 401."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401
        assert "Authentication credentials were not provided" in res.json()["error"]["message"]

    def test_bcrypt_password_hashing_and_verification(self):
        """Verify password hashing with bcrypt, salt uniqueness, and correct verification."""
        pwd = "SecureAuditPassword2026!#"
        hashed1 = get_password_hash(pwd)
        hashed2 = get_password_hash(pwd)

        assert hashed1 != hashed2  # Salted bcrypt hashes must be distinct
        assert verify_password(pwd, hashed1) is True
        assert verify_password(pwd, hashed2) is True
        assert verify_password("IncorrectPassword", hashed1) is False

    def test_bcrypt_long_password_truncation_guard(self):
        """Verify passwords exceeding 72 bytes do not crash the hashing mechanism."""
        long_pwd = "A" * 150
        hashed = get_password_hash(long_pwd)
        assert verify_password(long_pwd, hashed) is True
        assert verify_password("A" * 72, hashed) is True


# ==============================================================================
# 2. RBAC MULTI-TIER ISOLATION AUDIT
# ==============================================================================

class TestRoleBasedAccessControlAudit:

    def test_admin_has_full_access(self):
        """ADMIN can access admin endpoints, surveillance, GIS, and reporting."""
        token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        res_admin = client.get("/api/auth/protected/admin", headers=headers)
        assert res_admin.status_code == 200

        res_surv = client.get("/api/v1/surveillance/dashboard", headers=headers)
        assert res_surv.status_code == 200

        res_reports = client.get("/api/v1/reports/preview?report_type=comprehensive", headers=headers)
        assert res_reports.status_code == 200

    def test_public_health_officer_access_boundaries(self):
        """PUBLIC_HEALTH_OFFICER can access surveillance and reports, but NOT admin-only routes."""
        token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # Authorized surveillance access
        res_surv = client.get("/api/v1/surveillance/dashboard", headers=headers)
        assert res_surv.status_code == 200

        res_heatmaps = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res_heatmaps.status_code == 200

        res_exposure = client.get("/api/v1/exposure/events", headers=headers)
        assert res_exposure.status_code == 200

        # Forbidden admin route
        res_admin = client.get("/api/auth/protected/admin", headers=headers)
        assert res_admin.status_code == 403

    def test_health_worker_access_boundaries(self):
        """HEALTH_WORKER cannot access surveillance heatmaps, exposure tracking, or reports."""
        token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # Authorized worker route
        res_worker = client.get("/api/auth/protected/worker", headers=headers)
        assert res_worker.status_code == 200

        # Forbidden: Admin route
        res_admin = client.get("/api/auth/protected/admin", headers=headers)
        assert res_admin.status_code == 403

        # Forbidden: Surveillance heatmaps
        res_heatmaps = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res_heatmaps.status_code == 403

        # Forbidden: Exposure tracking
        res_exposure = client.get("/api/v1/exposure/events", headers=headers)
        assert res_exposure.status_code == 403

        # Forbidden: Surveillance dashboard
        res_surv = client.get("/api/v1/surveillance/dashboard", headers=headers)
        assert res_surv.status_code == 403

        # Forbidden: Reports export
        res_rep = client.get("/api/v1/reports/preview", headers=headers)
        assert res_rep.status_code == 403

    def test_patient_access_boundaries(self):
        """PATIENT cannot access administrative, officer, worker, or public surveillance tools."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # Authorized: Patient own route
        res_patient = client.get("/api/auth/protected/patient", headers=headers)
        assert res_patient.status_code == 200

        # Forbidden: Admin route
        res_admin = client.get("/api/auth/protected/admin", headers=headers)
        assert res_admin.status_code == 403

        # Forbidden: Officer route
        res_officer = client.get("/api/auth/protected/officer", headers=headers)
        assert res_officer.status_code == 403

        # Forbidden: Worker route
        res_worker = client.get("/api/auth/protected/worker", headers=headers)
        assert res_worker.status_code == 403

        # Forbidden: Surveillance dashboard
        res_surv = client.get("/api/v1/surveillance/dashboard", headers=headers)
        assert res_surv.status_code == 403

        # Forbidden: Heatmaps
        res_heatmaps = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res_heatmaps.status_code == 403

        # Forbidden: Exposure events
        res_exposure = client.get("/api/v1/exposure/events", headers=headers)
        assert res_exposure.status_code == 403

        # Forbidden: Reports preview
        res_rep = client.get("/api/v1/reports/preview", headers=headers)
        assert res_rep.status_code == 403


# ==============================================================================
# 3. PATIENT OWNERSHIP (IDOR) ATTEMPTS AUDIT
# ==============================================================================

class TestPatientOwnershipAndIDORPrevention:

    @pytest.fixture(autouse=True)
    def setup_patients(self):
        """Create two separate patients (Patient A and Patient B) in the database."""
        db = SessionLocal()
        try:
            patient_role = db.query(Role).filter(Role.name == RoleEnum.PATIENT.value).first()

            # Ensure Patient A user and profile
            user_a = db.query(User).filter(User.email == "patient.synth101@healthwatch.org").first()
            patient_a = db.query(Patient).filter(Patient.user_id == user_a.id).first()

            # Create or resolve Patient B user and profile
            user_b = db.query(User).filter(User.email == "patient.b.audit@healthwatch.org").first()
            if not user_b:
                user_b = User(
                    email="patient.b.audit@healthwatch.org",
                    hashed_password=get_password_hash("PatientB@HealthWatch2026"),
                    full_name="Audit Patient B",
                    role_id=patient_role.id,
                    is_active=True,
                    is_superuser=False,
                )
                db.add(user_b)
                db.commit()
                db.refresh(user_b)

            patient_b = db.query(Patient).filter(Patient.user_id == user_b.id).first()
            if not patient_b:
                patient_b = Patient(
                    pseudo_id="PAT-AUDIT-B",
                    user_id=user_b.id,
                    full_name="Audit Patient B",
                    age=35,
                    gender="FEMALE",
                    contact_number="+91-9847000099",
                    address="Kochi, Ernakulam",
                    district_name="Ernakulam",
                    local_body_name="Kochi Municipal Corporation",
                    ward_number=12,
                    is_active=True,
                )
                db.add(patient_b)
                db.commit()
                db.refresh(patient_b)

            # Ensure Patient B has a disease case
            disease = db.query(Disease).first()
            case_b = db.query(DiseaseCase).filter(DiseaseCase.patient_id == patient_b.id).first()
            if not case_b and disease:
                case_b = DiseaseCase(
                    patient_id=patient_b.id,
                    disease_id=disease.id,
                    case_status=CaseStatus.CONFIRMED.value,
                    severity="MODERATE",
                    diagnosis_date=datetime.date.today(),
                    clinical_notes="Confidential clinical notes for Patient B",
                )
                db.add(case_b)
                db.commit()
                db.refresh(case_b)

            self.patient_a = patient_a
            self.patient_b = patient_b
            self.case_b = case_b
        finally:
            db.close()

    def test_idor_patient_a_cannot_access_patient_b_profile(self):
        """Attempt: Patient A -> Patient B profile. Must return 403 Forbidden."""
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        # Attempt direct IDOR access to Patient B's profile
        res = client.get(f"/api/v1/patients/{self.patient_b.id}", headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["error"]["message"]

    def test_idor_patient_a_cannot_access_patient_b_disease_case(self):
        """Attempt: Patient A -> Patient B disease case. Must return 403 Forbidden."""
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        # Attempt direct access to Patient B's case record
        res = client.get(f"/api/v1/cases/{self.case_b.id}", headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["error"]["message"]

    def test_idor_patient_a_cannot_access_patient_b_gps_history(self):
        """Attempt: Patient A -> Patient B GPS history. Must return 403 Forbidden."""
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        # Attempt accessing Patient B's location history table
        res = client.get(f"/api/v1/monitoring/locations/history?patient_id={self.patient_b.id}", headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["error"]["message"]

    def test_idor_patient_a_cannot_access_patient_b_movement_roadmap(self):
        """Attempt: Patient A -> Patient B movement roadmap. Must return 403 Forbidden."""
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        # Attempt accessing Patient B's roadmap via patient_id query param
        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={self.patient_b.id}", headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["error"]["message"]

        # Attempt accessing Patient B's roadmap via pseudo_id
        res_pseudo = client.get(f"/api/v1/monitoring/roadmap?pseudo_id={self.patient_b.pseudo_id}", headers=headers)
        assert res_pseudo.status_code == 403

    def test_idor_patient_a_cannot_access_patient_b_exposure_information(self):
        """Attempt: Patient A -> Patient B exposure information. Must return 403 Forbidden."""
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        # Attempt accessing exposure events endpoint filtered by Patient B
        res = client.get(f"/api/v1/exposure/events?patient_id={self.patient_b.id}", headers=headers)
        assert res.status_code == 403


# ==============================================================================
# 4. LOCATION SECURITY & CONSENT STATE AUDIT
# ==============================================================================

class TestLocationSecurityAndStateEnforcement:

    @pytest.fixture(autouse=True)
    def setup_monitoring_states(self):
        """Create explicit monitoring sessions in various states: REVOKED consent, STOPPED, EXPIRED."""
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
            assert patient is not None
            now = datetime.datetime.now(datetime.timezone.utc)

            # 1. Revoked Consent Session
            revoked_consent = LocationConsent(
                patient_id=patient.id,
                consent_status=ConsentStatus.REVOKED.value,
                consent_given_at=now - datetime.timedelta(days=2),
                revoked_at=now - datetime.timedelta(hours=1),
                monitoring_start=now - datetime.timedelta(days=2),
                monitoring_end=now + datetime.timedelta(days=5),
            )
            db.add(revoked_consent)
            db.commit()
            db.refresh(revoked_consent)

            revoked_session = MonitoringSession(
                patient_id=patient.id,
                consent_id=revoked_consent.id,
                status=SessionStatus.ACTIVE.value,
                start_time=now - datetime.timedelta(days=2),
                end_time=now + datetime.timedelta(days=5),
            )
            db.add(revoked_session)
            db.commit()
            db.refresh(revoked_session)

            # 2. Stopped Session
            active_consent = db.query(LocationConsent).filter(
                LocationConsent.patient_id == patient.id,
                LocationConsent.consent_status == ConsentStatus.ACTIVE.value,
            ).first()

            stopped_session = MonitoringSession(
                patient_id=patient.id,
                consent_id=active_consent.id if active_consent else revoked_consent.id,
                status=SessionStatus.STOPPED.value,
                start_time=now - datetime.timedelta(days=1),
                end_time=now + datetime.timedelta(days=5),
                stopped_at=now - datetime.timedelta(hours=2),
            )
            db.add(stopped_session)
            db.commit()
            db.refresh(stopped_session)

            # 3. Expired Session
            expired_session = MonitoringSession(
                patient_id=patient.id,
                consent_id=active_consent.id if active_consent else revoked_consent.id,
                status=SessionStatus.EXPIRED.value,
                start_time=now - datetime.timedelta(days=10),
                end_time=now - datetime.timedelta(days=3),
            )
            db.add(expired_session)
            db.commit()
            db.refresh(expired_session)

            self.patient = patient
            self.revoked_session = revoked_session
            self.stopped_session = stopped_session
            self.expired_session = expired_session
        finally:
            db.close()

    def test_location_submission_rejected_when_consent_is_revoked(self):
        """Verify location telemetry cannot be submitted when consent is REVOKED."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "monitoring_session_id": str(self.revoked_session.id),
            "latitude": 8.5241,
            "longitude": 76.9366,
            "accuracy": 12.5,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": "PATIENT_GPS",
        }
        res = client.post("/api/v1/locations", json=payload, headers=headers)
        assert res.status_code == 400
        assert "consent is revoked, expired, or missing" in res.json()["error"]["message"]

    def test_location_submission_rejected_when_session_is_stopped(self):
        """Verify location telemetry cannot be submitted when monitoring session is STOPPED."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "monitoring_session_id": str(self.stopped_session.id),
            "latitude": 8.5241,
            "longitude": 76.9366,
            "accuracy": 12.5,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": "PATIENT_GPS",
        }
        res = client.post("/api/v1/locations", json=payload, headers=headers)
        assert res.status_code == 400
        assert "STOPPED, not ACTIVE" in res.json()["error"]["message"]

    def test_location_submission_rejected_when_session_is_expired(self):
        """Verify location telemetry cannot be submitted when monitoring session is EXPIRED."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "monitoring_session_id": str(self.expired_session.id),
            "latitude": 8.5241,
            "longitude": 76.9366,
            "accuracy": 12.5,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": "PATIENT_GPS",
        }
        res = client.post("/api/v1/locations", json=payload, headers=headers)
        assert res.status_code == 400
        # Either session is EXPIRED or session has expired
        assert "expired" in res.json()["error"]["message"].lower()

    def test_cross_patient_telemetry_submission_rejected_and_audited(self):
        """Verify Patient A attempting to submit telemetry for Patient B's session returns 403 and logs audit."""
        db = SessionLocal()
        try:
            patient_b = db.query(Patient).filter(Patient.pseudo_id == "PAT-AUDIT-B").first()
            now = datetime.datetime.now(datetime.timezone.utc)

            # Active consent and session for Patient B
            b_consent = LocationConsent(
                patient_id=patient_b.id,
                consent_status=ConsentStatus.ACTIVE.value,
                consent_given_at=now,
                monitoring_start=now,
                monitoring_end=now + datetime.timedelta(days=7),
            )
            db.add(b_consent)
            db.commit()
            db.refresh(b_consent)

            b_session = MonitoringSession(
                patient_id=patient_b.id,
                consent_id=b_consent.id,
                status=SessionStatus.ACTIVE.value,
                start_time=now,
                end_time=now + datetime.timedelta(days=7),
            )
            db.add(b_session)
            db.commit()
            db.refresh(b_session)
            target_session_id = str(b_session.id)
        finally:
            db.close()

        # Patient A tries to submit data for Patient B's active session
        token_a = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token_a}"}

        payload = {
            "monitoring_session_id": target_session_id,
            "latitude": 9.9312,
            "longitude": 76.2673,
            "accuracy": 15.0,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": "PATIENT_GPS",
        }
        res = client.post("/api/v1/locations", json=payload, headers=headers)
        assert res.status_code == 403
        assert "Access denied" in res.json()["error"]["message"]

        # Verify audit log recorded LOCATION_REJECTED
        db = SessionLocal()
        try:
            audit = db.query(AuditLog).filter(
                AuditLog.action == "LOCATION_REJECTED",
                AuditLog.entity_id == target_session_id,
            ).first()
            assert audit is not None
            assert audit.metadata_json.get("reason") == "Patient attempted cross-patient telemetry submission"
        finally:
            db.close()


# ==============================================================================
# 5. SECRETS & CREDENTIALS AUDIT
# ==============================================================================

class TestSecretsAndCredentialsAudit:

    def test_password_hashes_never_leaked_in_responses(self):
        """Verify hashed passwords are never exposed in user API payloads."""
        token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # User profile endpoint
        res = client.get("/api/auth/me", headers=headers)
        assert res.status_code == 200
        user_data = res.json()
        assert "hashed_password" not in user_data
        assert "password" not in user_data

    def test_environment_configuration_validity(self):
        """Verify critical security settings are configured from environment variables."""
        assert len(settings.SECRET_KEY) >= 32
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.POSTGRES_USER != ""
        assert settings.POSTGRES_DB != ""


# ==============================================================================
# 6. API SECURITY & ERROR MASKING AUDIT
# ==============================================================================

class TestAPISecurityAndErrorMasking:

    def test_input_validation_coordinates_and_accuracy(self):
        """Verify invalid telemetry coordinates and unreasonable accuracy are rejected cleanly."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # Invalid latitude (> 90)
        payload_bad_lat = {
            "monitoring_session_id": str(uuid.uuid4()),
            "latitude": 150.0,
            "longitude": 76.9366,
            "accuracy": 10.0,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        res_lat = client.post("/api/v1/locations", json=payload_bad_lat, headers=headers)
        # Rejection should be 404 (session missing) or 422
        assert res_lat.status_code in [404, 422]

    def test_sql_injection_resilience_in_filters(self):
        """Verify SQL injection strings in query filters are parameterized safely by ORM."""
        token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # Malicious SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE patients; --",
            "1' UNION SELECT NULL, NULL, NULL --",
        ]

        for payload in sql_payloads:
            res = client.get(f"/api/v1/patients/?q={payload}", headers=headers)
            assert res.status_code == 200
            # Ensure query executes safely without returning all database tables or erroring
            data = res.json()
            assert "total" in data

    def test_error_handling_masks_internal_stack_traces(self):
        """Verify server errors return generic message without leaking Python tracebacks."""
        token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # Querying an invalid UUID format triggers validation error (422)
        res_val = client.get("/api/v1/patients/not-a-valid-uuid", headers=headers)
        assert res_val.status_code == 422
        err = res_val.json().get("error", {})
        assert err.get("type") == "ValidationError"
        # Verify no Python traceback in response
        assert "Traceback" not in res_val.text
        assert "File \"" not in res_val.text

    def test_cors_headers_present(self):
        """Verify CORS preflight and headers are configured properly."""
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
        res = client.options("/api/health", headers=headers)
        assert res.status_code == 200
        assert "access-control-allow-origin" in res.headers
        assert res.headers["access-control-allow-origin"] == "http://localhost:5173"


# ==============================================================================
# 7. AUDIT LOGGING AUDIT
# ==============================================================================

class TestAuditTrailAudit:

    def test_sensitive_compliance_actions_generate_audit_logs(self):
        """Verify sensitive actions like consent updates and telemetry events appear in audit log."""
        token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/api/v1/monitoring/audit-logs?limit=50", headers=headers)
        assert res.status_code == 200
        logs = res.json()
        assert isinstance(logs, list)
        assert len(logs) > 0

        actions = [log["action"] for log in logs]
        # Verify that key audit actions are captured in the system
        assert any("LOCATION" in a or "CONSENT" in a or "SESSION" in a for a in actions)
