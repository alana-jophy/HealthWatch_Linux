# HealthWatch — Role-Based Access Control (RBAC) Architecture

## 1. Overview
HealthWatch implements a dual-role access control system designed for epidemiological surveillance and communicable disease containment:
1. **Public Health Officer / Administrator (`PUBLIC_HEALTH_OFFICER` / `ADMIN`)**:
   Authorized personnel responsible for patient registration, disease case management, spatial outbreak analytics, GIS hot-spot analysis, exposure tracing, and AI risk prediction.
2. **Patient (`PATIENT`)**:
   Infected or monitored individuals with privacy-isolated access strictly limited to their own clinical record, active monitoring session, statutory consent management, and their personal movement roadmap.

---

## 2. Core Architectural Principles
* **Defense in Depth**: Role-based access control is enforced at both the **React Frontend layer** (route guards, dynamic navigation, context state) and the **FastAPI Backend layer** (OAuth2 JWT verification, SQL query scoping, dependency injection).
* **Zero Patient Cross-Visibility**: A patient cannot view administrative navigation, officer GIS tools, outbreak heatmaps, exposure traces, or other patients' records.
* **Strict Ownership Scoping**: In the database, all patient telemetry (`LocationConsent`, `MonitoringSession`, `MovementObservation`) is keyed to `patient_id`. Any query initiated by a `PATIENT` role automatically filters by `current_user.patient_id` or verifies user ownership.

---

## 3. Roles and Permissions Matrix

| Capability / Resource | Public Health Officer / Admin | Monitored Patient |
| :--- | :---: | :---: |
| **Public Health Dashboard** (District metrics, stats) |  Full Access |  Blocked |
| **Patient Management** (Add, View, Edit, Soft-Deactivate) |  Full CRUD |  Blocked |
| **Disease & Case Management** |  Full CRUD |  Blocked |
| **GIS Outbreak Heatmap & Spatial Layers** |  Full Access |  Blocked |
| **Contact Tracing & Exposure Analysis** |  Full Access |  Blocked |
| **AI Outbreak Risk Prediction (scikit-learn)** |  Full Access |  Blocked |
| **System Audit Logs & Surveillance Reports** |  Full Access |  Blocked |
| **Personal Dashboard** (Health state, session status) |  N/A (Officer overview) |  Self Only |
| **Personal Profile** (Demographics, contact info) |  View All |  Self Only |
| **Personal Disease Case** (Diagnosis, isolation terms) |  Manage All |  Self Only |
| **Location Consent Management** |  View audit trail |  Grant / Revoke (Self) |
| **Monitoring Session Controls** |  Initiate / Terminate |  Start / Stop (Self) |
| **Real Phone GPS Telemetry Submission** |  Manual entry |  Direct Device Feed |
| **Personal Movement Roadmap** |  View Patient Paths |  Self Only |

---

## 4. Authentication Flow (JWT Bearer Tokens)

```
[Client (React / Android)]
        │
        ▼ POST /api/auth/login
[FastAPI: app.api.endpoints.auth]
        │
        ├── 1. Validate Email & Password against hashed DB record (bcrypt)
        ├── 2. Resolve Role: PUBLIC_HEALTH_OFFICER | PATIENT
        └── 3. Generate Signed JWT (HMAC-SHA256, 60-min expiry)
                Payload: { sub: email, role: role, user_id: id, exp: timestamp }
        │
        ▼ 200 OK + access_token + user profile
[Client AuthContext]
        │
        ├── Persist token in localStorage ("healthwatch_token")
        └── Attach "Authorization: Bearer <token>" via Axios interceptor
```

---

## 5. Backend Authorization & Route Protection

FastAPI endpoints enforce access control through dependency injection functions in `app.api.deps`:

### Role Verification Dependencies
```python
# app/api/deps.py
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    # Decodes and verifies token signature & expiration
    ...

async def require_officer(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.PUBLIC_HEALTH_OFFICER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Public Health Officers"
        )
    return current_user

async def require_patient(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Registered Patients"
        )
    return current_user
```

### Secured Endpoint Examples
- **Officer Protected**:
  - `POST /api/patients/` (Create Patient)
  - `GET /api/gis/heatmap` (Outbreak Heatmap)
  - `GET /api/movement/exposure-analysis` (Spatial Co-location Engine)
- **Patient Protected**:
  - `POST /api/movement/real-gps` (Self-telemetry submission)
  - `POST /api/consent/` (Grant/revoke personal tracking consent)
  - `GET /api/patients/me/roadmap` (Personal GPS history)

---

## 6. Frontend Route Protection & Layout Adapters

In `src/App.tsx`, authentication state determines the rendered view tree:
1. **Unauthenticated**: Render `LoginView` with clean glassmorphic credentials cards and quick-fill academic test buttons.
2. **Officer Role**:
   - Renders desktop sidebar and admin layout.
   - Routes: `Dashboard`, `Patients`, `Disease Management`, `GIS`, `Heatmap`, `Movement Analysis`, `Exposure Analysis`, `AI Prediction`, `Reports`.
   - Any attempt to load patient views switches context safely or redirects to dashboard.
3. **Patient Role**:
   - Renders mobile-first interface with fixed bottom touch navigation (`sm:hidden`).
   - Routes: `My Dashboard`, `My Profile`, `My Disease Case`, `My Monitoring`, `My Location History`, `My Movement Roadmap`.
   - Sidebar strictly excludes all administrative and epidemiological modules.

---

## 7. Pre-Configured Academic Test Credentials

For evaluation, defense, and cross-device testing, the database is seeded with dedicated credentials:

| Role | Email Address | Password | Associated Patient Code |
| :--- | :--- | :--- | :--- |
| **Public Health Officer** | `officer@test.com` | `Officer@123` | N/A (Admin privileges) |
| **Standard Monitored Patient** | `patient@test.com` | `Patient@123` | `PAT-TEST-001` (Ernakulam) |
| **Personal Monitored Patient** | `alana@healthwatch.org` | `Patient@HealthWatch2026` | `PAT-USER-143` (Ernakulam) |

---

## 8. Automated Verification & Testing

Backend RBAC enforcement is verified via automated pytest suites:
```bash
docker exec -e PYTHONPATH=/app healthwatch-backend pytest tests/backend/test_auth.py tests/backend/test_role_based_gis_and_movement_rbac.py -v
```
Tests ensure:
- Unauthenticated requests receive `401 Unauthorized`.
- Patient tokens accessing officer endpoints receive `403 Forbidden`.
- Officer tokens attempting patient-only personal streams receive appropriate scoping or administrative overrides.
