import requests
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}", flush=True)

def run_tests():
    session = requests.Session()

    log("Step 1: Check backend health...")
    r = session.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    log("Backend health check PASSED", "SUCCESS")

    log("Step 2: Login as Public Health Officer...")
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "officer.surveillance@healthwatch.org",
        "password": "Officer@HealthWatch2026"
    })
    if r.status_code != 200:
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "officer@test.com",
            "password": "Officer@123"
        })
    assert r.status_code == 200, f"Officer login failed: {r.text}"
    officer_token = r.json()["access_token"]
    officer_headers = {"Authorization": f"Bearer {officer_token}"}
    log("Officer login PASSED", "SUCCESS")

    log("Step 3: Fetch Disease Catalog...")
    r = session.get(f"{BASE_URL}/api/v1/diseases/", headers=officer_headers)
    assert r.status_code == 200, f"Fetch diseases failed: {r.text}"
    diseases_data = r.json()
    diseases = diseases_data.get("items", diseases_data) if isinstance(diseases_data, dict) else diseases_data
    assert len(diseases) > 0, "No diseases found"
    log(f"Found {len(diseases)} registered diseases in catalog:")
    for d in diseases[:5]:
        log(f"  - {d['name']} ({d['code']})")
    
    cholera = next((d for d in diseases if "CHOLERA" in d['code'].upper() or "CHOLERA" in d['name'].upper()), diseases[1] if len(diseases) > 1 else diseases[0])
    lepto = next((d for d in diseases if "LEPTO" in d['code'].upper() or "ZIKA" in d['code'].upper() or "HEPATITIS" in d['code'].upper()), diseases[-1])
    log(f"Selected test disease 1: {cholera['name']} ({cholera['code']})")
    log(f"Selected test disease 2: {lepto['name']} ({lepto['code']})")

    log("Step 4: Fetch location hierarchy (District -> Local Body -> Ward)...")
    r = session.get(f"{BASE_URL}/api/v1/gis/districts", headers=officer_headers)
    assert r.status_code == 200
    districts = r.json()
    district_id = districts[0]["id"]
    
    r = session.get(f"{BASE_URL}/api/v1/gis/local-bodies?district_id={district_id}", headers=officer_headers)
    assert r.status_code == 200
    local_bodies = r.json()
    local_body_id = local_bodies[0]["id"]

    r = session.get(f"{BASE_URL}/api/v1/gis/wards?local_body_id={local_body_id}", headers=officer_headers)
    assert r.status_code == 200
    wards = r.json()
    ward_id = wards[0]["id"]
    log(f"Selected Location: District={districts[0]['name']}, LocalBody={local_bodies[0]['name']}, Ward #{wards[0]['ward_number']} ({wards[0]['name']})")

    log("Step 5: Test Phone Validation (Reject non-10 digits)...")
    bad_payload = {
        "pseudo_id": "PAT-BAD-01",
        "full_name": "Test Bad Phone",
        "age": 30,
        "gender": "OTHER",
        "has_phone": True,
        "contact_number": "12345",  # Invalid! Only 5 digits
        "disease_id": cholera["id"],
        "district_id": district_id,
        "local_body_id": local_body_id,
        "ward_id": ward_id,
        "address": "Test Bad Phone Lane",
        "email": "badphone@test.com",
        "initial_password": "Password123!"
    }
    r = session.post(f"{BASE_URL}/api/v1/patients/", json=bad_payload, headers=officer_headers)
    assert r.status_code == 422, f"Expected 422 for invalid phone, got {r.status_code}: {r.text}"
    assert "10 numeric digits" in r.text or "contact_number" in r.text
    log("Validation correctly rejected non-10-digit phone number (HTTP 422)", "SUCCESS")

    run_id = int(time.time())
    p1_email = f"rahul_{run_id}@healthwatch.org"
    p2_email = f"lakshmi_{run_id}@healthwatch.org"

    log("Step 6: Register Patient 1 with 10-digit phone and Cholera disease...")
    p1_payload = {
        "pseudo_id": f"PAT-RAHUL-{run_id % 10000}",
        "full_name": f"Rahul Nair {run_id % 1000}",
        "age": 28,
        "gender": "MALE",
        "has_phone": True,
        "contact_number": "9847123456",  # Exactly 10 digits
        "disease_id": cholera["id"],
        "disease_name": cholera["name"],
        "district_id": district_id,
        "local_body_id": local_body_id,
        "ward_id": ward_id,
        "address": "TC 14/220, Medical College Road",
        "email": p1_email,
        "initial_password": "Patient@HealthWatch2026"
    }
    r = session.post(f"{BASE_URL}/api/v1/patients/", json=p1_payload, headers=officer_headers)
    assert r.status_code == 201, f"Failed to create Patient 1: {r.text}"
    p1 = r.json()

    assert p1["has_phone"] is True
    assert p1["contact_number"] == "9847123456"
    assert p1["disease_name"] == cholera["name"]
    log(f"Patient 1 Registered: PseudoID={p1['pseudo_id']}, Disease={p1['disease_name']}, Phone={p1['contact_number']}", "SUCCESS")

    log("Step 7: Register Patient 2 WITHOUT phone (has_phone=False) and Zika Virus...")
    p2_payload = {
        "pseudo_id": f"PAT-LAKSHMI-{run_id % 10000}",
        "full_name": f"Lakshmi Amma {run_id % 1000}",
        "age": 64,
        "gender": "FEMALE",
        "has_phone": False,
        "contact_number": None,
        "disease_id": lepto["id"],
        "disease_name": lepto["name"],
        "district_id": district_id,
        "local_body_id": local_body_id,
        "ward_id": ward_id,
        "address": "Kowdiar Ward, House #45",
        "email": p2_email,
        "initial_password": "Patient@HealthWatch2026"
    }
    r = session.post(f"{BASE_URL}/api/v1/patients/", json=p2_payload, headers=officer_headers)
    assert r.status_code == 201, f"Failed to create Patient 2: {r.text}"
    p2 = r.json()

    assert p2["has_phone"] is False
    assert p2["contact_number"] is None
    assert p2["disease_name"] == lepto["name"]
    log(f"Patient 2 Registered: PseudoID={p2['pseudo_id']}, Disease={p2['disease_name']}, Phone={p2['contact_number']} (No fake phone)", "SUCCESS")

    log("Step 8: Test Officer Filter by Disease and Phone Availability...")
    r_filter_phone = session.get(f"{BASE_URL}/api/v1/patients/?has_phone=true", headers=officer_headers)
    assert r_filter_phone.status_code == 200
    for pat in r_filter_phone.json()["items"]:
        assert pat["has_phone"] is True, "Found patient without phone in has_phone=true filter"

    r_filter_no_phone = session.get(f"{BASE_URL}/api/v1/patients/?has_phone=false", headers=officer_headers)
    assert r_filter_no_phone.status_code == 200
    for pat in r_filter_no_phone.json()["items"]:
        assert pat["has_phone"] is False, "Found patient with phone in has_phone=false filter"
    log("Officer Phone Availability filters working correctly", "SUCCESS")

    log("Step 9: Test Patient 1 Login & Data Isolation...")
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": p1_email,
        "password": "Patient@HealthWatch2026"
    })
    assert r.status_code == 200, f"Patient 1 login failed: {r.text}"
    p1_token = r.json()["access_token"]
    p1_headers = {"Authorization": f"Bearer {p1_token}"}

    # Patient 1 Profile
    r = session.get(f"{BASE_URL}/api/v1/patients/me", headers=p1_headers)
    assert r.status_code == 200
    p1_profile = r.json()
    assert p1_profile["pseudo_id"] == p1["pseudo_id"]
    assert p1_profile["disease_name"] == cholera["name"]
    assert p1_profile["contact_number"] == "9847123456"
    log(f"Patient 1 sees own profile with disease '{p1_profile['disease_name']}' (NOT Dengue)", "SUCCESS")

    # Patient 1 Cases
    r = session.get(f"{BASE_URL}/api/v1/cases/me", headers=p1_headers)
    assert r.status_code == 200
    p1_cases = r.json()["items"]
    assert len(p1_cases) > 0
    assert p1_cases[0]["disease"]["name"] == cholera["name"]
    log(f"Patient 1 cases list accurately shows '{p1_cases[0]['disease']['name']}'", "SUCCESS")

    # Patient 1 cannot access officer patient list (HTTP 403)
    r = session.get(f"{BASE_URL}/api/v1/patients/", headers=p1_headers)
    assert r.status_code == 403, f"Expected 403 Forbidden for patient on admin endpoint, got {r.status_code}"
    log("Patient 1 strictly blocked from officer /api/v1/patients/ (HTTP 403 Forbidden)", "SUCCESS")

    log("Step 10: Test Patient 2 Login & Data Isolation...")
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": p2_email,
        "password": "Patient@HealthWatch2026"
    })
    assert r.status_code == 200, f"Patient 2 login failed: {r.text}"
    p2_token = r.json()["access_token"]
    p2_headers = {"Authorization": f"Bearer {p2_token}"}

    # Patient 2 Profile
    r = session.get(f"{BASE_URL}/api/v1/patients/me", headers=p2_headers)
    assert r.status_code == 200
    p2_profile = r.json()
    assert p2_profile["pseudo_id"] == p2["pseudo_id"]
    assert p2_profile["disease_name"] == lepto["name"]
    assert p2_profile["has_phone"] is False
    assert p2_profile["contact_number"] is None
    log(f"Patient 2 sees own profile with disease '{p2_profile['disease_name']}' and no phone", "SUCCESS")

    log("Step 11: Test Configurable GPS Sampling Cadence...")
    # First grant consent for Patient 1
    r_consent = session.post(f"{BASE_URL}/api/v1/monitoring/consent/grant", json={
        "consent_type": "LOCATION_TRACKING",
        "purpose": "Public Health Disease Surveillance"
    }, headers=p1_headers)
    log(f"Consent grant response: {r_consent.status_code}")

    # Patient 1 starts monitoring session with 5-minute sampling cadence
    session_payload = {
        "sampling_interval_minutes": 5,
        "duration_hours": 24
    }
    r = session.post(f"{BASE_URL}/api/v1/monitoring/sessions/start", json=session_payload, headers=p1_headers)
    assert r.status_code in [200, 201], f"Failed to start monitoring session: {r.text}"
    sess = r.json()
    assert sess["sampling_interval_minutes"] == 5
    log(f"Monitoring session created with sampling_interval_minutes={sess['sampling_interval_minutes']}", "SUCCESS")

    # Patient 1 checks monitoring status
    r = session.get(f"{BASE_URL}/api/v1/monitoring/status", headers=p1_headers)
    assert r.status_code == 200
    mon_status = r.json()
    assert mon_status["sampling_interval_minutes"] == 5
    log(f"Patient monitoring status reflects cadence: {mon_status['sampling_interval_minutes']} minutes", "SUCCESS")

    log("Step 12: Test Patient Movement Roadmap Data & Hierarchy...")
    # Add a telemetry observation for Patient 1
    obs_payload = {
        "session_id": sess["id"],
        "latitude": 8.524139,
        "longitude": 76.936638,
        "accuracy_meters": 8.5,
        "source": "SIMULATED",
        "is_mock_provider": True
    }
    r = session.post(f"{BASE_URL}/api/v1/monitoring/locations/submit", json=obs_payload, headers=p1_headers)
    assert r.status_code in [200, 201], f"Failed to log telemetry: {r.text}"
    log("Telemetry location observation submitted successfully", "SUCCESS")

    # Query roadmap as Officer
    r = session.get(f"{BASE_URL}/api/v1/monitoring/roadmap?patient_id={p1['id']}", headers=officer_headers)
    assert r.status_code == 200, f"Failed to get roadmap: {r.text}"
    roadmap = r.json()
    assert roadmap["disease_name"] == cholera["name"]
    assert len(roadmap["observations"]) > 0
    latest_obs = roadmap["observations"][-1]
    assert latest_obs["district_name"] == districts[0]["name"]
    assert latest_obs["local_body_name"] == local_bodies[0]["name"]
    assert latest_obs["ward_number"] == wards[0]["ward_number"]
    log(f"Roadmap verified: Disease={roadmap['disease_name']}, District={latest_obs['district_name']}, LocalBody={latest_obs['local_body_name']}, Ward=#{latest_obs['ward_number']} ({latest_obs['ward_name']})", "SUCCESS")

    log("\n==================================================", "SUCCESS")
    log("ALL 12 END-TO-END SPECIFICATION CHECKS PASSED!", "SUCCESS")
    log("==================================================", "SUCCESS")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        log(f"Test failed with error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
