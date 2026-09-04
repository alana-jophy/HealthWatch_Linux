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
from app.models.disease import DiseaseCase

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic data exist."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# HealthWatch Step 14: Complete Role-Based Access Control (RBAC) Tests
# Testing all 4 system roles:
# 1. ADMIN
# 2. PUBLIC_HEALTH_OFFICER
# 3. HEALTH_WORKER
# 4. PATIENT
# ==============================================================================

class TestRoleBasedAccessControl:

    # --------------------------------------------------------------------------
    # 1. ADMIN ROLE TESTS
    # --------------------------------------------------------------------------
    def test_admin_has_full_gis_and_movement_access(self):
        """Admin can access all GIS, cases, movement, heatmaps, exposure, and reports."""
        token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. GIS cases
        res = client.get("/api/v1/gis/cases", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) >= 4

        # 2. Heatmaps
        res = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # 3. Exposure Analysis
        res = client.get("/api/v1/gis/exposure-analysis", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # 4. Summary Reports
        res = client.get("/api/v1/gis/reports/summary", headers=headers)
        assert res.status_code == 200
        assert "spatial_coverage" in res.json()

        # 5. Any patient movement roadmap
        db = SessionLocal()
        p101 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
        p103 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-103").first()
        db.close()

        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={p101.id}", headers=headers)
        assert res.status_code == 200

        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={p103.id}", headers=headers)
        assert res.status_code == 200

    # --------------------------------------------------------------------------
    # 2. PUBLIC HEALTH OFFICER ROLE TESTS
    # --------------------------------------------------------------------------
    def test_public_health_officer_surveillance_and_analytics_access(self):
        """Public Health Officer can access disease surveillance GIS, heatmaps, exposure, and reports."""
        token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Full GIS cases surveillance
        res = client.get("/api/v1/gis/cases", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) >= 4

        # 2. Heatmaps
        res = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res.status_code == 200
        assert "hotspots" in res.json()

        # 3. Exposure analysis
        res = client.get("/api/v1/gis/exposure-analysis", headers=headers)
        assert res.status_code == 200
        assert "exposure_risk_zones" in res.json()

        # 4. Summary reports
        res = client.get("/api/v1/gis/reports/summary", headers=headers)
        assert res.status_code == 200
        assert "epidemiology" in res.json()

        # 5. Can access movement roadmaps for epidemiological investigation
        db = SessionLocal()
        p101 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
        db.close()
        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={p101.id}", headers=headers)
        assert res.status_code == 200

    # --------------------------------------------------------------------------
    # 3. HEALTH WORKER ROLE TESTS (Assigned vs Unassigned Restrictions)
    # --------------------------------------------------------------------------
    def test_health_worker_access_to_assigned_patient_is_allowed(self):
        """Health Worker can view assigned patient details, cases, location history, and roadmap."""
        token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        p101 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
        c101 = db.query(DiseaseCase).filter(DiseaseCase.patient_id == p101.id).first()
        db.close()

        # 1. Patient profile of assigned patient
        res = client.get(f"/api/v1/patients/{p101.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["pseudo_id"] == "PAT-SYNTH-101"

        # 2. Disease case of assigned patient
        res = client.get(f"/api/v1/cases/{c101.id}", headers=headers)
        assert res.status_code == 200

        # 3. Movement roadmap of assigned patient
        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={p101.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["patient_pseudo_id"] == "PAT-SYNTH-101"

        # 4. Location history of assigned patient
        res = client.get(f"/api/v1/monitoring/locations/history?patient_id={p101.id}", headers=headers)
        assert res.status_code == 200

    def test_health_worker_access_to_unassigned_patient_is_strictly_forbidden(self):
        """Health Worker is strictly rejected (403 Forbidden) when accessing unassigned patients."""
        token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        p103 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-103").first()
        c103 = db.query(DiseaseCase).filter(DiseaseCase.patient_id == p103.id).first()
        db.close()

        # 1. Attempt to view unassigned patient profile -> 403
        res = client.get(f"/api/v1/patients/{p103.id}", headers=headers)
        assert res.status_code == 403, f"Expected 403 for unassigned patient, got {res.status_code}"
        assert "not assigned" in res.text.lower()

        # 2. Attempt to update unassigned patient -> 403
        res = client.put(f"/api/v1/patients/{p103.id}", json={"full_name": "Tampered Name"}, headers=headers)
        assert res.status_code == 403

        # 3. Attempt to view unassigned patient's case -> 403
        res = client.get(f"/api/v1/cases/{c103.id}", headers=headers)
        assert res.status_code == 403

        # 4. Attempt to view unassigned patient's roadmap -> 403
        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={p103.id}", headers=headers)
        assert res.status_code == 403

        # 5. Attempt to view unassigned patient's location history -> 403
        res = client.get(f"/api/v1/monitoring/locations/history?patient_id={p103.id}", headers=headers)
        assert res.status_code == 403

    def test_health_worker_restricted_from_advanced_analytics_and_deletions(self):
        """Health Worker cannot access heatmaps, exposure analysis, summary reports, or deletion APIs."""
        token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Heatmaps forbidden -> 403
        res = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res.status_code == 403

        # 2. Exposure analysis forbidden -> 403
        res = client.get("/api/v1/gis/exposure-analysis", headers=headers)
        assert res.status_code == 403

        # 3. Reports summary forbidden -> 403
        res = client.get("/api/v1/gis/reports/summary", headers=headers)
        assert res.status_code == 403

        # 4. Deleting patient records forbidden -> 403
        dummy_id = str(uuid.uuid4())
        res = client.delete(f"/api/v1/patients/{dummy_id}", headers=headers)
        assert res.status_code == 403

        # 5. Deleting disease case records forbidden -> 403
        res = client.delete(f"/api/v1/cases/{dummy_id}", headers=headers)
        assert res.status_code == 403

    def test_health_worker_gis_cases_only_contain_assigned_patients(self):
        """Health Worker querying /gis/cases only receives cases for assigned patients."""
        token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/api/v1/gis/cases", headers=headers)
        assert res.status_code == 200
        cases = res.json()
        assert len(cases) > 0

        # Every returned case must belong to assigned patients (PAT-SYNTH-101 or PAT-SYNTH-102)
        for c in cases:
            assert c["patient_pseudo_id"] in ["PAT-SYNTH-101", "PAT-SYNTH-102"], f"Health Worker saw unassigned case: {c}"
            assert c["patient_pseudo_id"] != "PAT-SYNTH-103"

    # --------------------------------------------------------------------------
    # 4. PATIENT ROLE TESTS (Strict Self-Ownership Isolation)
    # --------------------------------------------------------------------------
    def test_patient_can_only_access_own_records(self):
        """Patient can access own profile, case, monitoring, roadmap, and location history."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Own profile
        res = client.get("/api/v1/patients/me", headers=headers)
        assert res.status_code == 200
        assert res.json()["pseudo_id"] == "PAT-SYNTH-101"

        # 2. Own disease case
        res = client.get("/api/v1/cases/me", headers=headers)
        assert res.status_code == 200

        # 3. Own monitoring status
        res = client.get("/api/v1/monitoring/status", headers=headers)
        assert res.status_code == 200
        assert res.json()["patient_pseudo_id"] == "PAT-SYNTH-101"

        # 4. Own movement roadmap
        res = client.get("/api/v1/monitoring/roadmap", headers=headers)
        assert res.status_code == 200
        assert res.json()["patient_pseudo_id"] == "PAT-SYNTH-101"

        # 5. Own location history
        res = client.get("/api/v1/monitoring/locations/history", headers=headers)
        assert res.status_code == 200
        assert res.json()["patient_pseudo_id"] == "PAT-SYNTH-101"

        # 6. GIS cases only returns patient's own location point
        res = client.get("/api/v1/gis/cases", headers=headers)
        assert res.status_code == 200
        cases = res.json()
        assert len(cases) == 1
        assert cases[0]["patient_pseudo_id"] == "PAT-SYNTH-101"

    def test_patient_cannot_access_other_patients_records_or_analytics(self):
        """Patient is strictly forbidden (403 Forbidden) from accessing other patients or analytics."""
        token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        p103 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-103").first()
        c103 = db.query(DiseaseCase).filter(DiseaseCase.patient_id == p103.id).first()
        db.close()

        # 1. Other patient profile -> 403
        res = client.get(f"/api/v1/patients/{p103.id}", headers=headers)
        assert res.status_code == 403

        # 2. Other patient case -> 403
        res = client.get(f"/api/v1/cases/{c103.id}", headers=headers)
        assert res.status_code == 403

        # 3. Other patient roadmap -> 403
        res = client.get(f"/api/v1/monitoring/roadmap?patient_id={p103.id}", headers=headers)
        assert res.status_code == 403

        # 4. Other patient location history -> 403
        res = client.get(f"/api/v1/monitoring/locations/history?patient_id={p103.id}", headers=headers)
        assert res.status_code == 403

        # 5. Heatmaps -> 403
        res = client.get("/api/v1/gis/heatmaps", headers=headers)
        assert res.status_code == 403

        # 6. Exposure analysis -> 403
        res = client.get("/api/v1/gis/exposure-analysis", headers=headers)
        assert res.status_code == 403

        # 7. Summary reports -> 403
        res = client.get("/api/v1/gis/reports/summary", headers=headers)
        assert res.status_code == 403
