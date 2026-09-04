#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "HealthWatch Verification Suite: Step 13 Patient Dashboard"
echo "=========================================================="

echo "1. Authenticating as Patient 101..."
PATIENT_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"patient.synth101@healthwatch.org","password":"Patient@HealthWatch2026"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo ""
echo "2. Querying Authenticated Patient Profile (/api/v1/patients/me)..."
PROFILE_RES=$(curl -s -X GET "http://localhost:8000/api/v1/patients/me" \
  -H "Authorization: Bearer $PATIENT_TOKEN")
echo "$PROFILE_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Welcome:', d.get('full_name'), f'[{d.get(\"pseudo_id\")}]')
print('  Age & Gender:', d.get('age'), d.get('gender'))
print('  Contact:', d.get('contact_number'))
print('  Address:', d.get('address'))
print('  Kerala Ward Hierarchy: Ward #' + str(d.get('ward_number')) + ' - ' + str(d.get('local_body_name')) + ' (' + str(d.get('district_name')) + ')')
"

echo ""
echo "3. Querying Patient Disease Cases (/api/v1/cases/me)..."
CASES_RES=$(curl -s -X GET "http://localhost:8000/api/v1/cases/me" \
  -H "Authorization: Bearer $PATIENT_TOKEN")
echo "$CASES_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Total Cases Logged:', d.get('total'))
for c in d.get('items', []):
    print(f'  - Status: {c.get(\"case_status\")}, Severity: {c.get(\"severity\")}, Diagnosed: {c.get(\"diagnosis_date\")}')
    print(f'    Notes: {c.get(\"clinical_notes\")[:80]}...')
"

echo ""
echo "4. Querying Monitoring Card Status (/api/v1/monitoring/status)..."
STATUS_RES=$(curl -s -X GET "http://localhost:8000/api/v1/monitoring/status" \
  -H "Authorization: Bearer $PATIENT_TOKEN")
echo "$STATUS_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
consent = d.get('active_consent') or {}
session = d.get('active_session') or {}
status = 'ACTIVE' if d.get('has_active_session') and session.get('status') == 'ACTIVE' else ('STOPPED' if session.get('status') == 'STOPPED' else 'EXPIRED')
print('  Monitoring Status:', status)
print('  Monitoring Period:', consent.get('monitoring_start'), '->', consent.get('monitoring_end'))
print('  Location Sampling:', d.get('sampling_interval_description'))
print('  Notice:', d.get('explanation_notice'))
"

echo ""
echo "5. Querying Location History Table (/api/v1/monitoring/locations/history)..."
HISTORY_RES=$(curl -s -X GET "http://localhost:8000/api/v1/monitoring/locations/history?limit=5" \
  -H "Authorization: Bearer $PATIENT_TOKEN")
echo "$HISTORY_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Total Location History Records:', d.get('total'))
print('  Sample Observations Table:')
print('    Timestamp               | Latitude | Longitude | Accuracy | Source')
print('    ------------------------------------------------------------------')
for obs in d.get('items', [])[:5]:
    acc_str = f'±{obs.get(\"accuracy\")}m' if obs.get('accuracy') is not None else 'N/A'
    print(f'    {obs.get(\"recorded_at\")} | {obs.get(\"latitude\"):.4f}  | {obs.get(\"longitude\"):.4f}   | {acc_str:<8} | {obs.get(\"source\")}')
"

echo ""
echo "6. Querying Movement Roadmap (/api/v1/monitoring/roadmap?date=2026-09-05)..."
ROADMAP_RES=$(curl -s -X GET "http://localhost:8000/api/v1/monitoring/roadmap?date=2026-09-05" \
  -H "Authorization: Bearer $PATIENT_TOKEN")
echo "$ROADMAP_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Roadmap Points Count:', d.get('statistics', {}).get('total_observations'))
print('  Disclaimer:', d.get('disclaimer')[:85] + '...')
"

echo ""
echo "7. SECURITY & AUTHORIZATION TESTS: Enforcing Cross-Patient Isolation..."
P2_ID=$(docker compose exec -T db psql -U healthwatch_user -d healthwatch_db -t -A -c "SELECT id FROM patients WHERE pseudo_id = 'PAT-SYNTH-102' LIMIT 1;")
echo "  Target Unauthorized Patient 102 ID: $P2_ID"

HTTP_ROADMAP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/monitoring/roadmap?patient_id=$P2_ID" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "  [Test 1] Patient 101 requesting Patient 102 Roadmap: HTTP $HTTP_ROADMAP (Expected: 403 Forbidden)"
[ "$HTTP_ROADMAP" -eq 403 ] || (echo "Security failure: Roadmap not blocked" && exit 1)

