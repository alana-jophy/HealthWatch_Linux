import sys
import uuid
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, "/app")

from app.core.config import settings
from app.models.spatial import District, LocalBody, Ward
from app.models.patient import Patient
from app.models.user import User, Role
from app.models.disease import Disease, DiseaseCase, CaseStatus
from app.models.monitoring import LocationConsent, MonitoringSession, PatientLocation
from app.models.exposure import ExposureEvent

ALANA_PATIENT_ID = uuid.UUID("150e177d-4052-4e74-aa99-e20fb3606d89")

def main():
    print("=" * 70)
    print("HEALTHWATCH — CLEAN DATABASE: KEEP ONLY ONE PATIENT")
    print("=" * 70)

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Fetch Alana's record
        alana = session.query(Patient).filter(Patient.id == ALANA_PATIENT_ID).first()
        if not alana:
            # Fallback by pseudo_id or name
            alana = session.query(Patient).filter(Patient.pseudo_id == "PAT-USER-143").first()
        if not alana:
            alana = session.query(Patient).filter(Patient.full_name.ilike("%alana%")).first()

        if not alana:
            print("ERROR: Could not locate Alana P J patient record!")
            sys.exit(1)

        print(f"Target Patient Identified: {alana.full_name} ({alana.pseudo_id}, ID: {alana.id})")

        # 2. Resolve official Kerala hierarchy for Alana
        thrissur_dist = session.query(District).filter(District.code == "KL-TCR").first()
        elavally_lb = session.query(LocalBody).filter(LocalBody.code == "G08037").first()
        if not elavally_lb:
            elavally_lb = session.query(LocalBody).filter(LocalBody.name.ilike("%elavally%")).first()

        padivarambu_ward = None
        if elavally_lb:
            padivarambu_ward = session.query(Ward).filter(
                Ward.local_body_id == elavally_lb.id,
                Ward.ward_number == 17
            ).first()

        alana.district_id = thrissur_dist.id if thrissur_dist else alana.district_id
        alana.district_name = thrissur_dist.name if thrissur_dist else "Thrissur"
        alana.local_body_id = elavally_lb.id if elavally_lb else alana.local_body_id
        alana.local_body_name = elavally_lb.name if elavally_lb else "Elavally Grama Panchayat"
        alana.ward_id = padivarambu_ward.id if padivarambu_ward else alana.ward_id
        alana.ward_name = padivarambu_ward.name if padivarambu_ward else "PADIVARAMBU"
        alana.ward_number = 17
        alana.address = "PULIKKOTTIL HOUSE, PADIVARAMBU, ELAVALLY"
        alana.contact_number = "+91-81369-63623"
        alana.is_active = True
        session.commit()

        alana_id_str = str(alana.id)
        alana_user_id = alana.user_id

        # 3. Clean up related records for all other patients
        print("Cleaning up secondary data for all other patients...")

        # Delete exposure events involving other patients
        deleted_exposures = session.query(ExposureEvent).filter(
            (ExposureEvent.patient_a_id != alana.id) | (ExposureEvent.patient_b_id != alana.id)
        ).delete(synchronize_session=False)

        # Delete disease cases for other patients
        deleted_cases = session.query(DiseaseCase).filter(
            DiseaseCase.patient_id != alana.id
        ).delete(synchronize_session=False)

        # Delete patient locations for other patients
        deleted_locs = session.query(PatientLocation).filter(
            PatientLocation.patient_id != alana.id
        ).delete(synchronize_session=False)

        # Delete monitoring sessions for other patients
        deleted_sessions = session.query(MonitoringSession).filter(
            MonitoringSession.patient_id != alana.id
        ).delete(synchronize_session=False)

        # Delete location consents for other patients
        deleted_consents = session.query(LocationConsent).filter(
            LocationConsent.patient_id != alana.id
        ).delete(synchronize_session=False)

        session.commit()
        print(f"Removed: {deleted_cases} disease cases, {deleted_locs} telemetry points, {deleted_sessions} sessions, {deleted_consents} consents.")

        # 4. Delete all other patients
        deleted_patients = session.query(Patient).filter(
            Patient.id != alana.id
        ).delete(synchronize_session=False)
        session.commit()
        print(f"Deleted {deleted_patients} patient records. Active patient count: {session.query(Patient).count()}")

        # 5. Clean up unused patient User accounts
        patient_role = session.query(Role).filter(Role.name == "PATIENT").first()
        if patient_role:
            deleted_users = session.query(User).filter(
                User.role_id == patient_role.id,
                User.id != alana_user_id
            ).delete(synchronize_session=False)
            session.commit()
            print(f"Deleted {deleted_users} extraneous patient user accounts.")

        # 6. Ensure Alana has an active DiseaseCase
        existing_case = session.query(DiseaseCase).filter(DiseaseCase.patient_id == alana.id).first()
        if not existing_case:
            dengue = session.query(Disease).filter(Disease.code == "DENGUE-01").first()
            officer_user = session.query(User).filter(User.email == "officer@test.com").first()
            new_case = DiseaseCase(
                id=uuid.uuid4(),
                patient_id=alana.id,
                disease_id=dengue.id if dengue else None,
                reported_by_id=officer_user.id if officer_user else None,
                ward_id=alana.ward_id,
                case_status=CaseStatus.CONFIRMED.value,
                severity="MILD",
                diagnosis_date=datetime.date.today(),
                latitude=10.570261,
                longitude=76.079231,
                source="PATIENT_GPS",
                clinical_notes="Patient monitoring active via phone GPS in Elavally Grama Panchayat, Ward 17 (Padivarambu).",
            )
            session.add(new_case)
            session.commit()
            print("Created surveillance disease case for Alana P J.")

        # 7. Final Verification
        total_patients = session.query(Patient).count()
        total_locations = session.query(PatientLocation).filter(PatientLocation.patient_id == alana.id).count()
        p = session.query(Patient).first()

        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"Total Patients in Database: {total_patients}")
        print(f"Sole Active Patient: {p.full_name} ({p.pseudo_id})")
        print(f"Login Email: {p.user.email if p.user else 'No linked user'}")
        print(f"District: {p.district_name}")
        print(f"Local Body: {p.local_body_name} (Code: {p.local_body.code if p.local_body else 'N/A'})")
        print(f"Ward: Ward #{p.ward_number} - {p.ward_name} (Code: {p.ward.ward_code if p.ward else 'N/A'})")
        print(f"Real Phone GPS Points: {total_locations} points preserved")
        print("=" * 70)

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
