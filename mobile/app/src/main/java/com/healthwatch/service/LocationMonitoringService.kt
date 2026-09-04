package com.healthwatch.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.google.android.gms.location.*
import com.healthwatch.MainActivity
import com.healthwatch.data.api.HealthWatchApiClient
import com.healthwatch.data.local.OfflineLocationQueue
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.LocationObservationSubmit
import com.healthwatch.data.model.QueuedLocationObservation
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

/**
 * Android Foreground Service for authorized periodic patient location surveillance.
 * 
 * Invariants:
 * 1. Requires explicit patient authorization and active monitoring session.
 * 2. Displays persistent ongoing notification to ensure full visibility (no hidden tracking).
 * 3. Sampling interval: ~15 MINUTES (900,000 ms), NOT 10 seconds.
 * 4. Tag: Source is strictly 'PATIENT_GPS'.
 * 5. On network failure, enqueues observations into OfflineLocationQueue and flushes when online.
 * 6. Respects Android battery, permission, and background execution limits.
 */
class LocationMonitoringService : Service() {

    companion object {
        private const val TAG = "HealthWatchLocation"
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "healthwatch_monitoring_channel"

        // 15 Minutes sampling interval (900,000 ms)
        const val INTERVAL_MILLIS = 15 * 60 * 1000L
        const val FASTEST_INTERVAL_MILLIS = 10 * 60 * 1000L

        const val ACTION_START = "com.healthwatch.action.START_MONITORING"
        const val ACTION_STOP = "com.healthwatch.action.STOP_MONITORING"
    }

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient
    private lateinit var offlineQueue: OfflineLocationQueue

    private val isoDateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    override fun onCreate() {
        super.onCreate()
        sessionManager = SessionManager(applicationContext)
        apiClient = HealthWatchApiClient(sessionManager)
        offlineQueue = OfflineLocationQueue(applicationContext)
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        createNotificationChannel()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                for (location in result.locations) {
                    processLocationObservation(location.latitude, location.longitude, location.accuracy)
                }
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action ?: ACTION_START

        if (action == ACTION_STOP) {
            Log.i(TAG, "Stopping authorized location monitoring service.")
            stopLocationMonitoring()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }

        // Verify active patient authorization
        val sessionId = sessionManager.getActiveSessionId()
        if (sessionId.isNullOrBlank()) {
            Log.w(TAG, "Cannot start location monitoring: No active monitoring session ID in session.")
            stopSelf()
            return START_NOT_STICKY
        }

        Log.i(TAG, "Starting authorized location monitoring (Interval: ~15 mins) for session: $sessionId")
        val notification = createNotification("Monitoring active: location sampled approximately every 15 minutes.")
        startForeground(NOTIFICATION_ID, notification)

        startLocationUpdates()
        flushPendingOfflineQueue()

        return START_STICKY
    }

    private fun startLocationUpdates() {
        val hasFineLocation = ContextCompat.checkSelfPermission(
            this,
            android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        val hasCoarseLocation = ContextCompat.checkSelfPermission(
            this,
            android.Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (!hasFineLocation && !hasCoarseLocation) {
            Log.e(TAG, "Cannot collect location: Android location permissions not granted.")
            stopSelf()
            return
        }

        // LocationRequest configured for ~15 minutes (900 seconds)
        val locationRequest = LocationRequest.Builder(Priority.PRIORITY_BALANCED_POWER_ACCURACY, INTERVAL_MILLIS)
            .setMinUpdateIntervalMillis(FASTEST_INTERVAL_MILLIS)
            .setMaxUpdateDelayMillis(INTERVAL_MILLIS + 60000L)
            .build()

        try {
            fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback, Looper.getMainLooper())
            Log.i(TAG, "FusedLocationProviderClient registered at ~15-minute interval.")
        } catch (unlikely: SecurityException) {
            Log.e(TAG, "SecurityException while requesting location updates: ${unlikely.message}")
        }
    }

    private fun stopLocationMonitoring() {
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
        } catch (e: Exception) {
            Log.w(TAG, "Error removing location updates: ${e.message}")
        }
    }

    private fun processLocationObservation(latitude: Double, longitude: Double, accuracy: Float?) {
        val patientId = sessionManager.getPatientId() ?: "UNKNOWN_PATIENT"
        val sessionId = sessionManager.getActiveSessionId() ?: return
        val recordedAt = isoDateFormat.format(Date())

        val observation = LocationObservationSubmit(
            patientId = patientId,
            monitoringSessionId = sessionId,
            latitude = latitude,
            longitude = longitude,
            accuracy = accuracy,
            recordedAt = recordedAt,
            source = "PATIENT_GPS"
        )

        Log.i(TAG, "Collected observation: ($latitude, $longitude), Accuracy: $accuracy, Source: PATIENT_GPS")

        serviceScope.launch {
            val result = apiClient.submitLocationObservation(observation)

            if (result.isSuccess) {
                Log.i(TAG, "Location observation successfully uploaded to HealthWatch backend.")
                // Attempt to flush previous pending observations
                flushPendingOfflineQueue()
            } else {
                Log.w(TAG, "Network failure or server error. Enqueuing observation to local offline queue: ${result.exceptionOrNull()?.message}")
                offlineQueue.enqueueObservation(
                    QueuedLocationObservation(
                        patientId = patientId,
                        monitoringSessionId = sessionId,
                        latitude = latitude,
                        longitude = longitude,
                        accuracy = accuracy,
                        recordedAt = recordedAt,
                        source = "PATIENT_GPS"
                    )
                )
            }
        }
    }

    private fun flushPendingOfflineQueue() {
        serviceScope.launch {
            val (synced, failed) = apiClient.flushOfflineQueue(offlineQueue)
            if (synced > 0) {
                Log.i(TAG, "Flushed $synced offline observations to server. ($failed failed)")
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "HealthWatch Surveillance Monitoring",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent notification for authorized patient location surveillance."
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun createNotification(contentText: String): Notification {
        val launchIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            launchIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopIntent = Intent(this, LocationMonitoringService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this,
            1,
            stopIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("HealthWatch Location Monitoring Active")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop Monitoring", stopPendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        stopLocationMonitoring()
        serviceScope.cancel()
        Log.i(TAG, "LocationMonitoringService destroyed.")
    }
}
