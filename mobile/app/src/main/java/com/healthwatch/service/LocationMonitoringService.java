package com.healthwatch.service;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;
import com.healthwatch.MainActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.OfflineLocationQueue;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.ConsentModels.PatientMonitoringStatusResponse;
import com.healthwatch.data.model.LocationModels.LocationObservationSubmit;
import com.healthwatch.data.model.LocationModels.QueuedLocationObservation;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class LocationMonitoringService extends Service {

    private static final String TAG = "HealthWatchLocation";
    private static final int NOTIFICATION_ID = 1001;
    private static final String CHANNEL_ID = "healthwatch_monitoring_channel";

    public static final String ACTION_START = "com.healthwatch.action.START_MONITORING";
    public static final String ACTION_STOP = "com.healthwatch.action.STOP_MONITORING";

    private final SimpleDateFormat isoDateFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);

    private FusedLocationProviderClient fusedLocationClient;
    private LocationCallback locationCallback;
    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;
    private OfflineLocationQueue offlineQueue;
    private ExecutorService serviceExecutor;
    private Handler mainHandler;

    @Override
    public void onCreate() {
        super.onCreate();
        isoDateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        sessionManager = new SessionManager(getApplicationContext());
        apiClient = new HealthWatchApiClient(sessionManager);
        offlineQueue = new OfflineLocationQueue(getApplicationContext());
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this);
        serviceExecutor = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());

        createNotificationChannel();

        locationCallback = new LocationCallback() {
            @Override
            public void onLocationResult(LocationResult result) {
                if (result == null) return;
                for (android.location.Location location : result.getLocations()) {
                    processLocationObservation(location.getLatitude(), location.getLongitude(), location.getAccuracy());
                }
            }
        };
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null && intent.getAction() != null ? intent.getAction() : ACTION_START;

        if (ACTION_STOP.equals(action)) {
            Log.i(TAG, "Stopping authorized location monitoring service.");
            stopLocationMonitoring();
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
            return START_NOT_STICKY;
        }

        String sessionId = sessionManager.getActiveSessionId();
        if (sessionId == null || sessionId.trim().isEmpty()) {
            Log.w(TAG, "Cannot start location monitoring: No active monitoring session ID in session.");
            stopSelf();
            return START_NOT_STICKY;
        }

        Log.i(TAG, "Starting authorized location monitoring for session: " + sessionId);
        Notification initialNotification = createNotification("Monitoring active: initializing surveillance cadence...");
        startForeground(NOTIFICATION_ID, initialNotification);

        serviceExecutor.execute(() -> {
            int intervalMinutes = 15;
            boolean isTrackingDay = true;
            boolean canCollect = true;

            try {
                PatientMonitoringStatusResponse status = apiClient.getMonitoringStatusSync();
                if (status != null) {
                    intervalMinutes = status.getSamplingIntervalMinutes();
                    isTrackingDay = status.isTrackingDayToday();
                    canCollect = status.isCanCollectLocation();
                }
            } catch (Exception e) {
                Log.w(TAG, "Unable to query current status from backend, using defaults: " + e.getMessage());
            }

            if (!canCollect || !isTrackingDay) {
                Log.i(TAG, "Location collection disabled for today (Active day: " + isTrackingDay + ", Can collect: " + canCollect + ").");
                Notification standbyNotification = createNotification("Surveillance standby: Today is not an active tracking day.");
                NotificationManager notificationManager = getSystemService(NotificationManager.class);
                if (notificationManager != null) {
                    notificationManager.notify(NOTIFICATION_ID, standbyNotification);
                }
                return;
            }

            Notification activeNotification = createNotification("Monitoring active: location sampled every " + intervalMinutes + " minutes.");
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            if (notificationManager != null) {
                notificationManager.notify(NOTIFICATION_ID, activeNotification);
            }

            final int finalIntervalMinutes = intervalMinutes;
            mainHandler.post(() -> startLocationUpdates(finalIntervalMinutes));

            flushPendingOfflineQueue();
        });

        return START_STICKY;
    }

    private void startLocationUpdates(int intervalMinutes) {
        boolean hasFineLocation = ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED;

        boolean hasCoarseLocation = ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED;

        if (!hasFineLocation && !hasCoarseLocation) {
            Log.e(TAG, "Cannot collect location: Android location permissions not granted.");
            stopSelf();
            return;
        }

        long intervalMillis = Math.max((long) intervalMinutes * 60 * 1000L, 60000L);
        long fastestMillis = Math.max(intervalMillis / 2, 30000L);

        int priority = hasFineLocation ? Priority.PRIORITY_HIGH_ACCURACY : Priority.PRIORITY_BALANCED_POWER_ACCURACY;

        LocationRequest locationRequest = new LocationRequest.Builder(priority, intervalMillis)
                .setMinUpdateIntervalMillis(fastestMillis)
                .setMaxUpdateDelayMillis(intervalMillis + 30000L)
                .build();

        try {
            fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback, Looper.getMainLooper());
            Log.i(TAG, "FusedLocationProviderClient registered (Priority: " + (hasFineLocation ? "HIGH_ACCURACY" : "BALANCED") + ") at dynamic " + intervalMinutes + "-minute interval (" + intervalMillis + " ms).");
        } catch (SecurityException unlikely) {
            Log.e(TAG, "SecurityException while requesting location updates: " + unlikely.getMessage());
        }
    }

    private void stopLocationMonitoring() {
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback);
        } catch (Exception e) {
            Log.w(TAG, "Error removing location updates: " + e.getMessage());
        }
    }

    private void processLocationObservation(double latitude, double longitude, Float accuracy) {
        String patientId = sessionManager.getPatientId();
        if (patientId == null || patientId.trim().isEmpty()) {
            patientId = sessionManager.getPatientPseudoId();
        }
        if (patientId == null || patientId.trim().isEmpty()) {
            Log.w(TAG, "Cannot process location: No authenticated patient identifier found.");
            return;
        }
        String sessionId = sessionManager.getActiveSessionId();
        if (sessionId == null || sessionId.trim().isEmpty()) {
            return;
        }

        String recordedAt = isoDateFormat.format(new Date());
        LocationObservationSubmit observation = new LocationObservationSubmit(
                patientId,
                sessionId,
                latitude,
                longitude,
                accuracy,
                recordedAt,
                "PATIENT_GPS"
        );

        Log.i(TAG, "Collected observation: (" + latitude + ", " + longitude + "), Accuracy: " + accuracy + ", Source: PATIENT_GPS");

        final String finalPatientId = patientId;
        serviceExecutor.execute(() -> {
            try {
                apiClient.submitLocationObservationSync(observation);
                Log.i(TAG, "Location observation successfully uploaded to HealthWatch backend.");
                flushPendingOfflineQueue();
            } catch (Exception e) {
                Log.w(TAG, "Network failure or server error. Enqueuing observation to local offline queue: " + e.getMessage());
                offlineQueue.enqueueObservation(new QueuedLocationObservation(
                        finalPatientId,
                        sessionId,
                        latitude,
                        longitude,
                        accuracy,
                        recordedAt,
                        "PATIENT_GPS"
                ));
            }
        });
    }

    private void flushPendingOfflineQueue() {
        serviceExecutor.execute(() -> {
            int[] counts = apiClient.flushOfflineQueueSync(offlineQueue);
            int synced = counts[0];
            int failed = counts[1];
            if (synced > 0) {
                Log.i(TAG, "Flushed " + synced + " offline observations to server. (" + failed + " failed)");
            }
        });
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "HealthWatch Surveillance Monitoring",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Persistent notification for authorized patient location surveillance.");
            channel.setShowBadge(false);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification createNotification(String contentText) {
        Intent launchIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this,
                0,
                launchIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );

        Intent stopIntent = new Intent(this, LocationMonitoringService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent stopPendingIntent = PendingIntent.getService(
                this,
                1,
                stopIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("HealthWatch Location Monitoring Active")
                .setContentText(contentText)
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setOngoing(true)
                .setContentIntent(pendingIntent)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop Monitoring", stopPendingIntent)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setCategory(NotificationCompat.CATEGORY_SERVICE)
                .build();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopLocationMonitoring();
        if (serviceExecutor != null) {
            serviceExecutor.shutdown();
        }
        Log.i(TAG, "LocationMonitoringService destroyed.");
    }
}
