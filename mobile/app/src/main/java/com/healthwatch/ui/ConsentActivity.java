package com.healthwatch.ui;

import android.Manifest;
import android.content.pm.PackageManager;
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
import android.widget.Toast;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.ConsentModels.ConsentGrantRequest;
import com.healthwatch.data.model.ConsentModels.ConsentResponse;
import com.healthwatch.data.model.ConsentModels.ConsentRevokeRequest;
import com.healthwatch.data.model.ConsentModels.PatientMonitoringStatusResponse;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class ConsentActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;

    private TextView consentStatusBadge;
    private TextView consentValidUntilText;
    private TextView permissionStatusText;
    private Button grantButton;
    private Button revokeButton;
    private Button permissionButton;
    private ProgressBar progressBar;
    private TextView feedbackMessageText;

    private final ActivityResultLauncher<String[]> locationPermissionLauncher = registerForActivityResult(
            new ActivityResultContracts.RequestMultiplePermissions(),
            (Map<String, Boolean> permissions) -> {
                Boolean fineGranted = permissions.get(Manifest.permission.ACCESS_FINE_LOCATION);
                Boolean coarseGranted = permissions.get(Manifest.permission.ACCESS_COARSE_LOCATION);
                boolean granted = (fineGranted != null && fineGranted) || (coarseGranted != null && coarseGranted);
                if (granted) {
                    updatePermissionStatus(true);
                    Toast.makeText(ConsentActivity.this, "Android location permission granted.", Toast.LENGTH_SHORT).show();
                } else {
                    updatePermissionStatus(false);
                    Toast.makeText(ConsentActivity.this, "Location permission is required for monitoring.", Toast.LENGTH_LONG).show();
                }
            }
    );

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        buildUi();
        refreshConsentState();
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
        headerTitle.setText("Location Consent Agreement");
        headerTitle.setTextSize(22f);
        headerTitle.setTextColor(Color.WHITE);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setPadding(0, 16, 0, 8);
        container.addView(headerTitle);

        // Transparency Box
        LinearLayout disclosureBox = new LinearLayout(this);
        disclosureBox.setOrientation(LinearLayout.VERTICAL);
        disclosureBox.setBackgroundColor(Color.parseColor("#1E293B"));
        disclosureBox.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 12, 0, 24);
        disclosureBox.setLayoutParams(params);

        TextView disclosureTitle = new TextView(this);
        disclosureTitle.setText("MANDATORY TRANSPARENCY NOTICE");
        disclosureTitle.setTextSize(11f);
        disclosureTitle.setTextColor(Color.parseColor("#38BDF8"));
        disclosureTitle.setTypeface(Typeface.DEFAULT_BOLD);

        TextView disclosureBody = new TextView(this);
        disclosureBody.setText("“HealthWatch will collect your location approximately every 15 minutes during the authorized monitoring period.”");
        disclosureBody.setTextSize(14f);
        disclosureBody.setTextColor(Color.WHITE);
        disclosureBody.setTypeface(Typeface.DEFAULT_BOLD);
        disclosureBody.setPadding(0, 8, 0, 12);

        TextView disclosureTerms = new TextView(this);
        disclosureTerms.setText("Location data is recorded solely for quarantine compliance verification, spatial outbreak hotspot detection, and contact safety. HealthWatch strictly prohibits hidden or covert tracking. You may revoke this authorization at any time.");
        disclosureTerms.setTextSize(12f);
        disclosureTerms.setTextColor(Color.parseColor("#94A3B8"));

        disclosureBox.addView(disclosureTitle);
        disclosureBox.addView(disclosureBody);
        disclosureBox.addView(disclosureTerms);
        container.addView(disclosureBox);

        // Consent Status Card
        LinearLayout statusCard = new LinearLayout(this);
        statusCard.setOrientation(LinearLayout.VERTICAL);
        statusCard.setBackgroundColor(Color.parseColor("#1E293B"));
        statusCard.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams statusCardParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        statusCardParams.setMargins(0, 0, 0, 24);
        statusCard.setLayoutParams(statusCardParams);

        consentStatusBadge = new TextView(this);
        consentStatusBadge.setText("CONSENT: LOADING...");
        consentStatusBadge.setTextSize(13f);
        consentStatusBadge.setTextColor(Color.WHITE);
        consentStatusBadge.setTypeface(Typeface.DEFAULT_BOLD);
        consentStatusBadge.setBackgroundColor(Color.parseColor("#334155"));
        consentStatusBadge.setPadding(16, 8, 16, 8);

        consentValidUntilText = new TextView(this);
        consentValidUntilText.setText("Authorized Window: —");
        consentValidUntilText.setTextSize(12f);
        consentValidUntilText.setTextColor(Color.parseColor("#CBD5E1"));
        consentValidUntilText.setPadding(0, 12, 0, 8);

        permissionStatusText = new TextView(this);
        permissionStatusText.setText("Android OS Permission: Checking...");
        permissionStatusText.setTextSize(12f);
        permissionStatusText.setTextColor(Color.parseColor("#94A3B8"));

        statusCard.addView(consentStatusBadge);
        statusCard.addView(consentValidUntilText);
        statusCard.addView(permissionStatusText);
        container.addView(statusCard);

        // Feedback / Alert Text
        feedbackMessageText = new TextView(this);
        feedbackMessageText.setTextSize(12f);
        feedbackMessageText.setTextColor(Color.parseColor("#38BDF8"));
        feedbackMessageText.setVisibility(View.GONE);
        feedbackMessageText.setPadding(0, 0, 0, 16);
        container.addView(feedbackMessageText);

        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.GONE);
        progressBar.setPadding(0, 8, 0, 16);
        container.addView(progressBar);

        // Android Permission Button
        permissionButton = new Button(this);
        permissionButton.setText("REQUEST ANDROID LOCATION PERMISSION");
        permissionButton.setTextSize(12f);
        permissionButton.setTextColor(Color.WHITE);
        permissionButton.setBackgroundColor(Color.parseColor("#334155"));
        permissionButton.setOnClickListener(v -> requestAndroidPermissions());
        container.addView(permissionButton);

        // Spacer
        View sp1 = new View(this);
        sp1.setLayoutParams(new LinearLayout.LayoutParams(1, 16));
        container.addView(sp1);

        // Grant Consent Button
        grantButton = new Button(this);
        grantButton.setText("I AGREE & GRANT CONSENT (14 DAYS)");
        grantButton.setTextSize(13f);
        grantButton.setTextColor(Color.WHITE);
        grantButton.setTypeface(Typeface.DEFAULT_BOLD);
        grantButton.setBackgroundColor(Color.parseColor("#0284C7"));
        grantButton.setOnClickListener(v -> grantConsent());
        container.addView(grantButton);

        // Spacer
        View sp2 = new View(this);
        sp2.setLayoutParams(new LinearLayout.LayoutParams(1, 16));
        container.addView(sp2);

        // Revoke Consent Button
        revokeButton = new Button(this);
        revokeButton.setText("REVOKE CONSENT & TERMINATE MONITORING");
        revokeButton.setTextSize(12f);
        revokeButton.setTextColor(Color.parseColor("#FDA4AF"));
        revokeButton.setBackgroundColor(Color.parseColor("#881337"));
        revokeButton.setOnClickListener(v -> revokeConsent());
        container.addView(revokeButton);

        root.addView(container);
        setContentView(root);
    }

    private boolean checkAndroidPermissions() {
        boolean fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        boolean coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        return fine || coarse;
    }

    private void updatePermissionStatus(boolean granted) {
        if (granted) {
            permissionStatusText.setText("Android OS Permission: GRANTED ✓");
            permissionStatusText.setTextColor(Color.parseColor("#34D399"));
            permissionButton.setVisibility(View.GONE);
        } else {
            permissionStatusText.setText("Android OS Permission: NOT GRANTED");
            permissionStatusText.setTextColor(Color.parseColor("#F43F5E"));
            permissionButton.setVisibility(View.VISIBLE);
        }
    }

    private void requestAndroidPermissions() {
        List<String> perms = new ArrayList<>();
        perms.add(Manifest.permission.ACCESS_FINE_LOCATION);
        perms.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS);
        }
        locationPermissionLauncher.launch(perms.toArray(new String[0]));
    }

    private void refreshConsentState() {
        updatePermissionStatus(checkAndroidPermissions());

        progressBar.setVisibility(View.VISIBLE);
        apiClient.getMonitoringStatus(new HealthWatchApiClient.ApiCallback<PatientMonitoringStatusResponse>() {
            @Override
            public void onSuccess(PatientMonitoringStatusResponse status) {
                progressBar.setVisibility(View.GONE);
                if (status != null && status.isHasActiveConsent() && status.getActiveConsent() != null) {
                    ConsentResponse active = status.getActiveConsent();
                    consentStatusBadge.setText("CONSENT: ACTIVE (" + active.getConsentVersion() + ")");
                    consentStatusBadge.setBackgroundColor(Color.parseColor("#059669"));
                    consentValidUntilText.setText("Authorized Window: Valid until " + active.getMonitoringEnd());
                    grantButton.setVisibility(View.GONE);
                    revokeButton.setVisibility(View.VISIBLE);
                } else {
                    consentStatusBadge.setText("CONSENT: NOT ACTIVE / REVOKED");
                    consentStatusBadge.setBackgroundColor(Color.parseColor("#475569"));
                    consentValidUntilText.setText("Authorized Window: Explicit agreement required.");
                    grantButton.setVisibility(View.VISIBLE);
                    revokeButton.setVisibility(View.GONE);
                }
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                feedbackMessageText.setText("Failed to query consent: " + (e != null ? e.getMessage() : "Unknown"));
                feedbackMessageText.setVisibility(View.VISIBLE);
            }
        });
    }

    private void grantConsent() {
        if (!checkAndroidPermissions()) {
            requestAndroidPermissions();
            return;
        }

        progressBar.setVisibility(View.VISIBLE);
        apiClient.grantConsent(new ConsentGrantRequest(14), new HealthWatchApiClient.ApiCallback<ConsentResponse>() {
            @Override
            public void onSuccess(ConsentResponse consent) {
                progressBar.setVisibility(View.GONE);
                feedbackMessageText.setText("Explicit 14-day consent granted successfully.");
                feedbackMessageText.setTextColor(Color.parseColor("#34D399"));
                feedbackMessageText.setVisibility(View.VISIBLE);
                refreshConsentState();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                feedbackMessageText.setText("Error granting consent: " + (e != null ? e.getMessage() : "Unknown"));
                feedbackMessageText.setTextColor(Color.parseColor("#FDA4AF"));
                feedbackMessageText.setVisibility(View.VISIBLE);
            }
        });
    }

    private void revokeConsent() {
        progressBar.setVisibility(View.VISIBLE);
        apiClient.revokeConsent(new ConsentRevokeRequest(), new HealthWatchApiClient.ApiCallback<ConsentResponse>() {
            @Override
            public void onSuccess(ConsentResponse consent) {
                progressBar.setVisibility(View.GONE);
                feedbackMessageText.setText("Location consent revoked. All active sessions stopped.");
                feedbackMessageText.setTextColor(Color.parseColor("#FDA4AF"));
                feedbackMessageText.setVisibility(View.VISIBLE);
                refreshConsentState();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                feedbackMessageText.setText("Error revoking consent: " + (e != null ? e.getMessage() : "Unknown"));
                feedbackMessageText.setVisibility(View.VISIBLE);
            }
        });
    }
}
