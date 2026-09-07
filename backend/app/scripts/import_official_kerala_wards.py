import csv
import os
import sys
import uuid
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, "/app")

from app.core.config import settings
from app.db.base import Base
from app.models.spatial import District, LocalBody, Ward
from app.models.patient import Patient
from app.models.disease import DiseaseCase

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "official_kerala_wards.csv")

def format_lb_name(name: str, lb_type: str) -> str:
    clean = name.strip()
    clean_lower = clean.lower()
    
    if lb_type == "Corporation":
        if "corporation" not in clean_lower:
            return f"{clean} Municipal Corporation"
        return clean
    elif lb_type == "Municipality":
        if "municipality" not in clean_lower:
            return f"{clean} Municipality"
        return clean
    elif lb_type == "Grama Panchayat":
        if "panchayat" not in clean_lower:
            return f"{clean} Grama Panchayat"
        return clean
    elif lb_type == "Block Panchayat":
        if "panchayat" not in clean_lower:
            return f"{clean} Block Panchayat"
        return clean
    elif lb_type == "District Panchayat":
        if "panchayat" not in clean_lower:
            return f"{clean} District Panchayat"
        return clean
    return clean

def import_official_wards():
    start_time = time.time()
    print("=" * 70)
    print("HEALTHWATCH — OFFICIAL KERALA WARDS IMPORT")
    print("Source: Kerala State Election Commission / NIC Trend Data")
    print(f"Reading dataset: {CSV_PATH}")
    print("=" * 70)

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing official ward dataset at {CSV_PATH}")

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Ensure columns and indexes exist in DB
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS code VARCHAR(50);"))
            conn.execute(text("ALTER TABLE wards ADD COLUMN IF NOT EXISTS ward_code VARCHAR(50);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_local_bodies_code ON local_bodies(code);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_wards_ward_code ON wards(ward_code);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_wards_lb_wn ON wards(local_body_id, ward_number);"))
            conn.commit()

        # Step 1: Map all 14 districts
        districts = session.query(District).all()
        district_map = {d.name.strip().lower(): d for d in districts}
        print(f"Loaded {len(districts)} existing districts from DB.")

        # Read CSV rows
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)

        print(f"Loaded {len(csv_rows)} rows from CSV dataset.")

        # Step 2: Extract distinct Local Bodies
        lb_records = {}
        for r in csv_rows:
            dist_name = r["district"].strip()
            lb_code = r["lb_code"].strip()
            lb_type = r["lb_type"].strip()
            lb_name = r["lb_name"].strip()
            
            if lb_code not in lb_records:
                lb_records[lb_code] = {
                    "district_name": dist_name,
                    "code": lb_code,
                    "type": lb_type,
                    "name": lb_name,
                    "full_name": format_lb_name(lb_name, lb_type),
                }

        print(f"Found {len(lb_records)} distinct local bodies in dataset.")

        # Load existing local bodies
        existing_lbs = session.query(LocalBody).all()
        lb_code_to_model = {lb.code: lb for lb in existing_lbs if lb.code}
        lb_name_to_model = {(lb.district_id, lb.name.strip().lower()): lb for lb in existing_lbs}

        created_lbs = 0
        updated_lbs = 0
        lb_id_map = {}  # lb_code -> local_body.id

        for lb_code, info in lb_records.items():
            dist_obj = district_map.get(info["district_name"].lower())
            if not dist_obj:
                print(f"WARNING: District {info['district_name']} not found in DB!")
                continue

            target_lb = None
            if lb_code in lb_code_to_model:
                target_lb = lb_code_to_model[lb_code]
            else:
                # Try exact match by name and district
                key1 = (dist_obj.id, info["full_name"].lower())
                key2 = (dist_obj.id, info["name"].lower())
                if key1 in lb_name_to_model:
                    target_lb = lb_name_to_model[key1]
                elif key2 in lb_name_to_model:
                    target_lb = lb_name_to_model[key2]

            if target_lb:
                target_lb.code = lb_code
                target_lb.body_type = info["type"]
                target_lb.name = info["full_name"]
                target_lb.source = "OFFICIAL_SEC"
                updated_lbs += 1
                lb_id_map[lb_code] = target_lb.id
            else:
                new_id = uuid.uuid4()
                new_lb = LocalBody(
                    id=new_id,
                    district_id=dist_obj.id,
                    code=lb_code,
                    name=info["full_name"],
                    body_type=info["type"],
                    source="OFFICIAL_SEC",
                )
                session.add(new_lb)
                created_lbs += 1
                lb_id_map[lb_code] = new_id
                lb_code_to_model[lb_code] = new_lb


        session.commit()
        
        # Clean up any legacy demo local bodies that have no official code
        legacy_lbs = session.query(LocalBody).filter(LocalBody.code.is_(None)).all()
        for leg in legacy_lbs:
            # Check if there is an official counterpart
            official_counterpart = session.query(LocalBody).filter(
                LocalBody.district_id == leg.district_id,
                LocalBody.code.isnot(None)
            ).first()
            if official_counterpart:
                session.query(Patient).filter(Patient.local_body_id == leg.id).update(
                    {"local_body_id": official_counterpart.id}
                )
            session.delete(leg)
        session.commit()

        print(f"Local bodies synced: {created_lbs} created, {updated_lbs} updated. Total active: {session.query(LocalBody).count()}")


        # Step 3: Clean up any legacy demo wards without official ward_code
        session.execute(text("UPDATE disease_cases SET ward_id = NULL WHERE ward_id IN (SELECT id FROM wards WHERE ward_code IS NULL);"))
        session.execute(text("UPDATE patients SET ward_id = NULL WHERE ward_id IN (SELECT id FROM wards WHERE ward_code IS NULL);"))
        session.execute(text("DELETE FROM wards WHERE ward_code IS NULL;"))
        session.commit()

        # Step 4: Bulk insert all 23,573 official wards if not already imported
        existing_official_wards_count = session.query(Ward).filter(Ward.ward_code.isnot(None)).count()
        print(f"Existing official wards in DB: {existing_official_wards_count}")

        lb_first_ward = {} # lb_id -> ward_id

        if existing_official_wards_count < 20000:
            # Clear any partial wards
            session.execute(text("UPDATE disease_cases SET ward_id = NULL WHERE ward_id IS NOT NULL;"))
            session.execute(text("UPDATE patients SET ward_id = NULL WHERE ward_id IS NOT NULL;"))
            session.execute(text("DELETE FROM wards;"))
            session.commit()

            print(f"Inserting {len(csv_rows)} official wards via bulk insert...")
            ward_insert_mappings = []

            for r in csv_rows:
                lb_code = r["lb_code"].strip()
                lb_id = lb_id_map.get(lb_code)
                if not lb_id:
                    continue

                w_id = uuid.uuid4()
                ward_code = r["ward_code"].strip()
                ward_no = int(r["ward_no"].strip()) if r["ward_no"].strip().isdigit() else 1
                ward_name = r["ward_name"].strip()

                ward_insert_mappings.append({
                    "id": w_id,
                    "local_body_id": lb_id,
                    "ward_code": ward_code,
                    "ward_number": ward_no,
                    "name": ward_name,
                    "source": "OFFICIAL_SEC"
                })
                if lb_id not in lb_first_ward or ward_no == 1:
                    lb_first_ward[lb_id] = w_id

            # Insert in chunks of 5000 for high performance
            chunk_size = 5000
            for i in range(0, len(ward_insert_mappings), chunk_size):
                chunk = ward_insert_mappings[i : i + chunk_size]
                session.bulk_insert_mappings(Ward, chunk)
                session.commit()
                print(f"  Inserted wards {i + 1} to {min(i + chunk_size, len(ward_insert_mappings))}...")
        else:
            print("Official wards already present in database.")
            # Map first ward per local body for patient linking
            first_wards = session.query(Ward).filter(Ward.ward_number == 1).all()
            for w in first_wards:
                lb_first_ward[w.local_body_id] = w.id


        total_wards_in_db = session.query(Ward).count()
        print(f"Official wards imported successfully: {total_wards_in_db} records.")

        # Step 5: Re-link patients to official wards based on their local body or name
        # If patient had Palayam in TVM, match to official TVM Palayam ward!
        tvm_palayam = session.query(Ward).filter(Ward.ward_code == "C01001039").first()
        patients = session.query(Patient).all()
        relinked_patients = 0
        for p in patients:
            if p.local_body_id and p.local_body_id in lb_first_ward:
                if p.full_name and "alana" in p.full_name.lower() and tvm_palayam and p.district and "thiruvananthapuram" in p.district.name.lower():
                    p.ward_id = tvm_palayam.id
                else:
                    p.ward_id = lb_first_ward[p.local_body_id]
                relinked_patients += 1

        # Re-link disease cases
        cases = session.query(DiseaseCase).all()
        for c in cases:
            if c.patient and c.patient.ward_id:
                c.ward_id = c.patient.ward_id

        session.commit()
        print(f"Relinked {relinked_patients} patient records to authentic official wards.")

        # Step 6: Summary and District breakdown
        print("\n" + "=" * 70)
        print("IMPORT VERIFICATION REPORT")
        print("=" * 70)
        print(f"{'District':<22} | {'Local Bodies':<14} | {'Wards':<8}")
        print("-" * 70)

        with engine.connect() as conn:
            res = conn.execute(text("""
                SELECT 
                    d.name AS district, 
                    COUNT(DISTINCT lb.id) AS local_bodies, 
                    COUNT(w.id) AS wards
                FROM districts d
                LEFT JOIN local_bodies lb ON lb.district_id = d.id
                LEFT JOIN wards w ON w.local_body_id = lb.id
                GROUP BY d.name
                ORDER BY d.name;
            """)).fetchall()

            for row in res:
                print(f"{row[0]:<22} | {row[1]:<14} | {row[2]:<8}")

        elapsed = time.time() - start_time
        print("=" * 70)
        print(f"Import completed successfully in {elapsed:.2f} seconds!")
        print("=" * 70)

    except Exception as e:
        session.rollback()
        print(f"ERROR during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    import_official_wards()
