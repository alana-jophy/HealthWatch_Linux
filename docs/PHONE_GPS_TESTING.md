# HealthWatch — Physical Phone Real GPS Testing Guide (Step 26)

This operational manual documents the exact procedure for connecting a physical Android smartphone to your local HealthWatch development environment, authorizing real device GPS collection, transmitting spatial observations to PostgreSQL/PostGIS, and visualizing live movement roadmaps.

---

## Architecture Overview: Mobile LAN Testing

```
  +--------------------------------------------------------------------+
  |                           Local Wi-Fi Network                      |
  |                                                                    |
  |   +------------------------------------+                           |
  |   |        Physical Android Phone      |                           |
  |   |                                    |                           |
  |   | 1. Web Browser (Chrome/Firefox)    |                           |
  |   |    http://<WINDOWS-LAN-IP>:5173    |                           |
  |   |    (or Android Companion App)      |                           |
  |   |                                    |                           |
  |   | 2. Hardware GPS Telemetry          |                           |
  |   |    ~15-minute sampling             |                           |
  |   |    source = PATIENT_GPS            |                           |
  |   +-----------------+------------------+                           |
  |                     |                                              |
  |                     | HTTP REST / JSON                             |
  |                     v                                              |
  |   +------------------------------------+                           |
  |   |    Windows Host (LAN 0.0.0.0)      |                           |
  |   |                                    |                           |
  |   | 1. FastAPI (Port 8000)             |                           |
  |   |    CORS regex: private LAN IPs     |                           |
  |   |    Auth & Consent Validation       |                           |
  |   |                                    |                           |
  |   | 2. PostgreSQL / PostGIS (Port 5432)|                           |
  |   |    geometry(Point, 4326)           |                           |
  |   |                                    |                           |
  |   | 3. Vite Dev Server (Port 5173)     |                           |
  |   |    host: 0.0.0.0                   |                           |
  |   +------------------------------------+                           |
  +--------------------------------------------------------------------+
```

---

## 1. Start Docker Services (PostgreSQL + PostGIS)

Open your **WSL Ubuntu 24.04.1** terminal or PowerShell in the project directory:

```bash
cd "/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch"
# (or in Windows PowerShell: cd "C:\Users\Alana P J\.gemini\antigravity-ide\scratch\healthwatch")

# Start PostGIS database container
docker compose up -d postgres

# Verify that PostgreSQL + PostGIS container is healthy
docker compose ps
```

---

## 2. Start FastAPI Backend on `0.0.0.0`

In your WSL terminal (or PowerShell):

```bash
cd "/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch/backend"
source .venv/bin/activate  # if using virtualenv

# Run uvicorn listening on all network interfaces (0.0.0.0)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Why `0.0.0.0`?** Binding to `127.0.0.1` restricts traffic solely to the local computer. Binding to `0.0.0.0` allows devices on your Wi-Fi network (such as your phone) to connect to port 8000.

---

## 3. Start Vite Frontend on `0.0.0.0`

In a second terminal window:

```bash
cd "/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch/frontend"

# Start Vite dev server with 0.0.0.0 host binding
npm run dev -- --host 0.0.0.0
```

Vite will output:
```
  VITE v5.x.x  ready in 320 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

---

## 4. Find Your Windows LAN IPv4 Address

To connect your phone, you must determine your computer's local Wi-Fi IP address.

In **Windows PowerShell** or Command Prompt:

```powershell
ipconfig
```

Look for the adapter labeled **Wireless LAN adapter Wi-Fi** (or Ethernet if wired):

```text
Wireless LAN adapter Wi-Fi:
   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 192.168.1.105   <--- THIS IS YOUR <WINDOWS-LAN-IP>
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
```

*(In this example, your Windows LAN IP is `192.168.1.105`).*

---

## 5. Connect Phone and PC to the Same Wi-Fi Network

> [!IMPORTANT]
> - Ensure your **Android phone is connected to the exact same Wi-Fi router/SSID** as your Windows laptop/PC.
> - Ensure your Wi-Fi network does not have "Client Isolation / AP Isolation" enabled in router settings (standard home Wi-Fi allows client-to-client traffic).

