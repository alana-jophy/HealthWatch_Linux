#!/usr/bin/env bash
set -e

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"patient.synth101@healthwatch.org","password":"Patient@HealthWatch2026"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "1. Testing /patients/me..."
curl -s http://localhost:8000/api/v1/patients/me -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Patient:', d['pseudo_id'], d['full_name'], 'Ward:', d['ward_number'])"

echo "2. Testing /cases/me..."
curl -s http://localhost:8000/api/v1/cases/me -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Total cases:', d['total'], 'Case status:', d['items'][0]['case_status'], 'Severity:', d['items'][0]['severity'])"

echo "3. Testing /monitoring/status..."
curl -s http://localhost:8000/api/v1/monitoring/status -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Consent:', d['has_active_consent'], 'Session:', d['has_active_session'], 'Sampling:', d['sampling_interval_description'])"

echo "4. Testing /monitoring/locations/history..."
curl -s http://localhost:8000/api/v1/monitoring/locations/history -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print('History count:', d['total'], 'Recent observation:', d['items'][0]['recorded_at'], 'Lat/Lng:', d['items'][0]['latitude'], d['items'][0]['longitude'])"

echo "5. Testing Cross-Patient Authorization (Patient 101 -> Patient 102)..."
P2_ID=$(docker compose exec -T db psql -U healthwatch_user -d healthwatch_db -t -A -c "SELECT id FROM patients WHERE pseudo_id = 'PAT-SYNTH-102' LIMIT 1;")
echo "Patient 102 ID: $P2_ID"

HTTP_ROADMAP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/monitoring/roadmap?patient_id=$P2_ID" -H "Authorization: Bearer $TOKEN")
echo "Cross-Patient Roadmap Access HTTP Code: $HTTP_ROADMAP"

HTTP_LOCS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/monitoring/locations/history?patient_id=$P2_ID" -H "Authorization: Bearer $TOKEN")
echo "Cross-Patient Location History HTTP Code: $HTTP_LOCS"

HTTP_PROFILE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/patients/$P2_ID" -H "Authorization: Bearer $TOKEN")
echo "Cross-Patient Patient Record HTTP Code: $HTTP_PROFILE"

HTTP_CASES=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/cases/?patient_id=$P2_ID" -H "Authorization: Bearer $TOKEN")
echo "Cross-Patient Cases Filter HTTP Code: $HTTP_CASES"
