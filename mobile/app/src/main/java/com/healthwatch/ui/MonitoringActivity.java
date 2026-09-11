package com.healthwatch.ui;

import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.ConsentModels.MonitoringSessionResponse;
import com.healthwatch.data.model.ConsentModels.PatientMonitoringStatusResponse;
import com.healthwatch.data.model.ConsentModels.SessionStartRequest;
import com.healthwatch.data.model.ConsentModels.SessionStopRequest;
import com.healthwatch.service.LocationMonitoringService;

public class MonitoringActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;

    private TextView statusBadgeText;
    private TextView monitoringStartText;
    private TextView monitoringEndText;
    private TextView samplingIntervalText;
    private TextView noticeText;
    private Button startMonitoringButton;
    private Button stopMonitoringButton;
    private ProgressBar progressBar;
    private TextView alertMessageText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        buildUi();
        refreshMonitoringStatus();
    }

    private void buildUi() {
        ScrollView root = new ScrollView(this);
        root.setBackgroundColor(Color.parseColor("#0B1120"));
        root.setFillViewport(true);

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(40, 48, 40, 48);

        Button backButton = new Button(this);
        backButton.setText("← Back to Dashboard");
        backButton.setTextSize(12f);
        backButton.setTextColor(Color.parseColor("#38BDF8"));
        backButton.setBackgroundColor(Color.TRANSPARENT);
        backButton.setOnClickListener(v -> finish());
        container.addView(backButton);

        TextView headerTitle = new TextView(this);
        headerTitle.setText("My Monitoring");
        headerTitle.setTextSize(24f);
        headerTitle.setTextColor(Color.WHITE);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setPadding(0, 16, 0, 16);
        container.addView(headerTitle);

        // Main Monitoring Card
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackgroundColor(Color.parseColor("#1E293B"));
        card.setPadding(32, 28, 32, 28);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 24);
        card.setLayoutParams(params);

        // 1. Monitoring Status
        TextView statusLabel = new TextView(this);
        statusLabel.setText("Monitoring Status:");
        statusLabel.setTextSize(12f);
        statusLabel.setTextColor(Color.parseColor("#94A3B8"));

        statusBadgeText = new TextView(this);
        statusBadgeText.setText("CHECKING...");
        statusBadgeText.setTextSize(18f);
        statusBadgeText.setTextColor(Color.WHITE);
        statusBadgeText.setTypeface(Typeface.DEFAULT_BOLD);
        statusBadgeText.setPadding(0, 4, 0, 20);

        card.addView(statusLabel);
        card.addView(statusBadgeText);

        // 2. Monitoring Start
        TextView startLabel = new TextView(this);
        startLabel.setText("Monitoring Start:");
        startLabel.setTextSize(12f);
        startLabel.setTextColor(Color.parseColor("#94A3B8"));

        monitoringStartText = new TextView(this);
        monitoringStartText.setText("—");
        monitoringStartText.setTextSize(14f);
        monitoringStartText.setTextColor(Color.WHITE);
        monitoringStartText.setTypeface(Typeface.DEFAULT_BOLD);
        monitoringStartText.setPadding(0, 4, 0, 20);

        card.addView(startLabel);
        card.addView(monitoringStartText);

        // 3. Monitoring End
        TextView endLabel = new TextView(this);
        endLabel.setText("Monitoring End:");
        endLabel.setTextSize(12f);
        endLabel.setTextColor(Color.parseColor("#94A3B8"));

        monitoringEndText = new TextView(this);
        monitoringEndText.setText("—");
        monitoringEndText.setTextSize(14f);
        monitoringEndText.setTextColor(Color.parseColor("#38BDF8"));
        monitoringEndText.setTypeface(Typeface.DEFAULT_BOLD);
        monitoringEndText.setPadding(0, 4, 0, 20);

        card.addView(endLabel);
        card.addView(monitoringEndText);

        // 4. Sampling Interval
        TextView intervalLabel = new TextView(this);
        intervalLabel.setText("Sampling Interval:");
        intervalLabel.setTextSize(12f);
        intervalLabel.setTextColor(Color.parseColor("#94A3B8"));

        samplingIntervalText = new TextView(this);
        samplingIntervalText.setText("Approximately 15 minutes");
        samplingIntervalText.setTextSize(14f);
        samplingIntervalText.setTextColor(Color.parseColor("#34D399"));
        samplingIntervalText.setTypeface(Typeface.DEFAULT_BOLD);
        samplingIntervalText.setPadding(0, 4, 0, 12);

        card.addView(intervalLabel);
        card.addView(samplingIntervalText);

        container.addView(card);

        // Explanation Notice
        noticeText = new TextView(this);
        noticeText.setText("HealthWatch collects location observations approximately every 15 minutes under authorized consent. GPS observations are submitted via background foreground service.");
        noticeText.setTextSize(12f);
        noticeText.setTextColor(Color.parseColor("#94A3B8"));
        noticeText.setPadding(0, 0, 0, 20);
        container.addView(noticeText);

        alertMessageText = new TextView(this);
        alertMessageText.setTextSize(12f);
        alertMessageText.setTextColor(Color.parseColor("#FDA4AF"));
        alertMessageText.setVisibility(View.GONE);
        alertMessageText.setPadding(0, 0, 0, 16);
        container.addView(alertMessageText);

        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.GONE);
        progressBar.setPadding(0, 0, 0, 16);
        container.addView(progressBar);

        // Action Buttons: START vs STOP
        startMonitoringButton = new Button(this);
        startMonitoringButton.setText("START MONITORING");
        startMonitoringButton.setTextSize(14f);
        startMonitoringButton.setTextColor(Color.WHITE);
        startMonitoringButton.setTypeface(Typeface.DEFAULT_BOLD);
        startMonitoringButton.setBackgroundColor(Color.parseColor("#059669"));
        startMonitoringButton.setVisibility(View.GONE);
        startMonitoringButton.setOnClickListener(v -> startMonitoring());
        container.addView(startMonitoringButton);

        stopMonitoringButton = new Button(this);
        stopMonitoringButton.setText("STOP MONITORING");
        stopMonitoringButton.setTextSize(14f);
        stopMonitoringButton.setTextColor(Color.WHITE);
        stopMonitoringButton.setTypeface(Typeface.DEFAULT_BOLD);
        stopMonitoringButton.setBackgroundColor(Color.parseColor("#E11D48"));
        stopMonitoringButton.setVisibility(View.GONE);
        stopMonitoringButton.setOnClickListener(v -> stopMonitoring());
        container.addView(stopMonitoringButton);

        root.addView(container);
        setContentView(root);
    }

    private void refreshMonitoringStatus() {
        progressBar.setVisibility(View.VISIBLE);
        alertMessageText.setVisibility(View.GONE);

        apiClient.getMonitoringStatus(new HealthWatchApiClient.ApiCallback<PatientMonitoringStatusResponse>() {
            @Override
            public void onSuccess(PatientMonitoringStatusResponse status) {
                progressBar.setVisibility(View.GONE);
                if (status != null) {
                    samplingIntervalText.setText(status.getSamplingIntervalDescription());

                    if (status.isHasActiveSession() && status.getActiveSession() != null) {
                        MonitoringSessionResponse s = status.getActiveSession();
                        statusBadgeText.setText("ACTIVE");
                        statusBadgeText.setTextColor(Color.parseColor("#34D399"));
                        monitoringStartText.setText(s.getStartTime() != null ? s.getStartTime() : "—");
                        monitoringEndText.setText(s.getEndTime() != null ? s.getEndTime() : "—");

                        startMonitoringButton.setVisibility(View.GONE);
                        stopMonitoringButton.setVisibility(View.VISIBLE);

                        startForegroundLocationService();
                    } else {
                        statusBadgeText.setText("INACTIVE");
                        statusBadgeText.setTextColor(Color.parseColor("#94A3B8"));
                        monitoringStartText.setText("—");
                        monitoringEndText.setText("—");

                        startMonitoringButton.setVisibility(View.VISIBLE);
                        stopMonitoringButton.setVisibility(View.GONE);
                    }
                }
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                alertMessageText.setText("Failed to load monitoring status: " + (e != null ? e.getMessage() : "Unknown"));
                alertMessageText.setVisibility(View.VISIBLE);
            }
        });
    }

    private void startMonitoring() {
        progressBar.setVisibility(View.VISIBLE);
        apiClient.startMonitoringSession(new SessionStartRequest(24), new HealthWatchApiClient.ApiCallback<MonitoringSessionResponse>() {
            @Override
            public void onSuccess(MonitoringSessionResponse session) {
                progressBar.setVisibility(View.GONE);
                if (session != null) {
                    sessionManager.saveActiveSessionId(session.getId());
                }
                startForegroundLocationService();
                refreshMonitoringStatus();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                alertMessageText.setText("Cannot start monitoring: " + (e != null ? e.getMessage() : "Unknown"));
                alertMessageText.setVisibility(View.VISIBLE);
            }
        });
    }

    private void stopMonitoring() {
        progressBar.setVisibility(View.VISIBLE);
        apiClient.stopMonitoringSession(new SessionStopRequest(), new HealthWatchApiClient.ApiCallback<MonitoringSessionResponse>() {
            @Override
            public void onSuccess(MonitoringSessionResponse session) {
                progressBar.setVisibility(View.GONE);
                sessionManager.saveActiveSessionId(null);
                stopForegroundLocationService();
                refreshMonitoringStatus();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                alertMessageText.setText("Failed to stop session: " + (e != null ? e.getMessage() : "Unknown"));
                alertMessageText.setVisibility(View.VISIBLE);
            }
        });
    }

    private void startForegroundLocationService() {
        Intent serviceIntent = new Intent(this, LocationMonitoringService.class);
        serviceIntent.setAction(LocationMonitoringService.ACTION_START);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ContextCompat.startForegroundService(this, serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    private void stopForegroundLocationService() {
        Intent serviceIntent = new Intent(this, LocationMonitoringService.class);
        serviceIntent.setAction(LocationMonitoringService.ACTION_STOP);
        startService(serviceIntent);
    }
}
