import sys
sys.path.insert(0, "/app")
from app.db.session import SessionLocal
from app.models.user import User
from app.models.patient import Patient
from app.models.spatial import Ward
from app.core.security import get_password_hash
import uuid

def main():
    db = SessionLocal()
    email = "patient.synth101@healthwatch.org"
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        u = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=get_password_hash("Patient@HealthWatch2026"),
            full_name="Demo Patient (SYNTH-101)",
            is_active=True,
            is_superuser=False
        )
        db.add(u)
        db.flush()
        w = db.query(Ward).first()
        p = Patient(
            id=uuid.uuid4(),
            user_id=u.id,
            pseudo_id="PAT-SYNTH-101",
            full_name="Demo Patient (SYNTH-101)",
            age=28,
            gender="FEMALE",
            district_id=w.local_body.district_id,
            local_body_id=w.local_body_id,
            ward_id=w.id,
            has_phone=True,
            contact_number="9876543210"
        )
        db.add(p)
        db.commit()
        print(f"Created {email} successfully.")
    else:
        print(f"{email} already exists.")

if __name__ == "__main__":
    main()
