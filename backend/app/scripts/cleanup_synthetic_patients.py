import sys
import uuid
import datetime
from sqlalchemy import create_engine, text, or_
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, "/app")

from app.core.config import settings
from app.models.patient import Patient
from app.models.user import User
from app.models.disease import DiseaseCase
from app.models.monitoring import LocationConsent, MonitoringSession, PatientLocation
from app.models.exposure import ExposureEvent

PAT_111_ID = uuid.UUID("35b86c94-7225-44ec-83f1-179318bad18e")
SEPT_8_OBS_IDS = [
    uuid.UUID("76e7c0b8-4607-4a5c-b7e5-d6e5c86fd6fe"),
    uuid.UUID("10e8b953-3733-4d35-b3b7-5f9d5bf5a593"),
    uuid.UUID("8937613d-9a35-458d-91ca-f51c11bba48c"),
    uuid.UUID("50e6f364-28fd-4c95-a69f-b280d8ca5392"),
    uuid.UUID("37786c12-2d0b-46e8-9efd-8236c08a5e04"),
]

def main():
    print("=" * 70)
    print("HEALTHWATCH — RECOVER HISTORICAL LOCATIONS & DATABASE CLEANUP")
    print("=" * 70)

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Verify PAT-111
        pat_111 = session.query(Patient).filter(Patient.id == PAT_111_ID).first()
        if not pat_111:
            pat_111 = session.query(Patient).filter(Patient.pseudo_id == "PAT-111").first()
        assert pat_111 is not None, "PAT-111 must exist in the database!"
        print(f"Verified Real Patient: {pat_111.full_name} ({pat_111.pseudo_id}, ID: {pat_111.id})")

        # 2. Find any non-PAT-111 demo/synthetic patients
        demo_patients = session.query(Patient).filter(
            Patient.id != pat_111.id,
            or_(
                Patient.pseudo_id.like("PAT-SYNTH-%"),
                Patient.pseudo_id.like("PAT-DEMO-%"),
                Patient.pseudo_id == "PAT-USER-143",
                Patient.pseudo_id.like("PAT-AUTO-%"),
                Patient.pseudo_id.like("PAT-TEST-%"),
                Patient.pseudo_id.like("PAT-SYS-%"),
                Patient.pseudo_id == "PAT-AUDIT-B"
            )
        ).all()

        demo_patient_ids = [p.id for p in demo_patients]
        print(f"Found {len(demo_patient_ids)} remaining demo/synthetic patients to delete.")

        if demo_patient_ids:
            session.query(ExposureEvent).filter(
                or_(
                    ExposureEvent.patient_a_id.in_(demo_patient_ids),
                    ExposureEvent.patient_b_id.in_(demo_patient_ids)
                )
            ).delete(synchronize_session=False)

            session.query(PatientLocation).filter(
                PatientLocation.patient_id.in_(demo_patient_ids)
            ).delete(synchronize_session=False)

            session.query(MonitoringSession).filter(
                MonitoringSession.patient_id.in_(demo_patient_ids)
            ).delete(synchronize_session=False)

            session.query(LocationConsent).filter(
                LocationConsent.patient_id.in_(demo_patient_ids)
            ).delete(synchronize_session=False)

            session.query(DiseaseCase).filter(
                DiseaseCase.patient_id.in_(demo_patient_ids)
            ).delete(synchronize_session=False)

            session.query(Patient).filter(
                Patient.id.in_(demo_patient_ids)
            ).delete(synchronize_session=False)

            session.commit()
            print("Successfully deleted remaining demo patients and their dependent data.")

        # 3. Final Assertions & Verification
        session.expire_all()

        pat_111_locs = session.query(PatientLocation).filter(
            PatientLocation.patient_id == pat_111.id
        ).order_by(PatientLocation.recorded_at.asc()).all()

        sept6_count = sum(1 for l in pat_111_locs if str(l.recorded_at.date()) == "2026-09-06")
        sept7_count = sum(1 for l in pat_111_locs if str(l.recorded_at.date()) == "2026-09-07")
        sept8_count = sum(1 for l in pat_111_locs if str(l.recorded_at.date()) == "2026-09-08")

        print("=" * 70)
        print("VERIFICATION RESULTS:")
        print(f"Total PAT-111 Locations: {len(pat_111_locs)}")
        print(f"  - September 6, 2026: {sept6_count} points")
        print(f"  - September 7, 2026: {sept7_count} points")
        print(f"  - September 8, 2026: {sept8_count} points (Original 5 preserved)")
        print("=" * 70)

        assert sept6_count == 5, f"Expected 5 Sept 6 points, got {sept6_count}"
        assert sept7_count == 39, f"Expected 39 Sept 7 points, got {sept7_count}"
        assert sept8_count == 5, f"Expected 5 Sept 8 points, got {sept8_count}"
        assert len(pat_111_locs) == 49, f"Expected 49 total points, got {len(pat_111_locs)}"

        # Check that original 5 September 8 IDs are exact
        current_sept8_ids = [l.id for l in pat_111_locs if str(l.recorded_at.date()) == "2026-09-08"]
        for orig_id in SEPT_8_OBS_IDS:
            assert orig_id in current_sept8_ids, f"Original September 8 ID {orig_id} missing!"

        # Check Disease Case
        case = session.query(DiseaseCase).filter(DiseaseCase.patient_id == pat_111.id).first()
        assert case is not None, "PAT-111 DiseaseCase must exist!"
        print(f"PAT-111 Disease Case: {case.disease.name if case.disease else 'Dengue'} ({case.case_status})")

        # Check User Link
        user = session.query(User).filter(User.id == pat_111.user_id).first()
        assert user is not None and user.email == "alanapj161@gmail.com", f"User link mismatch: {user}"
        print(f"PAT-111 Linked User: {user.email}")

        # Check remaining patients in DB
        remaining_patients = session.query(Patient).all()
        print(f"Remaining Patients in DB: {len(remaining_patients)} -> {[p.pseudo_id for p in remaining_patients]}")
        assert all("SYNTH" not in p.pseudo_id and "DEMO" not in p.pseudo_id for p in remaining_patients)

        print("ALL DATABASE RECOVERY AND CLEANUP CHECKS PASSED!")

    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
