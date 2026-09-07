import uuid
from loguru import logger
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.models.user import Role, User
from app.models.spatial import District, LocalBody, Ward
from app.schemas.auth import RoleEnum
from app.core.security import get_password_hash


def migrate_patient_accounts():
    """Ensure every patient in the database has a linked User account and spatial foreign keys."""
    db = SessionLocal()
    try:
        role_patient = db.query(Role).filter(Role.name == RoleEnum.PATIENT.value).first()
        if not role_patient:
            role_patient = Role(name=RoleEnum.PATIENT.value, description="Monitored Patient Role")
            db.add(role_patient)
            db.flush()

        patients = db.query(Patient).all()
        logger.info(f"Checking {len(patients)} total patients for user accounts and spatial links...")

        linked_count = 0
        spatial_linked_count = 0

        # Load spatial lookups
        districts = {d.name.lower(): d for d in db.query(District).all()}
        local_bodies = db.query(LocalBody).all()
        wards = db.query(Ward).all()

        for p in patients:
            # 1. Link or Create User Account
            if not p.user_id:
                account_email = f"{p.pseudo_id.lower()}@patient.healthwatch.org"
                user = db.query(User).filter(User.email == account_email).first()
                if not user:
                    user = User(
                        email=account_email,
                        hashed_password=get_password_hash(f"Patient@{p.pseudo_id}"),
                        full_name=p.full_name,
                        role_id=role_patient.id,
                        is_active=p.is_active,
                        is_superuser=False,
                    )
                    db.add(user)
                    db.flush()
                p.user_id = user.id
                linked_count += 1

            # 2. Link Administrative Spatial Hierarchy if missing
            if not p.district_id and p.district_name:
                matched_d = districts.get(p.district_name.lower())
                if matched_d:
                    p.district_id = matched_d.id
                    spatial_linked_count += 1

            if not p.local_body_id and p.district_id:
                matched_lb = next(
                    (lb for lb in local_bodies if lb.district_id == p.district_id and (p.local_body_name.lower() in lb.name.lower() or lb.name.lower() in p.local_body_name.lower())),
                    None,
                )
                if not matched_lb:
                    matched_lb = next((lb for lb in local_bodies if lb.district_id == p.district_id), None)
                if matched_lb:
                    p.local_body_id = matched_lb.id
                    p.local_body_name = matched_lb.name

            if not p.ward_id and p.local_body_id:
                matched_w = next(
                    (w for w in wards if w.local_body_id == p.local_body_id and w.ward_number == p.ward_number),
                    None,
                )
                if not matched_w:
                    matched_w = next((w for w in wards if w.local_body_id == p.local_body_id), None)
                if matched_w:
                    p.ward_id = matched_w.id
                    p.ward_number = matched_w.ward_number

        db.commit()
        logger.info(f"Migration complete: Linked {linked_count} patient user accounts, resolved {spatial_linked_count} spatial IDs.")
    except Exception as exc:
        db.rollback()
        logger.error(f"Migration error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_patient_accounts()
