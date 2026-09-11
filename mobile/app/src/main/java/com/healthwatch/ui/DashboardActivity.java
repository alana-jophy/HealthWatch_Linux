package com.healthwatch.ui;

import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.OfflineLocationQueue;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.ConsentModels.PatientMonitoringStatusResponse;

public class DashboardActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;
    private OfflineLocationQueue offlineQueue;

    private TextView patientNameText;
    private TextView patientPseudoText;
    private TextView statusBadgeText;
    private TextView queueStatusText;
    private ProgressBar refreshProgressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);
        offlineQueue = new OfflineLocationQueue(this);

        if (!sessionManager.isLoggedIn()) {
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }

        buildUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshDashboardData();
    }

    private void buildUi() {
        ScrollView root = new ScrollView(this);
        root.setBackgroundColor(Color.parseColor("#0B1120")); // Slate 950
        root.setFillViewport(true);

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(40, 48, 40, 48);

        // Header Title
        TextView appTitle = new TextView(this);
        appTitle.setText("HealthWatch Patient Portal");
        appTitle.setTextSize(20f);
        appTitle.setTextColor(Color.WHITE);
        appTitle.setTypeface(Typeface.DEFAULT_BOLD);

        TextView appSubtitle = new TextView(this);
        appSubtitle.setText("Intelligent Disease Surveillance & Contact Tracing");
        appSubtitle.setTextSize(12f);
        appSubtitle.setTextColor(Color.parseColor("#94A3B8"));
        appSubtitle.setPadding(0, 4, 0, 32);

        container.addView(appTitle);
        container.addView(appSubtitle);

        // Patient ID Card
        LinearLayout patientCard = new LinearLayout(this);
        patientCard.setOrientation(LinearLayout.VERTICAL);
        patientCard.setBackgroundColor(Color.parseColor("#1E293B"));
        patientCard.setPadding(32, 32, 32, 32);

        String userName = sessionManager.getUserName();
        patientNameText = new TextView(this);
        patientNameText.setText(userName != null && !userName.isEmpty() ? userName : "Authenticated Patient");
        patientNameText.setTextSize(18f);
        patientNameText.setTextColor(Color.WHITE);
        patientNameText.setTypeface(Typeface.DEFAULT_BOLD);

        String pseudoId = sessionManager.getPatientPseudoId();
        patientPseudoText = new TextView(this);
        patientPseudoText.setText("ID: " + (pseudoId != null && !pseudoId.isEmpty() ? pseudoId : "—"));
        patientPseudoText.setTextSize(13f);
        patientPseudoText.setTextColor(Color.parseColor("#38BDF8")); // Cyan 400
        patientPseudoText.setPadding(0, 4, 0, 16);

        statusBadgeText = new TextView(this);
        statusBadgeText.setText("MONITORING STATUS: CHECKING...");
        statusBadgeText.setTextSize(12f);
        statusBadgeText.setTextColor(Color.WHITE);
        statusBadgeText.setBackgroundColor(Color.parseColor("#334155"));
        statusBadgeText.setPadding(20, 10, 20, 10);
        statusBadgeText.setGravity(Gravity.CENTER);

        queueStatusText = new TextView(this);
        queueStatusText.setText("Offline Queue: 0 pending");
        queueStatusText.setTextSize(11f);
        queueStatusText.setTextColor(Color.parseColor("#94A3B8"));
        queueStatusText.setPadding(0, 12, 0, 0);

        patientCard.addView(patientNameText);
        patientCard.addView(patientPseudoText);
        patientCard.addView(statusBadgeText);
        patientCard.addView(queueStatusText);
        container.addView(patientCard);

        // Loading indicator
        refreshProgressBar = new ProgressBar(this);
        refreshProgressBar.setVisibility(View.GONE);
        refreshProgressBar.setPadding(0, 16, 0, 16);
        container.addView(refreshProgressBar);

        // Navigation Action Buttons Grid
        TextView sectionTitle = new TextView(this);
        sectionTitle.setText("PATIENT MODULES");
        sectionTitle.setTextSize(12f);
        sectionTitle.setTextColor(Color.parseColor("#64748B"));
        sectionTitle.setTypeface(Typeface.DEFAULT_BOLD);
        sectionTitle.setPadding(0, 32, 0, 16);
        container.addView(sectionTitle);

        // 1. My Monitoring Button
        container.addView(createModuleButton("1. My Monitoring", "Control observation sessions & view interval",
                () -> startActivity(new Intent(this, MonitoringActivity.class))));

        // 2. Location Consent Button
        container.addView(createModuleButton("2. Location Consent", "Manage explicit 14-day surveillance agreement",
                () -> startActivity(new Intent(this, ConsentActivity.class))));

        // 3. My Profile Button
        container.addView(createModuleButton("3. My Profile", "View demographics & assigned Kerala ward",
                () -> startActivity(new Intent(this, ProfileActivity.class))));

        // 4. My Disease Case Button
        container.addView(createModuleButton("4. My Disease Case", "Clinical details, diagnosis & recovery status",
                () -> startActivity(new Intent(this, DiseaseCaseActivity.class))));

        // 5. Location History Button
        container.addView(createModuleButton("5. Location History", "Review collected GPS points & sync offline queue",
                () -> startActivity(new Intent(this, LocationHistoryActivity.class))));

        // 6. Movement Roadmap Button
        container.addView(createModuleButton("6. Movement Roadmap", "Sequential spatial observation roadmap",
                () -> startActivity(new Intent(this, RoadmapActivity.class))));

        // Logout Button
        Button logoutButton = new Button(this);
        logoutButton.setText("LOG OUT");
        logoutButton.setTextSize(12f);
        logoutButton.setTextColor(Color.parseColor("#FDA4AF"));
        logoutButton.setBackgroundColor(Color.TRANSPARENT);
        logoutButton.setOnClickListener(v -> {
            sessionManager.clearSession();
            startActivity(new Intent(DashboardActivity.this, LoginActivity.class));
            finish();
        });
        container.addView(logoutButton);

        root.addView(container);
        setContentView(root);
    }

    private View createModuleButton(String title, String subtitle, Runnable onClick) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.parseColor("#1E293B"));
        layout.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 16);
        layout.setLayoutParams(params);
        layout.setClickable(true);
        layout.setOnClickListener(v -> onClick.run());

        TextView titleView = new TextView(this);
        titleView.setText(title);
        titleView.setTextSize(15f);
        titleView.setTextColor(Color.WHITE);
        titleView.setTypeface(Typeface.DEFAULT_BOLD);

        TextView subtitleView = new TextView(this);
        subtitleView.setText(subtitle);
        subtitleView.setTextSize(11f);
        subtitleView.setTextColor(Color.parseColor("#94A3B8"));
        subtitleView.setPadding(0, 4, 0, 0);

        layout.addView(titleView);
        layout.addView(subtitleView);
        return layout;
    }

    private void refreshDashboardData() {
        int pendingCount = offlineQueue.getPendingCount();
        queueStatusText.setText("Offline Queue: " + pendingCount + " observations pending upload");

        String currentPseudo = sessionManager.getPatientPseudoId();
        if (currentPseudo != null && !currentPseudo.isEmpty()) {
            patientPseudoText.setText("ID: " + currentPseudo);
        }
        String currentName = sessionManager.getUserName();
        if (currentName != null && !currentName.isEmpty()) {
            patientNameText.setText(currentName);
        }

        refreshProgressBar.setVisibility(View.VISIBLE);
        apiClient.getMonitoringStatus(new HealthWatchApiClient.ApiCallback<PatientMonitoringStatusResponse>() {
            @Override
            public void onSuccess(PatientMonitoringStatusResponse status) {
                refreshProgressBar.setVisibility(View.GONE);
                if (status != null) {
                    if (status.getPatientPseudoId() != null && !status.getPatientPseudoId().isEmpty()) {
                        patientPseudoText.setText("ID: " + status.getPatientPseudoId());
                    }

                    if (status.isHasActiveSession()) {
                        statusBadgeText.setText("MONITORING STATUS: ACTIVE");
                        statusBadgeText.setBackgroundColor(Color.parseColor("#059669")); // Emerald 600
                    } else {
                        statusBadgeText.setText("MONITORING STATUS: INACTIVE");
                        statusBadgeText.setBackgroundColor(Color.parseColor("#475569")); // Slate 600
                    }
                }
            }

            @Override
            public void onError(Exception e) {
                refreshProgressBar.setVisibility(View.GONE);
                statusBadgeText.setText("STATUS: OFFLINE / UNREACHABLE");
                statusBadgeText.setBackgroundColor(Color.parseColor("#E11D48")); // Rose 600
            }
        });
    }
}
