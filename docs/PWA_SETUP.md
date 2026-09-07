# HealthWatch — Progressive Web App (PWA) Setup & Architecture Manual

## 1. Overview
HealthWatch provides Progressive Web App (PWA) capabilities, allowing health officers and monitored patients to install the web platform directly onto Android and iOS home screens as a standalone application.

When installed as a PWA, HealthWatch:
- Runs in **standalone full-screen mode** without browser address bars or navigation controls.
- Displays custom branded app icons on the device launcher.
- Employs a **Service Worker** to cache core application assets for fast load times and offline shell resilience.
- Adapts fluidly to mobile form factors with a native-style bottom navigation bar.

---

## 2. Web App Manifest Configuration

The app manifest is located at `frontend/public/manifest.json`:

```json
{
  "short_name": "HealthWatch",
  "name": "HealthWatch — Epidemiological Surveillance",
  "description": "Public health surveillance, quarantine monitoring, and spatial outbreak detection platform",
  "icons": [
    {
      "src": "icon-192.svg",
      "type": "image/svg+xml",
      "sizes": "192x192",
      "purpose": "any maskable"
    },
    {
      "src": "icon-512.svg",
      "type": "image/svg+xml",
      "sizes": "512x512",
      "purpose": "any maskable"
    }
  ],
  "start_url": "/",
  "background_color": "#090d16",
  "theme_color": "#0ea5e9",
  "display": "standalone",
  "orientation": "portrait-primary",
  "scope": "/"
}
```

### Key Properties
- `display: "standalone"`: Hides the browser URL bar and toolbar, making the web app feel like an installed native application.
- `background_color: "#090d16"`: Matches the dark slate theme during splash-screen launch.
- `theme_color: "#0ea5e9"`: Colors the mobile system status bar to blend seamlessly with the app header.

---

## 3. Service Worker Implementation

The service worker is configured at `frontend/public/sw.js` and registered in `index.html`:

```javascript
// frontend/public/sw.js
const CACHE_NAME = 'healthwatch-shell-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.svg',
  '/icon-512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Bypass caching for live API calls to FastAPI backend
  if (event.request.url.includes('/api/')) {
    return;
  }
  // Cache-first falling back to network for static assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request);
    })
  );
});
```

---

## 4. How to Install HealthWatch on Android Devices

### Using Google Chrome on Android:
1. Open Chrome and navigate to:
   ```
   http://<YOUR-LAPTOP-IP>:5173
   ```
2. Tap the **Three Dots (Menu)** button in the top-right corner.
3. Select **"Install App"** or **"Add to Home Screen"**.
4. Confirm by tapping **"Install"**.
5. The HealthWatch icon will appear on your phone's home screen and app drawer.
6. Tapping the icon launches HealthWatch in **standalone full-screen mode**.

### Using Apple Safari on iOS:
1. Open Safari and navigate to `http://<YOUR-LAPTOP-IP>:5173`.
2. Tap the **Share** button (box with an upward arrow).
3. Scroll down and tap **"Add to Home Screen"**.
4. Tap **"Add"** in the top-right corner.

---

## 5. PWA vs. Native Android Application (Academic Comparison)

In an academic viva or project evaluation, the distinction between the **HealthWatch PWA** and the **HealthWatch Native Android App (`android/`)** demonstrates an understanding of mobile computing constraints:

| Capability / Metric | HealthWatch Progressive Web App (PWA) | HealthWatch Native Android App (Kotlin) |
| :--- | :--- | :--- |
| **Installation** | Instant via browser, no APK or Play Store required | Requires installing `.apk` file or sideloading |
| **Cross-Platform** | Runs identically on Android, iOS, Windows, macOS, Linux | Android devices only |
| **UI Experience** | Standalone full-screen, bottom touch navigation | Native Android Material Components |
| **Ad-Hoc GPS Telemetry** | High-accuracy real GPS when app is open | High-accuracy real GPS |
| **Background Telemetry (Screen Locked)** | **Suspended by OS** (Chrome suspends JS execution) | **Continuous & Reliable** via `ForegroundService` |
| **Boot Auto-Start** | Not supported | Supported via `BOOT_COMPLETED` BroadcastReceiver |
| **Battery Consumption** | Low (only runs when active) | Optimized via `FusedLocationProviderClient` |
| **Recommendation** | **Ideal for quick testing, check-ins, and officer review** | **Required for 24/7 mandatory quarantine monitoring** |
