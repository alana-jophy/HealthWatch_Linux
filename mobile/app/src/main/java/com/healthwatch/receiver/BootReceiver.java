package com.healthwatch.receiver;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;
import androidx.core.content.ContextCompat;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.service.LocationMonitoringService;

/**
 * Boot and Package Replacement Receiver.
 * Ensures the HealthWatch background location monitoring service automatically
 * resumes after device reboot, system restart, or application update if an active
 * monitoring session exists.
 */
public class BootReceiver extends BroadcastReceiver {

    private static final String TAG = "HealthWatchBoot";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        Log.i(TAG, "Received broadcast intent: " + action);

        if (Intent.ACTION_BOOT_COMPLETED.equals(action)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)
                || "android.intent.action.QUICKBOOT_POWERON".equals(action)
                || "com.htc.intent.action.QUICKBOOT_POWERON".equals(action)) {

            SessionManager sessionManager = new SessionManager(context);
            String sessionId = sessionManager.getActiveSessionId();

            if (sessionId != null && !sessionId.trim().isEmpty()) {
                Log.i(TAG, "Active monitoring session detected (" + sessionId + "). Resuming LocationMonitoringService on boot.");
                Intent serviceIntent = new Intent(context, LocationMonitoringService.class);
                serviceIntent.setAction(LocationMonitoringService.ACTION_START);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    ContextCompat.startForegroundService(context, serviceIntent);
                } else {
                    context.startService(serviceIntent);
                }
            } else {
                Log.d(TAG, "No active monitoring session found. Service will not start automatically.");
            }
        }
    }
}