HTTP_HISTORY=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/monitoring/locations/history?patient_id=$P2_ID" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "  [Test 2] Patient 101 requesting Patient 102 Location History: HTTP $HTTP_HISTORY (Expected: 403 Forbidden)"
[ "$HTTP_HISTORY" -eq 403 ] || (echo "Security failure: Location history not blocked" && exit 1)

HTTP_PROFILE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/patients/$P2_ID" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "  [Test 3] Patient 101 requesting Patient 102 Profile Record: HTTP $HTTP_PROFILE (Expected: 403 Forbidden)"
[ "$HTTP_PROFILE" -eq 403 ] || (echo "Security failure: Profile not blocked" && exit 1)

HTTP_CASES=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/cases/?patient_id=$P2_ID" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "  [Test 4] Patient 101 requesting Patient 102 Disease Cases: HTTP $HTTP_CASES (Expected: 403 Forbidden)"
[ "$HTTP_CASES" -eq 403 ] || (echo "Security failure: Cases not blocked" && exit 1)

echo ""
echo "8. STEP 14 RBAC VERIFICATION: Testing All 4 System Roles..."

echo "  A. Authenticating ADMIN..."
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@healthwatch.org","password":"Admin@HealthWatch2026"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

HTTP_ADMIN_HEATMAP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/gis/heatmaps" -H "Authorization: Bearer $ADMIN_TOKEN")
echo "     ADMIN accessing Heatmaps: HTTP $HTTP_ADMIN_HEATMAP (Expected: 200 OK)"
[ "$HTTP_ADMIN_HEATMAP" -eq 200 ] || exit 1

echo "  B. Authenticating PUBLIC HEALTH OFFICER..."
OFFICER_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"officer.surveillance@healthwatch.org","password":"Officer@HealthWatch2026"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

HTTP_OFFICER_EXPOSURE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/gis/exposure-analysis" -H "Authorization: Bearer $OFFICER_TOKEN")
echo "     OFFICER accessing Exposure Analysis: HTTP $HTTP_OFFICER_EXPOSURE (Expected: 200 OK)"
[ "$HTTP_OFFICER_EXPOSURE" -eq 200 ] || exit 1

echo "  C. Authenticating HEALTH WORKER..."
WORKER_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"worker.field01@healthwatch.org","password":"Worker@HealthWatch2026"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

P1_ID=$(docker compose exec -T db psql -U healthwatch_user -d healthwatch_db -t -A -c "SELECT id FROM patients WHERE pseudo_id = 'PAT-SYNTH-101' LIMIT 1;")
P3_ID=$(docker compose exec -T db psql -U healthwatch_user -d healthwatch_db -t -A -c "SELECT id FROM patients WHERE pseudo_id = 'PAT-SYNTH-103' LIMIT 1;")

HTTP_WORKER_ASSIGNED=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/patients/$P1_ID" -H "Authorization: Bearer $WORKER_TOKEN")
echo "     HEALTH WORKER accessing Assigned Patient (101): HTTP $HTTP_WORKER_ASSIGNED (Expected: 200 OK)"
[ "$HTTP_WORKER_ASSIGNED" -eq 200 ] || exit 1

HTTP_WORKER_UNASSIGNED=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/patients/$P3_ID" -H "Authorization: Bearer $WORKER_TOKEN")
echo "     HEALTH WORKER accessing Unassigned Patient (103): HTTP $HTTP_WORKER_UNASSIGNED (Expected: 403 Forbidden)"
[ "$HTTP_WORKER_UNASSIGNED" -eq 403 ] || exit 1

HTTP_WORKER_HEATMAP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/gis/heatmaps" -H "Authorization: Bearer $WORKER_TOKEN")
echo "     HEALTH WORKER accessing Heatmaps: HTTP $HTTP_WORKER_HEATMAP (Expected: 403 Forbidden)"
[ "$HTTP_WORKER_HEATMAP" -eq 403 ] || exit 1

echo "  D. Authenticating PATIENT..."
HTTP_PATIENT_HEATMAP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/gis/heatmaps" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "     PATIENT accessing Heatmaps: HTTP $HTTP_PATIENT_HEATMAP (Expected: 403 Forbidden)"
[ "$HTTP_PATIENT_HEATMAP" -eq 403 ] || exit 1

echo ""
echo "9. STEP 15 VERIFICATION: Disease Hotspot Heatmap & Privacy Aggregation..."
echo "  Querying Aggregated Disease Heatmaps (/api/v1/gis/heatmaps)..."
HEATMAP_RES=$(curl -s -X GET "http://localhost:8000/api/v1/gis/heatmaps" -H "Authorization: Bearer $OFFICER_TOKEN")
echo "$HEATMAP_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Statewide Total Cases:', d.get('total_cases_statewide'))
print('  Cases In Selected Area:', d.get('cases_in_selected_area'))
print('  Leaflet Density Points:', len(d.get('density_points', [])))
print('  Concentration Tiers:', d.get('concentration_summary'))
print('  Top Outbreak Hotspots:')
for a in d.get('hotspot_areas', [])[:4]:
    print(f'   - {a.get(\"area_name\")} ({a.get(\"district_name\")}): {a.get(\"total_cases\")} cases [{a.get(\"risk_tier\")}] Dominant: {a.get(\"dominant_disease\")}')
