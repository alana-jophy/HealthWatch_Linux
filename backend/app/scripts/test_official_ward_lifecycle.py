import requests
import sys

def main():
    print("Testing end-to-end official ward patient lifecycle...")
    login_resp = requests.post('http://localhost:8000/api/auth/login', json={'email': 'officer@test.com', 'password': 'Officer@123'})
    if login_resp.status_code != 200:
        print("Login failed:", login_resp.text)
        sys.exit(1)

    token = login_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 1. Look up Alappuzha Municipality & Thumpoly Ward
    dist = requests.get('http://localhost:8000/api/v1/gis/districts', headers=headers).json()
    alp_dist = next(d for d in dist if d['code'] == 'KL-ALP')

    lbs = requests.get(f'http://localhost:8000/api/v1/gis/local-bodies?district_id={alp_dist["id"]}', headers=headers).json()
    alpy_muni = next(lb for lb in lbs if lb['code'] == 'M04014')

    wards = requests.get(f'http://localhost:8000/api/v1/gis/local-bodies/{alpy_muni["id"]}/wards', headers=headers).json()
    thumpoly = next(w for w in wards if w['ward_code'] == 'M04014001')
    kommady = next(w for w in wards if w['ward_code'] == 'M04014002')

    print(f"District: {alp_dist['name']} ({alp_dist['id']})")
    print(f"Local Body: {alpy_muni['name']} ({alpy_muni['code']})")
    print(f"Ward 1: {thumpoly['name']} ({thumpoly['ward_code']})")
    print(f"Ward 2: {kommady['name']} ({kommady['ward_code']})")

    # 2. Create Patient in Thumpoly
    pat_payload = {
        'pseudo_id': 'PAT-TEST-ALPY-01',
        'full_name': 'Test Official Ward Subject',
        'email': 'patient.alpy01@test.com',
        'initial_password': 'Patient@Alpy123',
        'age': 29,
        'gender': 'MALE',
        'contact_number': '+91-98470-11223',
        'address': 'Beach Road, Thumpoly',
        'district_id': alp_dist['id'],
        'district_name': alp_dist['name'],
        'local_body_id': alpy_muni['id'],
        'local_body_name': alpy_muni['name'],
        'ward_id': thumpoly['id'],
        'ward_name': thumpoly['name'],
        'ward_number': thumpoly['ward_number']
    }

    create_resp = requests.post('http://localhost:8000/api/v1/patients/', json=pat_payload, headers=headers)
    print('Create Patient Status:', create_resp.status_code)
    created = create_resp.json()
    print(f"Created Patient: {created.get('pseudo_id')}, Ward: {created.get('ward_name')} ({created.get('ward_code')})")
    assert created.get('ward_code') == 'M04014001'
    assert created.get('ward_name') == 'THUMPOLY'

    # 3. Update Patient to Ward 2 (Kommady)
    edit_payload = {
        'ward_id': kommady['id'],
        'ward_name': kommady['name'],
        'ward_number': kommady['ward_number']
    }
    update_resp = requests.put(f'http://localhost:8000/api/v1/patients/{created["id"]}', json=edit_payload, headers=headers)
    print('Update Patient Status:', update_resp.status_code)
    updated = update_resp.json()
    print(f"Updated Patient Ward: {updated.get('ward_name')} ({updated.get('ward_code')})")
    assert updated.get('ward_code') == 'M04014002'
    assert updated.get('ward_name') == 'KOMMADY'

    # 4. Patient Login with New Account
    pat_login = requests.post('http://localhost:8000/api/auth/login', json={'email': 'patient.alpy01@test.com', 'password': 'Patient@Alpy123'})
    print('Patient Login Status:', pat_login.status_code)
    assert pat_login.status_code == 200

    # Clean up test patient
    del_resp = requests.delete(f'http://localhost:8000/api/v1/patients/{created["id"]}', headers=headers)
    print('Test patient delete status:', del_resp.status_code)
    print("All integration tests passed successfully!")

if __name__ == "__main__":
    main()
