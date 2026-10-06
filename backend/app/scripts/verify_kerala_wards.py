import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

from app.core.config import settings
from app.models.spatial import District, LocalBody, Ward

def verify_kerala_wards():
    print("=" * 72)
    print("HEALTHWATCH — KERALA ADMINISTRATIVE HIERARCHY DATA COMPLETENESS CHECK")
    print("=" * 72)

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. District Check (All 14)
        districts = session.query(District).order_by(District.name.asc()).all()
        print(f"\n[1] Districts Check: Found {len(districts)} / 14 required districts.")
        if len(districts) != 14:
            print(f"  FAILED: Expected 14 districts, found {len(districts)}")
            sys.exit(1)
        else:
            print("  PASS: All 14 Kerala districts are present.")

        # 2. Local Body Referential Integrity Check
        total_lbs = session.query(LocalBody).count()
        orphaned_lbs = session.query(LocalBody).filter(
            ~LocalBody.district_id.in_(session.query(District.id))
        ).count()
        print(f"\n[2] Local Bodies Integrity Check: Total = {total_lbs}, Orphaned (invalid district) = {orphaned_lbs}")
        if orphaned_lbs > 0:
            print(f"  FAILED: Found {orphaned_lbs} local bodies with invalid district foreign keys!")
            sys.exit(1)
        else:
            print(f"  PASS: All {total_lbs} local bodies have valid district foreign keys.")

        # 3. Ward Referential Integrity Check
        total_wards = session.query(Ward).count()
        orphaned_wards = session.query(Ward).filter(
            ~Ward.local_body_id.in_(session.query(LocalBody.id))
        ).count()
        print(f"\n[3] Wards Integrity Check: Total = {total_wards}, Orphaned (invalid local body) = {orphaned_wards}")
        if orphaned_wards > 0:
            print(f"  FAILED: Found {orphaned_wards} wards with invalid local body foreign keys!")
            sys.exit(1)
        else:
            print(f"  PASS: All {total_wards} wards have valid local body foreign keys.")

        # 4. Duplicate Ward Code Check
        with engine.connect() as conn:
            dup_codes = conn.execute(text("""
                SELECT ward_code, COUNT(*) 
                FROM wards 
                WHERE ward_code IS NOT NULL 
                GROUP BY ward_code 
                HAVING COUNT(*) > 1;
            """)).fetchall()
            print(f"\n[4] Duplicate Ward Codes: Found {len(dup_codes)}")
            if dup_codes:
                print(f"  FAILED: Duplicate ward codes detected: {dup_codes[:5]}")
                sys.exit(1)
            else:
                print("  PASS: 0 duplicate ward codes found across entire database.")

        # 5. Duplicate Ward Records per Local Body
        with engine.connect() as conn:
            dup_wards_in_lb = conn.execute(text("""
                SELECT local_body_id, ward_number, COUNT(*)
                FROM wards
                GROUP BY local_body_id, ward_number
                HAVING COUNT(*) > 1;
            """)).fetchall()
            print(f"\n[5] Duplicate Ward Number in Same Local Body: Found {len(dup_wards_in_lb)}")
            if dup_wards_in_lb:
                print(f"  FAILED: Duplicate ward numbers within local body: {dup_wards_in_lb[:5]}")
                sys.exit(1)
            else:
                print("  PASS: Every local body has distinct, valid ward numbers.")

        # 6. Ward Names & Codes Populated Check
        empty_names = session.query(Ward).filter((Ward.name == None) | (Ward.name == "")).count()
        empty_codes = session.query(Ward).filter((Ward.ward_code == None) | (Ward.ward_code == "")).count()
        print(f"\n[6] Empty Names: {empty_names} | Missing Official Codes: {empty_codes}")
        if empty_names > 0 or empty_codes > 0:
            print("  FAILED: Found wards with empty names or codes!")
            sys.exit(1)
        else:
            print("  PASS: 100% of wards have non-empty official names and codes.")

        # 7. Official District Breakdown Table (Database Computed)
        print("\n" + "=" * 72)
        print("DATABASE AUDIT REPORT: KERALA ADMINISTRATIVE HIERARCHY")
        print("=" * 72)
        print(f"{'District':<24} | {'Local Bodies':<16} | {'Wards':<10}")
        print("-" * 72)

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

            total_dist_count = 0
            total_lb_count = 0
            total_ward_count = 0

            for row in res:
                total_dist_count += 1
                total_lb_count += row[1]
                total_ward_count += row[2]
                print(f"{row[0]:<24} | {row[1]:<16} | {row[2]:<10}")

            print("-" * 72)
            print(f"{'TOTAL (14 Districts)':<24} | {total_lb_count:<16} | {total_ward_count:<10}")
            print("=" * 72)

    finally:
        session.close()

if __name__ == "__main__":
    verify_kerala_wards()