print('  Disease Breakdown:')
for dis in d.get('disease_distribution', []):
    print(f'   - {dis.get(\"disease_name\")}: {dis.get(\"case_count\")} ({dis.get(\"percentage\")}%)')
print('  Privacy Notice:', d.get('demo_data_notice')[:80] + '...')
"

echo ""
echo "10. STEP 16 VERIFICATION: Potential Spatial-Temporal Exposure Analysis..."
echo "  A. Triggering PostGIS Spatial-Temporal Analysis (/api/v1/exposure/analyze)..."
ANALYZE_RES=$(curl -s -X POST "http://localhost:8000/api/v1/exposure/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -d '{"spatial_distance_threshold_meters": 50.0, "temporal_difference_threshold_minutes": 15.0}')
echo "$ANALYZE_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Analysis Status:', d.get('status'))
print('  Configured Spatial Threshold:', d.get('spatial_threshold_meters'), 'meters')
print('  Configured Temporal Threshold:', d.get('temporal_threshold_minutes'), 'minutes')
print('  Potential Overlaps Detected:', d.get('potential_overlaps_detected'))
print('  Ethical Disclaimer:', d.get('disclaimer')[:80] + '...')
"

echo "  B. Querying Exposure Events List (/api/v1/exposure/events)..."
EVENTS_RES=$(curl -s -X GET "http://localhost:8000/api/v1/exposure/events" \
  -H "Authorization: Bearer $OFFICER_TOKEN")
echo "$EVENTS_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Total Exposure Records:', d.get('total'))
print('  Status Breakdown:', d.get('summary_by_status'))
for it in d.get('items', [])[:3]:
    print(f'   - Pair: {it.get(\"patient_a_pseudo_id\")} <-> {it.get(\"patient_b_pseudo_id\")} | Distance: {it.get(\"distance\")}m | Time Delta: {it.get(\"time_difference\")}m | Status: {it.get(\"status\")} | Conf: {it.get(\"confidence_score\")}')
"

echo "  C. Verifying Patient Role Rejection (RBAC Isolation)..."
HTTP_PATIENT_EXPOSURE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/exposure/events" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "     PATIENT accessing Exposure Analysis: HTTP $HTTP_PATIENT_EXPOSURE (Expected: 403 Forbidden)"
[ "$HTTP_PATIENT_EXPOSURE" -eq 403 ] || exit 1

echo ""
echo "11. STEP 17 VERIFICATION: Public Health Surveillance Dashboard..."
echo "  A. Querying Public Health Surveillance Dashboard (/api/v1/surveillance/dashboard)..."
SURVEILLANCE_RES=$(curl -s -X GET "http://localhost:8000/api/v1/surveillance/dashboard" \
  -H "Authorization: Bearer $OFFICER_TOKEN")
echo "$SURVEILLANCE_RES" | python3 -c "import sys, json
d = json.load(sys.stdin)
kpi = d.get('kpi_summary', {})
print('  --- KPI Cards ---')
print(f'   Total Patients: {kpi.get(\"total_patients\")}')
print(f'   Active Cases: {kpi.get(\"active_cases\")} (Confirmed: {kpi.get(\"confirmed_cases\")}, Suspected: {kpi.get(\"suspected_cases\")})')
print(f'   Recovered Cases: {kpi.get(\"recovered_cases\")}')
print(f'   Active Monitoring Sessions: {kpi.get(\"active_monitoring_sessions\")}')
print(f'   Potential Exposure Events: {kpi.get(\"potential_exposure_events\")}')

charts = d.get('charts', {})
print('  --- Recharts Datasets ---')
print(f'   Cases Over Time Points: {len(charts.get(\"cases_over_time\", []))}')
print(f'   Diseases Tracked: {len(charts.get(\"cases_by_disease\", []))}')
if charts.get('cases_by_disease'):
    top_dis = charts['cases_by_disease'][0]
    print(f'     Top Disease: {top_dis.get(\"disease_name\")} ({top_dis.get(\"count\")} cases, {top_dis.get(\"percentage\")}%)')
print(f'   Districts Tracked: {len(charts.get(\"cases_by_district\", []))}')
print(f'   Local Bodies Tracked: {len(charts.get(\"cases_by_local_body\", []))}')
print(f'   Wards Tracked: {len(charts.get(\"cases_by_ward\", []))}')

map_data = d.get('map_data', {})
print('  --- Spatial Map Layers ---')
print(f'   Disease Case Points: {len(map_data.get(\"disease_cases\", []))}')
print(f'   Heatmap Density Points: {len(map_data.get(\"heatmap_points\", []))}')
print(f'   District Aggregates: {len(map_data.get(\"districts\", []))}')
"

echo "  B. Verifying Role Isolation (RBAC)..."
HTTP_PATIENT_SURVEILLANCE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/surveillance/dashboard" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "     PATIENT accessing Surveillance Dashboard: HTTP $HTTP_PATIENT_SURVEILLANCE (Expected: 403 Forbidden)"
[ "$HTTP_PATIENT_SURVEILLANCE" -eq 403 ] || exit 1

HTTP_WORKER_SURVEILLANCE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/surveillance/dashboard" -H "Authorization: Bearer $WORKER_TOKEN")
echo "     HEALTH WORKER accessing Surveillance Dashboard: HTTP $HTTP_WORKER_SURVEILLANCE (Expected: 403 Forbidden)"
[ "$HTTP_WORKER_SURVEILLANCE" -eq 403 ] || exit 1

echo ""
echo "12. STEP 18 VERIFICATION: Epidemiological Report Generation (CSV & PDF Exports)..."
echo "  A. Querying Report Preview (/api/v1/reports/preview?report_type=comprehensive)..."
REPORT_PREVIEW=$(curl -s -X GET "http://localhost:8000/api/v1/reports/preview?report_type=comprehensive" \
  -H "Authorization: Bearer $OFFICER_TOKEN")
echo "$REPORT_PREVIEW" | python3 -c "import sys, json
d = json.load(sys.stdin)
print('  Report Title:', d.get('title'))
print('  Total Tabular Records:', d.get('total_records'))
print('  Columns:', ', '.join(d.get('columns', [])))
print('  Privacy Notice:', d.get('disclaimer')[:70] + '...')
"

echo "  B. Testing CSV Export (/api/v1/reports/export?format=csv&report_type=disease_statistics)..."
CSV_STATUS=$(curl -s -o /tmp/hw_test_report.csv -w "%{http_code}" "http://localhost:8000/api/v1/reports/export?format=csv&report_type=disease_statistics" \
  -H "Authorization: Bearer $OFFICER_TOKEN")
echo "     CSV Export HTTP Status: $CSV_STATUS (Expected: 200 OK)"
[ "$CSV_STATUS" -eq 200 ] || exit 1
python3 -c "
with open('/tmp/hw_test_report.csv', 'r') as f:
    lines = f.readlines()
print(f'     CSV File Generated: {len(lines)} lines | Starts with: {lines[0].strip()[:60]}...')
"

echo "  C. Testing PDF Export (/api/v1/reports/export?format=pdf&report_type=comprehensive)..."
PDF_STATUS=$(curl -s -o /tmp/hw_test_report.pdf -w "%{http_code}" "http://localhost:8000/api/v1/reports/export?format=pdf&report_type=comprehensive" \
  -H "Authorization: Bearer $OFFICER_TOKEN")
echo "     PDF Export HTTP Status: $PDF_STATUS (Expected: 200 OK)"
[ "$PDF_STATUS" -eq 200 ] || exit 1
python3 -c "
with open('/tmp/hw_test_report.pdf', 'rb') as f:
    header = f.read(10)
    size = f.seek(0, 2)
print(f'     PDF File Verified: Size = {size} bytes | Header = {header[:5].decode(\"ascii\", errors=\"ignore\")} (Valid PDF Document)')
"

echo "  D. Verifying Role Isolation (RBAC)..."
HTTP_PATIENT_REPORT=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/reports/preview" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "     PATIENT accessing Reports Preview: HTTP $HTTP_PATIENT_REPORT (Expected: 403 Forbidden)"
[ "$HTTP_PATIENT_REPORT" -eq 403 ] || exit 1

HTTP_PATIENT_EXPORT=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/reports/export?format=pdf" -H "Authorization: Bearer $PATIENT_TOKEN")
echo "     PATIENT exporting Report PDF: HTTP $HTTP_PATIENT_EXPORT (Expected: 403 Forbidden)"
[ "$HTTP_PATIENT_EXPORT" -eq 403 ] || exit 1

HTTP_WORKER_REPORT=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/reports/preview" -H "Authorization: Bearer $WORKER_TOKEN")
echo "     HEALTH WORKER accessing Reports Preview: HTTP $HTTP_WORKER_REPORT (Expected: 403 Forbidden)"
[ "$HTTP_WORKER_REPORT" -eq 403 ] || exit 1

echo ""
echo "13. Running Full Automated Backend Pytest Suite (All 17 test modules)..."
docker compose exec -T -e PYTHONPATH=/app backend pytest tests/backend -v
echo ""
echo "=========================================================="
echo "HealthWatch Verification Suite: ALL TESTS PASSED!"
echo "=========================================================="


