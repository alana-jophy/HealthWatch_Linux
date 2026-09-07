import requests

login_resp = requests.post(
    'http://127.0.0.1:8000/api/auth/login',
    json={'email': 'officer@test.com', 'password': 'Officer@123'}
)
tok = login_resp.json()['access_token']
h = {'Authorization': f'Bearer {tok}'}

# Query roadmap for PAT-SYNTH-101
r = requests.get(
    'http://127.0.0.1:8000/api/v1/monitoring/roadmap',
    params={'pseudo_id': 'PAT-SYNTH-101', 'date': '2026-09-05'},
    headers=h
)
print('Status:', r.status_code)
data = r.json()
obs = data.get('observations', [])
print('Obs count:', len(obs))
for o in obs:
    print(f"ID: {o.get('id')} | Time: {o.get('recorded_at')} | Lat: {o.get('latitude')} | Lng: {o.get('longitude')} | Acc: {o.get('accuracy')} | Source: {o.get('source')}")
