# HealthWatch — Smartphone Network & Real GPS Testing Manual

## 1. Prerequisites & Topology
To test HealthWatch on an actual physical Android or iOS smartphone using your local development host:
* **Host Machine**: Windows 11 with WSL2 (Ubuntu 24.04.1) running Docker containers:
  * `healthwatch-frontend` listening on port `5173` (Vite dev server bound to `0.0.0.0`)
  * `healthwatch-backend` listening on port `8000` (FastAPI / Uvicorn bound to `0.0.0.0`)
  * `healthwatch-db` listening on port `5432` (PostgreSQL 16 + PostGIS)
* **Local Area Network (LAN)**: Both the laptop/desktop host and the testing smartphone must be connected to the **same Wi-Fi router or mobile hotspot**.

---

## 2. Finding the Host Machine IP Address
Open Windows PowerShell and run:
```powershell
ipconfig
```
Look for your active wireless adapter (e.g., `Wireless LAN adapter Wi-Fi`):
```text
IPv4 Address. . . . . . . . . . . : 192.168.0.109
Subnet Mask . . . . . . . . . . . : 255.255.255.0
Default Gateway . . . . . . . . . : 192.168.0.1
```
*In this environment, the host LAN IP is **`192.168.0.109`**.*

---

## 3. Accessing HealthWatch from the Smartphone
1. Open **Google Chrome**, **Mozilla Firefox**, or **Safari** on your phone.
2. Navigate to:
   ```
   http://192.168.0.109:5173
   ```
3. You will be greeted by the **HealthWatch Login Portal**.

> [!TIP]
> If the page does not load, verify that Windows Defender Firewall permits incoming connections on port `5173` and port `8000`, or temporarily allow private network communication.

---

## 4. How to Install HealthWatch as an App on your Phone (PWA)

HealthWatch is a full **Progressive Web App (PWA)** with offline caching, high-resolution icons, and a standalone window interface without browser URL bars.

### Option 1: Using the in-app "Install App" Button
- Once you load `http://192.168.0.109:5173`, look for the **"Install HealthWatch as App"** button on the login screen, or the **"Install App"** button in the top header.
- Tap it to trigger the native phone installation dialog!

### Option 2: Android (Google Chrome, Brave, Samsung Internet)
1. In Chrome on your Android phone, tap the **Three Dots menu (⋮)** in the top-right corner.
2. Tap **"Install app"** (or **"Add to Home screen"**).
3. Tap **"Install"** in the popup dialog.
4. HealthWatch will now appear directly on your phone's home screen and app launcher with the HealthWatch shield icon!

### Option 3: iPhone (Safari)
1. Open the page in **Safari** on your iPhone.
2. Tap the **Share button** (square with an arrow pointing up at the bottom).
3. Scroll down the menu and tap **"Add to Home Screen"**.
4. Tap **"Add"** at the top right.
5. The HealthWatch icon will be pinned to your iPhone home screen and launch in full-screen standalone mode.

---

## 5. Step-by-Step Testing Walkthrough

### Step A: Public Health Officer Testing
1. On the login page, tap **"Officer Demo (Ernakulam Admin)"** or enter:
   - **Email**: `officer@test.com`
   - **Password**: `Officer@123`
2. **Examine Responsive Dashboard**:
   - Header shows authenticated officer badge and system connectivity.
   - Use the hamburger navigation drawer to inspect **Patient Management**, **GIS Outbreak Heatmap**, **Movement Analysis**, and **AI Outbreak Risk Prediction**.
3. **Inspect Patient Registry**:
   - Navigate to **Patient Management**.
   - Filter by district (*Ernakulam*, *Kozhikode*, *Thiruvananthapuram*, or any of all 14 Kerala districts).
   - Verify that patient `PAT-TEST-001` and `PAT-USER-143` (Alana P J) appear in the list.
4. Tap **Logout** in the header or sidebar to return to the login screen.

---

### Step B: Patient Testing & Real GPS Transmission
1. On the login page, tap **"Personal Demo (Alana P J)"** or enter:
   - **Email**: `alana@healthwatch.org`
   - **Password**: `Patient@HealthWatch2026`
2. **Observe Mobile-First Patient Interface**:
   - The desktop navigation sidebar is replaced with a streamlined **Mobile Bottom Navigation Bar**:
     - `Dashboard` | `Monitoring` | `Roadmap` | `Profile` | `Sign Out`
   - Notice the statutory patient isolation and consent cards.
3. **Grant Tracking Consent & Initiate Session**:
   - Tap **"Monitoring"** on the bottom bar.
   - If consent is not active, tap **"Grant Location Consent"** (recorded with timestamp & legal clause in PostGIS DB).
   - Tap **"Start Active Monitoring Session"**.
4. **Transmit Real Phone GPS Fix**:
   - Scroll down to the **"Real Phone GPS Telemetry"** card.
   - Tap **"Transmit Real Phone GPS Now"**.
   - When the phone browser displays:
     > *"healthwatch.org wants to know your location"*
     Tap **"Allow"** / **"While using the app"**.
   - The device's hardware GNSS chip will resolve the precise latitude, longitude, altitude, and accuracy (e.g., `±6.2m`).
   - The telemetry payload will be sent to `/api/movement/real-gps` with `source: "PATIENT_GPS"`.
   - The UI immediately updates:
     > *"Last location received: Just now (Accuracy: ±6.2m)"*

---

### Step C: Verifying Movement Roadmap on Phone
1. Tap **"Roadmap"** on the bottom navigation bar.
2. The Leaflet interactive map will center on your actual GPS coordinates.
3. The table beneath lists every observation along with its data provenance (`PATIENT_GPS`).
4. **Sampling Cadence Notice**:
   > *"Observations collected at ~15-minute intervals. Intermediate paths represent estimated trajectories."*

---

## 5. Verifying GPS Fix in the Database
From the host machine, verify that the real GPS coordinates were written to PostgreSQL/PostGIS:
```bash
wsl docker exec healthwatch-db psql -U healthwatch_user -d healthwatch_db -c \
"SELECT id, patient_id, source, ST_AsText(location) as coordinates, accuracy_meters, recorded_at FROM movement_observations WHERE source = 'PATIENT_GPS' ORDER BY recorded_at DESC LIMIT 5;"
```
Expected output:
```text
  id  |  patient_id  |   source    |            coordinates            | accuracy_meters |        recorded_at
------+--------------+-------------+-----------------------------------+-----------------+----------------------------
 1042 | PAT-USER-143 | PATIENT_GPS | POINT(76.32451234 10.01239871)    |            6.20 | 2026-09-05 11:58:20+05:30
```

---

## 6. Troubleshooting Common Issues
| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Phone shows "Site cannot be reached"** | Host firewall blocking port `5173` | Run `New-NetFirewallRule -DisplayName "Vite Dev" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow` in PowerShell (Admin). |
| **Login fails or times out on phone** | Vite proxying `/api` or API calling `localhost:8000` | Ensure `src/services/api.ts` uses `window.location.hostname` so requests point to `http://192.168.0.109:8000`. |
| **Geolocation permission denied** | Browser blocked location access | Go to Android Chrome Settings → Site Settings → Location → Allow for `http://192.168.0.109:5173`. |
| **Map tiles not loading on phone** | No internet connection on Wi-Fi | Ensure the Wi-Fi router has internet access to fetch OpenStreetMap tiles (`tile.openstreetmap.org`). |
