import csv
import urllib.request
import os

URL = "https://raw.githubusercontent.com/opendatakerala/LSGD2025-Results-Data/main/trend_detailed_results_2025.csv"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "official_kerala_wards.csv")

def main():
    print(f"Downloading official Kerala ward data from {URL} ...")
    req = urllib.request.urlopen(URL)
    lines = [line.decode("utf-8-sig", errors="ignore") for line in req.readlines()]
    reader = csv.DictReader(lines)

    districts = set()
    local_bodies = {}
    wards = {}

    for row in reader:
        dist = row["District"].strip()
        lb_type = row["LB_Type"].strip()
        lb_code = row["LB_Code"].strip()
        lb_name = row["LB_Name"].strip()
        ward_no_raw = row["Ward_No"].strip()
        ward_name = row["Ward_Name"].strip()

        if not dist or not lb_code or not ward_no_raw:
            continue

        districts.add(dist)

        if lb_code not in local_bodies:
            local_bodies[lb_code] = {
                "district": dist,
                "lb_type": lb_type,
                "lb_code": lb_code,
                "lb_name": lb_name,
            }

        # Canonical ward code: e.g. M04014001
        if ward_no_raw.startswith(lb_code):
            ward_code = ward_no_raw
            # Extract number from suffix
            suffix = ward_no_raw[len(lb_code):]
            ward_no = int(suffix) if suffix.isdigit() else 1
        else:
            ward_no = int(ward_no_raw) if ward_no_raw.isdigit() else 1
            ward_code = f"{lb_code}{str(ward_no).zfill(3)}"

        ward_key = (lb_code, ward_no)
        if ward_key not in wards:
            wards[ward_key] = {
                "district": dist,
                "lb_type": lb_type,
                "lb_code": lb_code,
                "lb_name": lb_name,
                "ward_no": ward_no,
                "ward_code": ward_code,
                "ward_name": ward_name,
            }

    print(f"Extracted: {len(districts)} districts, {len(local_bodies)} local bodies, {len(wards)} wards.")

    # Sort deterministically
    sorted_wards = sorted(
        wards.values(),
        key=lambda x: (x["district"], x["lb_type"], x["lb_name"], x["ward_no"])
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["district", "lb_type", "lb_code", "lb_name", "ward_no", "ward_code", "ward_name"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for w in sorted_wards:
            writer.writerow(w)

    print(f"Successfully written {len(sorted_wards)} rows to {OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(OUTPUT_PATH)} bytes")

if __name__ == "__main__":
    main()
