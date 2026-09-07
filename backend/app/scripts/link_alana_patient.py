from app.db.session import SessionLocal
from app.models.user import User, Role
from app.schemas.auth import RoleEnum
from app.models.patient import Patient
from app.models.monitoring import LocationConsent, MonitoringSession, ConsentStatus, SessionStatus
from app.models.disease import Disease, DiseaseCase, CaseStatus
from app.core.security import get_password_hash
from datetime import datetime, timezone, timedelta
import uuid

def setup_alana():
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.pseudo_id == 'PAT-USER-143').first()
        if not patient:
            # Fallback to any patient named Alana
            patient = db.query(Patient).filter(Patient.full_name.ilike('%alana%')).first()
        if not patient:
            print("Patient Alana not found")
            return

        print(f"Found patient: {patient.id} - {patient.full_name} ({patient.pseudo_id})")

        role_patient = db.query(Role).filter(Role.name == RoleEnum.PATIENT.value).first()
        user = db.query(User).filter(User.email == 'alana@healthwatch.org').first()
        if not user:
            user = User(
                email='alana@healthwatch.org',
                hashed_password=get_password_hash('Patient@HealthWatch2026'),
                full_name='Alana P J',
                role_id=role_patient.id,
                is_active=True,
                is_superuser=False,
            )
            db.add(user)
            db.flush()
            print("Created user: alana@healthwatch.org")
        else:
            print("User alana@healthwatch.org already exists")

        # Link user to patient
        patient.user_id = user.id

        # Location Consent
        now = datetime.now(timezone.utc)
        consent = db.query(LocationConsent).filter(LocationConsent.patient_id == patient.id).first()
        if not consent:
            consent = LocationConsent(
                patient_id=patient.id,
                consent_status=ConsentStatus.ACTIVE.value,
                consent_version='v1.0',
                monitoring_start=now - timedelta(hours=1),
                monitoring_end=now + timedelta(days=14),
                purpose='Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)',
            )
            db.add(consent)
            db.flush()
            print("Created active LocationConsent")
        else:
            consent.consent_status = ConsentStatus.ACTIVE.value
            consent.monitoring_end = now + timedelta(days=14)
            print("Updated LocationConsent to ACTIVE")

        # Monitoring Session
        session = db.query(MonitoringSession).filter(MonitoringSession.patient_id == patient.id).first()
        if not session:
            session = MonitoringSession(
                patient_id=patient.id,
                consent_id=consent.id,
                status=SessionStatus.ACTIVE.value,
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(days=14),
            )
            db.add(session)
            print("Created active MonitoringSession")
        else:
            session.status = SessionStatus.ACTIVE.value
            session.end_time = now + timedelta(days=14)
            print("Updated MonitoringSession to ACTIVE")

        # Disease Case
        case = db.query(DiseaseCase).filter(DiseaseCase.patient_id == patient.id).first()
        if not case:
            dengue = db.query(Disease).filter(Disease.code == 'DENGUE-01').first()
            if dengue:
                case = DiseaseCase(
                    patient_id=patient.id,
                    disease_id=dengue.id,
                    case_status=CaseStatus.CONFIRMED.value,
                    severity='MILD',
                    diagnosis_date=now.date(),
                    clinical_notes='Under observation in Elavally Ward 17, Thrissur',
                    source='SIMULATED',
                )
                db.add(case)
                print("Created active DiseaseCase")

        db.commit()
        print(f"SUCCESS: Successfully linked Alana P J ({patient.pseudo_id}) with user alana@healthwatch.org")
    finally:
        db.close()

if __name__ == '__main__':
    setup_alana()
