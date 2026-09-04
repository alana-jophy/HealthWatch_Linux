import csv
import datetime
import io
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.disease import Disease
from app.models.spatial import District

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Ensure database tables and synthetic demo data exist."""
    init_db()


def get_token(email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# HealthWatch Step 18: Surveillance Report Generation Test Suite
# ==============================================================================

class TestReportGeneration:

    @classmethod
    def setup_class(cls):
        cls.officer_token = get_token("officer.surveillance@healthwatch.org", "Officer@HealthWatch2026")
        cls.admin_token = get_token("admin@healthwatch.org", "Admin@HealthWatch2026")
        cls.worker_token = get_token("worker.field01@healthwatch.org", "Worker@HealthWatch2026")
        cls.patient_token = get_token("patient.synth101@healthwatch.org", "Patient@HealthWatch2026")

        cls.officer_headers = {"Authorization": f"Bearer {cls.officer_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.worker_headers = {"Authorization": f"Bearer {cls.worker_token}"}
        cls.patient_headers = {"Authorization": f"Bearer {cls.patient_token}"}

        db = SessionLocal()
        try:
            cls.dengue = db.query(Disease).filter(Disease.code == "DENGUE-01").first()
            cls.tvm_district = db.query(District).filter(District.code == "KL-TVM").first()
        finally:
            db.close()

    # --------------------------------------------------------------------------
    # 1. ACCESS CONTROL AND RBAC ENFORCEMENT
    # --------------------------------------------------------------------------
    def test_officer_and_admin_authorized_for_reports(self):
        """Public Health Officers and Admins have full access to generate and preview reports."""
        res_officer = client.get("/api/v1/reports/preview?report_type=comprehensive", headers=self.officer_headers)
        assert res_officer.status_code == 200, f"Officer preview rejected: {res_officer.text}"
        data = res_officer.json()
        assert "columns" in data
        assert "rows" in data

        res_admin = client.get("/api/v1/reports/preview?report_type=comprehensive", headers=self.admin_headers)
        assert res_admin.status_code == 200, f"Admin preview rejected: {res_admin.text}"

    def test_patient_forbidden_from_reports(self):
        """Patients are strictly blocked from generating or previewing administrative reports."""
        res_prev = client.get("/api/v1/reports/preview?report_type=comprehensive", headers=self.patient_headers)
        assert res_prev.status_code == 403
        msg = res_prev.json().get("error", {}).get("message") or res_prev.json().get("detail", "")
        assert "Access denied" in msg

        res_exp = client.get("/api/v1/reports/export?format=pdf&report_type=comprehensive", headers=self.patient_headers)
        assert res_exp.status_code == 403

    def test_health_worker_forbidden_from_state_reports(self):
        """Field health workers are forbidden from state-wide epidemiological export digests."""
        res_prev = client.get("/api/v1/reports/preview?report_type=comprehensive", headers=self.worker_headers)
        assert res_prev.status_code == 403
        msg = res_prev.json().get("error", {}).get("message") or res_prev.json().get("detail", "")
        assert "Access denied" in msg

        res_exp = client.get("/api/v1/reports/export?format=csv&report_type=comprehensive", headers=self.worker_headers)
        assert res_exp.status_code == 403

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests are rejected with HTTP 401."""
        res = client.get("/api/v1/reports/preview")
        assert res.status_code == 401

    # --------------------------------------------------------------------------
    # 2. CSV EXPORT COMPLIANCE (RFC 4180)
    # --------------------------------------------------------------------------
    def test_csv_export_format_and_headers(self):
        """CSV export must return valid text/csv format with metadata headers and tabular columns."""
        res = client.get(
            "/api/v1/reports/export?format=csv&report_type=disease_statistics",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert "attachment" in res.headers["content-disposition"]
        assert ".csv" in res.headers["content-disposition"]

        content = res.text
        assert "# HEALTHWATCH EPIDEMIOLOGICAL SURVEILLANCE REPORT" in content
        assert "Disease Code,Disease Name" in content

        # Verify RFC 4180 parsing with standard csv reader
        reader = csv.reader(io.StringIO(content))
        data_rows = [row for row in reader if row and not row[0].startswith("#")]
        assert len(data_rows) >= 2  # Header row + at least 1 data row

    # --------------------------------------------------------------------------
    # 3. PDF EXPORT COMPLIANCE (VALID MAGIC BYTES & STREAM)
    # --------------------------------------------------------------------------
    def test_pdf_export_format_and_magic_bytes(self):
        """PDF export must return valid application/pdf byte stream starting with %PDF- header."""
        res = client.get(
            "/api/v1/reports/export?format=pdf&report_type=comprehensive",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment" in res.headers["content-disposition"]
        assert ".pdf" in res.headers["content-disposition"]

        pdf_bytes = res.content
        assert len(pdf_bytes) > 1000, "PDF byte stream is suspiciously empty"
        assert pdf_bytes.startswith(b"%PDF-"), "File is missing the standard PDF magic header '%PDF-'"

    # --------------------------------------------------------------------------
    # 4. ALL 8 REPORT TYPES COMPILATION AND EXPORT
    # --------------------------------------------------------------------------
    @pytest.mark.parametrize("report_type", [
        "disease_statistics",
        "district_cases",
        "local_body_cases",
        "ward_cases",
        "date_range_cases",
        "hotspot_summary",
        "potential_exposures",
        "monitoring_summary",
    ])
    def test_all_eight_report_types_exportable(self, report_type):
        """Every one of the 8 required report types must preview and export in CSV and PDF."""
        # 1. Preview
        res_prev = client.get(
            f"/api/v1/reports/preview?report_type={report_type}",
            headers=self.officer_headers,
        )
        assert res_prev.status_code == 200
        pdata = res_prev.json()
        assert len(pdata["columns"]) > 0
        assert pdata["report_type"] == report_type

        # 2. CSV Export
        res_csv = client.get(
            f"/api/v1/reports/export?format=csv&report_type={report_type}",
            headers=self.officer_headers,
        )
        assert res_csv.status_code == 200
        assert res_csv.headers["content-type"].startswith("text/csv")
        assert len(res_csv.text) > 50

        # 3. PDF Export
        res_pdf = client.get(
            f"/api/v1/reports/export?format=pdf&report_type={report_type}",
            headers=self.officer_headers,
        )
        assert res_pdf.status_code == 200
        assert res_pdf.content.startswith(b"%PDF-")

    # --------------------------------------------------------------------------
    # 5. DYNAMIC FILTERING ON REPORTS
    # --------------------------------------------------------------------------
    def test_filter_by_disease_in_report(self):
        """Filtering reports by disease scopes the report to that pathogen."""
        if not self.dengue:
            pytest.skip("Dengue disease record not found")

        res = client.get(
            f"/api/v1/reports/preview?report_type=disease_statistics&disease_id={self.dengue.id}",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["rows"]) == 1
        assert data["rows"][0]["Disease Code"] == self.dengue.code

    def test_filter_by_district_in_report(self):
        """Filtering reports by district scopes caseload counts."""
        if not self.tvm_district:
            pytest.skip("TVM district record not found")

        res = client.get(
            f"/api/v1/reports/preview?report_type=district_cases&district_id={self.tvm_district.id}",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()
        for row in data["rows"]:
            if row["District Code"] == self.tvm_district.code:
                assert int(row["Total Cases"]) > 0

    # --------------------------------------------------------------------------
    # 6. PRIVACY PROTECTION (NO SENSITIVE PII)
    # --------------------------------------------------------------------------
    def test_privacy_no_personal_identifiable_information(self):
        """Reports must omit phone numbers, street addresses, and raw private coordinates."""
        res = client.get(
            "/api/v1/reports/preview?report_type=date_range_cases",
            headers=self.officer_headers,
        )
        assert res.status_code == 200
        data = res.json()

        # Check column headers for prohibited personal data
        columns_lower = [c.lower() for c in data["columns"]]
        assert "phone" not in columns_lower
        assert "contact" not in columns_lower
        assert "address" not in columns_lower
        assert "street" not in columns_lower
        assert "latitude" not in columns_lower
        assert "longitude" not in columns_lower

        # Check rows: Patient identifiers must be pseudo IDs (e.g., PAT-...)
        for row in data["rows"]:
            pid = str(row.get("Patient ID", ""))
            assert pid.startswith("PAT-") or pid == "ANON"
