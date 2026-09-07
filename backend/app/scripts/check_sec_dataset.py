import csv
import urllib.request

url = "https://raw.githubusercontent.com/opendatakerala/LSGD2025-Results-Data/main/trend_detailed_results_2025.csv"
print(f"Downloading dataset from {url} ...")
req = urllib.request.urlopen(url)
lines = [line.decode("utf-8-sig", errors="ignore") for line in req.readlines()]
reader = csv.DictReader(lines)

districts = set()
lbs = {}
wards = {}
lb_types = set()
dist_lb_map = {}
dist_ward_map = {}

for row in reader:
    dist = row["District"].strip()
    lb_type = row["LB_Type"].strip()
    lb_code = row["LB_Code"].strip()
    lb_name = row["LB_Name"].strip()
    ward_no = row["Ward_No"].strip()
    ward_name = row["Ward_Name"].strip()

    if not dist or not lb_code or not ward_no:
        continue

    districts.add(dist)
    lb_types.add(lb_type)

    if lb_code not in lbs:
        lbs[lb_code] = {
            "code": lb_code,
            "name": lb_name,
            "type": lb_type,
            "district": dist,
        }

    ward_code = f"{lb_code}{ward_no.zfill(3)}" if not ward_no.startswith(lb_code) else ward_no
    ward_key = (lb_code, ward_no)
    if ward_key not in wards:
        wards[ward_key] = {
            "lb_code": lb_code,
            "ward_code": ward_code,
            "ward_number": int(ward_no) if ward_no.isdigit() else 1,
            "ward_name": ward_name,
            "district": dist,
        }

    if dist not in dist_lb_map:
        dist_lb_map[dist] = set()
        dist_ward_map[dist] = set()
    dist_lb_map[dist].add(lb_code)
    dist_ward_map[dist].add((lb_code, ward_no))

print("=" * 60)
print(f"Total Districts: {len(districts)}")
print(f"Districts: {sorted(list(districts))}")
print(f"LB Types: {lb_types}")
print(f"Total Local Bodies: {len(lbs)}")
print(f"Total Unique Wards: {len(wards)}")
print("=" * 60)
print(f"{'District':<22} | {'Local Bodies':<14} | {'Wards':<8}")
print("-" * 60)
for d in sorted(districts):
    print(f"{d:<22} | {len(dist_lb_map[d]):<14} | {len(dist_ward_map[d]):<8}")
print("=" * 60)

# Check sample local bodies
print("\nSample: Alappuzha Municipality (M04014) Wards:")
alpy_wards = {k: v for k, v in wards.items() if v["lb_code"] == "M04014"}
print(f"Total Wards in Alappuzha Municipality: {len(alpy_wards)}")
for w in sorted(alpy_wards.values(), key=lambda x: x["ward_number"])[:5]:
    print(f"  Ward {w['ward_number']}: Code={w['ward_code']}, Name={w['ward_name']}")

print("\nSample: Kochi Municipal Corporation (C07001) or Corporation in Ernakulam:")
kochi_lbs = [l for l in lbs.values() if l["district"] == "Ernakulam" and l["type"] == "Corporation"]
for l in kochi_lbs:
    c_wards = [w for w in wards.values() if w["lb_code"] == l["code"]]
    print(f"  {l['name']} ({l['code']}): {len(c_wards)} wards")
    for w in sorted(c_wards, key=lambda x: x["ward_number"])[:3]:
        print(f"    Ward {w['ward_number']}: Code={w['ward_code']}, Name={w['ward_name']}")

