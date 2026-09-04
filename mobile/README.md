# HealthWatch Patient Companion Mobile Application

The HealthWatch mobile application is an **Android Kotlin** application designed for authorized patient location monitoring, quarantine boundary adherence verification, and public health telemetry reporting.

## Architecture
- **Language**: Kotlin
- **SDK Target**: Android 14+ (API 34)
- **Location Engine**: Google Play Services FusedLocationProviderClient
- **Background Execution**: Android Foreground Service with continuous notification (`LocationMonitoringService`)
- **Communication**: HTTPS REST / JWT authentication with HealthWatch Backend

## Structure
```
mobile/
├── app/
│   └── src/main/
│       ├── AndroidManifest.xml
│       └── java/com/healthwatch/
│           ├── MainActivity.kt
│           ├── service/
│           │   └── LocationMonitoringService.kt
│           └── data/
├── build.gradle.kts
├── settings.gradle.kts
└── README.md
```

## Permissions
- `ACCESS_FINE_LOCATION`
- `ACCESS_COARSE_LOCATION`
- `ACCESS_BACKGROUND_LOCATION`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_LOCATION`
- `INTERNET`
