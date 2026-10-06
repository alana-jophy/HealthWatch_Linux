package com.healthwatch.ui;

import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.PatientModels.PatientProfile;
import java.util.ArrayList;
import java.util.List;

public class ProfileActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;
    private LinearLayout contentContainer;
    private ProgressBar progressBar;

    private static class LabelValue {
        final String label;
        final String value;
        LabelValue(String label, String value) {
            this.label = label;
            this.value = value;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        buildUi();
        loadProfile();
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
        headerTitle.setText("My Patient Profile");
        headerTitle.setTextSize(22f);
        headerTitle.setTextColor(Color.WHITE);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setPadding(0, 16, 0, 8);
        container.addView(headerTitle);

        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.VISIBLE);
        progressBar.setPadding(0, 32, 0, 32);
        container.addView(progressBar);

        contentContainer = new LinearLayout(this);
        contentContainer.setOrientation(LinearLayout.VERTICAL);
        contentContainer.setVisibility(View.GONE);
        container.addView(contentContainer);

        root.addView(container);
        setContentView(root);
    }

    private void loadProfile() {
        apiClient.getPatientProfile(new HealthWatchApiClient.ApiCallback<PatientProfile>() {
            @Override
            public void onSuccess(PatientProfile profile) {
                progressBar.setVisibility(View.GONE);
                contentContainer.setVisibility(View.VISIBLE);
                if (profile != null) {
                    renderProfileDetails(profile);
                }
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                contentContainer.setVisibility(View.VISIBLE);

                TextView errorView = new TextView(ProfileActivity.this);
                errorView.setText("Failed to load patient profile: " + (e != null ? e.getMessage() : "Unknown"));
                errorView.setTextColor(Color.parseColor("#FDA4AF"));
                errorView.setTextSize(13f);
                contentContainer.addView(errorView);
            }
        });
    }

    private void renderProfileDetails(PatientProfile profile) {
        contentContainer.removeAllViews();

        // Card 1: Identity
        List<LabelValue> idFields = new ArrayList<>();
        idFields.add(new LabelValue("Pseudo Identifier", profile.getPseudoId() != null ? profile.getPseudoId() : "—"));
        idFields.add(new LabelValue("Full Legal Name", profile.getFullName() != null ? profile.getFullName() : "—"));
        idFields.add(new LabelValue("Age / Gender", profile.getAge() + " Years • " + (profile.getGender() != null ? profile.getGender() : "—")));
        idFields.add(new LabelValue("Contact Phone", profile.getContactNumber() != null ? profile.getContactNumber() : "—"));
        idFields.add(new LabelValue("Monitoring Period", (profile.getMonitoringDays() != null ? profile.getMonitoringDays() : 14) + " Days Active Protocol"));
        idFields.add(new LabelValue("Residential Address", profile.getAddress() != null ? profile.getAddress() : "—"));

        View identityCard = createInfoCard("IDENTIFICATION & DEMOGRAPHICS", idFields);
        contentContainer.addView(identityCard);

        // Card 2: Kerala Geographic Hierarchy
        List<LabelValue> geoFields = new ArrayList<>();
        geoFields.add(new LabelValue("District", profile.getDistrictName() != null ? profile.getDistrictName() : "—"));
        geoFields.add(new LabelValue("Local Body (Panchayat / Corp)", profile.getLocalBodyName() != null ? profile.getLocalBodyName() : "—"));
        geoFields.add(new LabelValue("Ward Number", "Ward " + profile.getWardNumber()));
        geoFields.add(new LabelValue("Surveillance State", "Kerala, India"));

        View geoCard = createInfoCard("ASSIGNED SURVEILLANCE GEOGRAPHY", geoFields);
        contentContainer.addView(geoCard);

        // Card 3: Server & Sync Network Domain
        List<LabelValue> serverFields = new ArrayList<>();
        serverFields.add(new LabelValue("Sync Target Server", sessionManager.getBaseUrl()));
        serverFields.add(new LabelValue("Telemetry Protocol", sessionManager.getBaseUrl().startsWith("https://") ? "HTTPS (Encrypted)" : "HTTP"));
        View serverCard = createInfoCard("SERVER DOMAIN & TELEMETRY SYNC", serverFields);
        contentContainer.addView(serverCard);

        Button changeServerBtn = new Button(this);
        changeServerBtn.setText("⚙️ CONFIGURE SERVER DOMAIN");
        changeServerBtn.setTextColor(Color.WHITE);
        changeServerBtn.setBackgroundColor(Color.parseColor("#334155"));
        changeServerBtn.setTypeface(Typeface.DEFAULT_BOLD);
        changeServerBtn.setTextSize(13f);
        changeServerBtn.setPadding(0, 20, 0, 20);
        LinearLayout.LayoutParams srvParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        srvParams.setMargins(0, 0, 0, 20);
        changeServerBtn.setLayoutParams(srvParams);
        changeServerBtn.setOnClickListener(v -> showServerConfigDialog());
        contentContainer.addView(changeServerBtn);

        // Security / Change Password Button
        Button changePasswordBtn = new Button(this);
        changePasswordBtn.setText("CHANGE ACCOUNT PASSWORD");
        changePasswordBtn.setTextColor(Color.WHITE);
        changePasswordBtn.setBackgroundColor(Color.parseColor("#0284C7"));
        changePasswordBtn.setTypeface(Typeface.DEFAULT_BOLD);
        changePasswordBtn.setTextSize(14f);
        changePasswordBtn.setPadding(0, 24, 0, 24);
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        btnParams.setMargins(0, 0, 0, 24);
        changePasswordBtn.setLayoutParams(btnParams);
        changePasswordBtn.setOnClickListener(v -> startActivity(new Intent(ProfileActivity.this, ResetPasswordActivity.class)));
        contentContainer.addView(changePasswordBtn);
    }

    private void showServerConfigDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Server Domain & API URL");

        LinearLayout dialogLayout = new LinearLayout(this);
        dialogLayout.setOrientation(LinearLayout.VERTICAL);
        dialogLayout.setPadding(50, 24, 50, 12);

        TextView infoText = new TextView(this);
        infoText.setText("Enter the backend server domain or IP address to sync data (e.g. http://192.168.0.119:8000 or https://healthwatch.example.com):");
        infoText.setTextSize(13f);
        infoText.setTextColor(Color.parseColor("#475569"));
        infoText.setPadding(0, 0, 0, 16);
        dialogLayout.addView(infoText);

        EditText input = new EditText(this);
        input.setText(sessionManager.getBaseUrl());
        input.setSingleLine(true);
        input.setTextSize(14f);
        dialogLayout.addView(input);

        builder.setView(dialogLayout);

        builder.setPositiveButton("Save", (dialog, which) -> {
            String newUrl = input.getText() != null ? input.getText().toString().trim() : "";
            if (!newUrl.isEmpty()) {
                sessionManager.saveBaseUrl(newUrl);
                Toast.makeText(this, "Server domain updated to: " + sessionManager.getBaseUrl(), Toast.LENGTH_SHORT).show();
                loadProfile();
            }
        });

        builder.setNeutralButton("Reset Default", (dialog, which) -> {
            sessionManager.saveBaseUrl(SessionManager.DEFAULT_BASE_URL);
            Toast.makeText(this, "Reset to default: " + sessionManager.getBaseUrl(), Toast.LENGTH_SHORT).show();
            loadProfile();
        });

        builder.setNegativeButton("Cancel", (dialog, which) -> dialog.dismiss());
        builder.show();
    }

    private View createInfoCard(String title, List<LabelValue> fields) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackgroundColor(Color.parseColor("#1E293B"));
        card.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 20);
        card.setLayoutParams(params);

        TextView titleView = new TextView(this);
        titleView.setText(title);
        titleView.setTextSize(11f);
        titleView.setTextColor(Color.parseColor("#38BDF8"));
        titleView.setTypeface(Typeface.DEFAULT_BOLD);
        titleView.setPadding(0, 0, 0, 16);
        card.addView(titleView);

        for (LabelValue field : fields) {
            TextView labelView = new TextView(this);
            labelView.setText(field.label);
            labelView.setTextSize(11f);
            labelView.setTextColor(Color.parseColor("#94A3B8"));

            TextView valueView = new TextView(this);
            valueView.setText(field.value);
            valueView.setTextSize(14f);
            valueView.setTextColor(Color.WHITE);
            valueView.setTypeface(Typeface.DEFAULT_BOLD);
            valueView.setPadding(0, 2, 0, 12);

            card.addView(labelView);
            card.addView(valueView);
        }

        return card;
    }
}
