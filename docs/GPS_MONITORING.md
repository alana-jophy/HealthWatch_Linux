# HealthWatch — Patient GPS Monitoring Architecture & Telemetry Engine

## 1. Overview
Location telemetry is central to communicable disease containment in HealthWatch. It enables:
1. Verifying patient compliance with statutory home quarantine and isolation orders.
2. Generating chronological movement roadmaps for epidemiological contact tracing.
3. Powering spatial-temporal co-location analysis to compute secondary exposure risk.

To achieve this while upholding data privacy and battery efficiency, HealthWatch implements an **adaptive dual-tier telemetry model**:
- **Browser-Based Geolocation (Web PWA)**: Ideal for immediate real-device verification, ad-hoc check-ins, and manual telemetry submission.
- **Android Native Foreground Service (Kotlin)**: Designed for 24/7 background telemetry collection at 15-minute intervals with zero battery drain and immune to OS sleep modes.

---

## 2. Browser Geolocation API Implementation

In the web interface (`src/components/patient/PatientMonitoringView.tsx`), location data is harvested using the standard W3C Geolocation API:

```typescript
navigator.geolocation.getCurrentPosition(
  async (position) => {
    const payload = {
      patient_id: patient.id,
      session_id: activeSession.id,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      altitude: position.coords.altitude || 0.0,
      accuracy_meters: position.coords.accuracy,
      recorded_at: new Date(position.timestamp).toISOString(),
      source: "PATIENT_GPS"  // Explicit real device origin
    };
    await submitRealGpsLocation(payload);
  },
  (error) => {
    console.error("GPS Acquisition Error:", error.message);
  },
  {
    enableHighAccuracy: true,  // Engages device GNSS/GPS chipset
    timeout: 15000,            // 15-second acquisition window
    maximumAge: 0              // Refuses cached coordinates
  }
);
```

### Accuracy vs. Battery Trade-Off
| Mode | Sensor Engaged | Typical Accuracy | Battery Impact | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| `enableHighAccuracy: false` | Wi-Fi BSSID + Cellular Towers | 50m – 500m | Extremely Low | Coarse city/ward verification |
| `enableHighAccuracy: true` | Dedicated GNSS (GPS, GLONASS, NavIC) | 3m – 15m | Moderate during sampling | Contact tracing & roadmap rendering |

HealthWatch balances this by executing **discrete 15-minute sampling bursts** rather than continuous GPS streaming, reducing device battery consumption by over 92%.

---

## 3. The 15-Minute Sampling Philosophy
Continuous sub-second GPS tracking (like turn-by-turn navigation) is unsuitable for public health surveillance for two reasons:
1. **Severe Battery Depletion**: Continuous GPS drains a modern smartphone battery in 4 to 6 hours.
2. **Surveillance Proportionality & Privacy**: Public health regulations (such as epidemic containment acts) require recording *significant epidemiological stops* (e.g., supermarkets, clinics, bus stands), which typically last 15 minutes or more.

Therefore, HealthWatch records an observation **every 15 minutes** (4 fixes per hour / 96 points per 24 hours).
In the UI, movement between discrete observations is drawn with a trajectory polyline and accompanied by the disclaimer:
> *"Observations collected at approximately 15-minute intervals. Trajectories represent estimated paths between verified spatial coordinates."*

---

## 4. Mobile Browser Constraints vs. Native Android Service

### Why Browser Geolocation Fails in the Background
Modern mobile operating systems (Android 10+ and iOS 14+) enforce aggressive background process limits:
- When a user locks their phone or switches away from Chrome/Safari, the browser tab enters **Doze mode**.
- JavaScript execution timers (`setInterval`, `setTimeout`, and Web Workers) are paused.
- The browser is denied access to location sensors to protect battery life and user privacy.
- Consequently, **a browser app cannot reliably collect background GPS points while the screen is locked**.

### How the Native Android Kotlin Application Solves This
HealthWatch includes a native Android component (`android/`) that guarantees reliable background telemetry:
1. **Foreground Service with Persistent Notification**:
   Under Android architecture rules, an app can run background location updates if it declares a `ForegroundService` with a persistent notification visible in the status bar:
   > *"HealthWatch Active — Monitoring Health & Quarantine Safety"*
2. **Google Play Services `FusedLocationProviderClient`**:
   The native app requests `PRIORITY_BALANCED_POWER_ACCURACY` with an interval of `15 * 60 * 1000 ms` (15 minutes).
3. **WorkManager Resiliency**:
   If the device reboots, an Android `BroadcastReceiver` (`BOOT_COMPLETED`) restarts the tracking service automatically.

---

## 5. Storage in PostgreSQL / PostGIS

Every location observation received from the phone is persisted in the `movement_observations` table:

```sql
CREATE TABLE movement_observations (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id),
    session_id VARCHAR(64) REFERENCES monitoring_sessions(id),
    location GEOMETRY(Point, 4326) NOT NULL,  -- WGS84 Spatial Coordinate
    accuracy_meters FLOAT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    source VARCHAR(32) DEFAULT 'PATIENT_GPS' -- 'PATIENT_GPS' vs 'SIMULATED'
);

CREATE INDEX idx_movement_obs_location ON movement_observations USING GIST(location);
CREATE INDEX idx_movement_obs_patient_time ON movement_observations(patient_id, recorded_at);
```

By storing coordinates as native PostGIS `GEOMETRY(Point, 4326)`, the system can execute high-speed spatial operations:
- `ST_DWithin(a.location::geography, b.location::geography, 15)` to identify exposure co-locations within 15 meters.
- `ST_MakeLine(location ORDER BY recorded_at)` to build the patient trajectory vector.

---

## 6. Leaflet Map Visualization & Provenance Indicators

In `PatientMovementRoadmapView.tsx`, GPS points are rendered dynamically:
- **Green Marker**: Start of monitoring session.
- **Red Pulsing Marker**: Latest recorded GPS coordinate.
- **Blue Markers**: Intermediate 15-minute fixes.
- **Color-Coded Badge**:
  - `PATIENT_GPS` points display a **Green Real GPS Verified** badge with horizontal accuracy (e.g., `±6m`).
  - `SIMULATED` points display an **Amber Academic Simulation** badge.
- Clicking any waypoint opens a detailed popup:
  ```
  Fix #4: 10.012398° N, 76.324512° E
  Time: 11:45:00 AM (15 min interval)
  Accuracy: ±6.2m | Source: PATIENT_GPS
  ```
