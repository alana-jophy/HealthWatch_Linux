import requests

login_resp = requests.post(
    'http://127.0.0.1:8000/api/auth/login',
    json={'email': 'alana@healthwatch.org', 'password': 'Patient@HealthWatch2026'}
)
tok = login_resp.json()['access_token']
h = {'Authorization': f'Bearer {tok}'}

# Patient querying roadmap without parameters (should get own records)
r = requests.get(
    'http://127.0.0.1:8000/api/v1/monitoring/roadmap',
    headers=h
)
print('Alana Status:', r.status_code)
data = r.json()
obs = data.get('observations', [])
print('Obs count:', len(obs))
for o in obs:
    print(f"ID: {o.get('id')} | Time: {o.get('recorded_at')} | Lat: {o.get('latitude')} | Lng: {o.get('longitude')} | Acc: {o.get('accuracy')} | Source: {o.get('source')}")