---

## 6. Open HealthWatch on Your Android Phone

On your phone, open **Chrome** (or Firefox) and navigate to:

```text
http://<WINDOWS-LAN-IP>:5173
```
*(For example: `http://192.168.1.105:5173`)*.

---

## 7. Dynamic Frontend API Configuration

HealthWatch is pre-configured with dynamic host resolution in [`frontend/src/services/api.ts`](file:///C:/Users/Alana%20P%20J/.gemini/antigravity-ide/scratch/healthwatch/frontend/src/services/api.ts):
- When accessed on PC via `http://localhost:5173`, it calls `http://localhost:8000`.
- When accessed on your phone via `http://192.168.1.105:5173`, it **automatically routes API calls to `http://192.168.1.105:8000`** without needing manual edits!

*(If you ever need an explicit override, create `frontend/.env.local` containing `VITE_API_BASE_URL=http://192.168.1.105:8000`).*

---

## 8. Log In as the Synthetic Test Patient

In the web interface on your phone:
1. Ensure the mode is set to **Patient View** (or toggle the role switch at the top).
2. The web client auto-authenticates the default test patient:
   - **Email**: `patient.synth101@healthwatch.org`
   - **Password**: `Patient@HealthWatch2026`
   - **Pseudo ID**: `PAT-SYNTH-101`

---

## 9. Location Permission Flow

1. In the sidebar or hamburger menu, open **My Monitoring** (`patient-monitoring`).
2. Read the statutory disclosure:
   > *"HealthWatch requires your location during an active authorized monitoring session. Location observations are collected approximately every 15 minutes to support disease surveillance and movement analysis."*
3. Tap **Authorize Location Permission**:
   - The browser will trigger the Android system permission dialog: *"Allow HealthWatch to access this device's location?"*
   - Tap **"While using the app"** / **"Allow"**.

---

## 10. Explicit HealthWatch Location Consent

1. Under **MY LOCATION MONITORING**, tap **Grant Explicit Consent (14 Days)**.
2. An immutable compliance audit record is saved in PostgreSQL:
   - `action = "CONSENT_GRANTED"`
   - `validity = 14 days`
3. The Consent metric updates to <span style="color:#10b981;font-weight:bold;">GRANTED</span>.

---

## 11. Start Monitoring Session

1. Tap the green **START MONITORING** button.
2. Backend confirms authorization and creates an active surveillance session (`status = "ACTIVE"`).
3. The status indicator begins pulsating green: <span style="color:#10b981;font-weight:bold;">ACTIVE</span>.

---

## 12. Walk with the Phone & Capture Real GPS Observations

1. Step outside or walk along your street/corridor.
2. Tap **"Record Phone GPS Now"** (or allow the ~15-minute automated sampling timer to trigger).
3. The browser requests high-accuracy satellite/cellular coordinates from Android's GNSS provider (`enableHighAccuracy: true`).
4. A success notification will appear:
   `Real Phone GPS Observation Recorded: (9.xxxx, 76.xxxx) ±4.2m [Source: PATIENT_GPS]`
5. The dashboard metrics update:
   - **Last GPS Observation**: e.g., `11:15 AM`
   - **GPS Accuracy**: e.g., `±4.2 m`
   - **Source**: `PATIENT_GPS`
   - **Last location received**: `just now` / `1 minute ago`

---

## 13. Observation Timing Tolerance (~15-Minute Cadence)

- HealthWatch enforces an **approximate 15-minute sampling interval**.
- It is **NOT** a second-by-second continuous turn-by-turn tracker.
- Variations between 12 to 18 minutes are natural and tolerated due to mobile OS battery optimization, GNSS satellite fix delays, and cellular handoffs.
- The system **never fabricates an observation** if the device did not supply one.

---

## 14. Verify Database Records in PostgreSQL / PostGIS

To inspect the raw GPS records stored in PostGIS, run in WSL/PowerShell:

```bash
docker compose exec postgres psql -U healthwatch_user -d healthwatch_db -c "
SELECT 
  id, 
  patient_id, 
  recorded_at, 
  latitude, 
  longitude, 
  accuracy_meters, 
  source,
  ST_AsText(location) AS postgis_wkt 
FROM patient_locations 
WHERE source = 'PATIENT_GPS' 
ORDER BY recorded_at DESC 
LIMIT 5;
"
```

Expected Output:
```text
                  id                  | recorded_at | latitude | longitude | accuracy_meters |   source    |      postgis_wkt       
--------------------------------------+-------------+----------+-----------+-----------------+-------------+------------------------
 3f1a2b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c | 11:15:32    |  9.9816  |  76.2999  |             4.2 | PATIENT_GPS | POINT(76.2999 9.9816)
```

---

## 15. Verify Movement Roadmap & Real GPS Visualization

1. On your PC (or phone), open **My Movement Roadmap** (`patient-roadmap`).
2. Ensure the patient selected is `PAT-SYNTH-101`.
3. Click **"Today's Route"** or **"All Observations (Live)"** to clear any historical date filter.
4. Toggle **Live Dashboard Polling: ACTIVE (15s)**.
5. You will see:
   - **Marker Pins ($A, B, C \dots$)**: Rendered at your actual geographic location.
   - **Source Badge**: Displaying `REAL GPS (PATIENT_GPS)` with green styling.
   - **Observation Classification**: Clearly tagged as `Start Observation`, `Intermediate Observation`, or `Final Observation`.
   - **Visual Polyline**: Chronologically connecting points.
   - **Mandatory Disclaimers**:
     - *"Recorded GPS observations — approximately 15-minute sampling"*
     - *"The connecting line is a visual representation between recorded observations and does not represent continuous GPS tracking."*

---

## 16. Technical Distinction: Browser-Based Testing vs Android Kotlin Foreground Service

> [!IMPORTANT]
> ### 1. Phone Web Browser Testing (This Step)
> - **Capability**: Collects real hardware GPS observations via HTML5 Geolocation API (`navigator.geolocation`) while the browser tab remains open.
> - **Limitation**: Web browsers **do NOT provide guaranteed background execution**. If the user locks the phone, switches apps, or the OS suspends background browser tabs, periodic timers may be halted by Android's Doze mode.
> - **Purpose**: Ideal for immediate verification of:
>   `REAL PHONE GPS → FASTAPI (0.0.0.0) → POSTGRESQL/POSTGIS → LEAFLET ROADMAP`
>
> ### 2. Android Kotlin Companion App (`mobile/`)
> - **Capability**: Uses Android's native `LocationMonitoringService` implemented as an **Android Foreground Service** with a persistent ongoing notification and `FusedLocationProviderClient`.
> - **Background Reliability**: Runs in the background even when the screen is turned off or other apps are in use, sampling coordinates approximately every 15 minutes.
> - **Implementation**: Located in `mobile/app/src/main/java/com/healthwatch/service/LocationMonitoringService.kt`.

---

## Troubleshooting Common Errors

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **Phone says "Site can't be reached"** | PC and Phone on different Wi-Fi networks | Connect both to the same Wi-Fi SSID; verify PC IP with `ipconfig`. |
| **Windows Firewall blocks port 5173 / 8000** | Windows Defender Firewall rule | In PowerShell (Admin): `New-NetFirewallRule -DisplayName "HealthWatch Dev" -Direction Inbound -LocalPort 5173,8000 -Protocol TCP -Action Allow` |
| **"Location permission denied"** | Mobile browser blocked location | In Android Chrome: Tap Lock icon in address bar &rarr; Permissions &rarr; Allow Location. |
| **"GPS position unavailable"** | Phone GPS switched off or no satellite fix | Turn on Device Location (GPS) in phone quick settings; set to High Accuracy. |
| **"CORS error in console"** | Connecting via unusual IP address | Verify FastAPI has `allow_origin_regex` configured in `main.py` for LAN IPs. |
