package com.healthwatch.ui;

import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.PatientModels.DiseaseCase;
import com.healthwatch.data.model.PatientModels.DiseaseInfo;
import java.util.List;

public class DiseaseCaseActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;
    private LinearLayout contentContainer;
    private ProgressBar progressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        buildUi();
        loadCaseData();
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
        headerTitle.setText("My Disease Case");
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

    private void loadCaseData() {
        apiClient.getDiseaseCases(new HealthWatchApiClient.ApiCallback<List<DiseaseCase>>() {
            @Override
            public void onSuccess(List<DiseaseCase> cases) {
                progressBar.setVisibility(View.GONE);
                contentContainer.setVisibility(View.VISIBLE);

                if (cases != null && !cases.isEmpty()) {
                    renderCaseDetails(cases.get(0));
                } else {
                    renderEmptyCase();
                }
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                contentContainer.setVisibility(View.VISIBLE);

                TextView errorView = new TextView(DiseaseCaseActivity.this);
                errorView.setText("Failed to load clinical case: " + (e != null ? e.getMessage() : "Unknown"));
                errorView.setTextColor(Color.parseColor("#FDA4AF"));
                errorView.setTextSize(13f);
                contentContainer.addView(errorView);
            }
        });
    }

    private void renderEmptyCase() {
        TextView view = new TextView(this);
        view.setText("No active clinical disease case registered for this patient profile.");
        view.setTextColor(Color.parseColor("#94A3B8"));
        view.setTextSize(14f);
        view.setPadding(0, 24, 0, 0);
        contentContainer.addView(view);
    }

    private void renderCaseDetails(DiseaseCase diseaseCase) {
        contentContainer.removeAllViews();

        // Card 1: Clinical Diagnosis
        LinearLayout diagCard = new LinearLayout(this);
        diagCard.setOrientation(LinearLayout.VERTICAL);
        diagCard.setBackgroundColor(Color.parseColor("#1E293B"));
        diagCard.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 20);
        diagCard.setLayoutParams(params);

        DiseaseInfo info = diseaseCase.getDisease();
        String name = info != null && info.getName() != null ? info.getName() : "Dengue Fever";
        String code = info != null && info.getCode() != null ? info.getCode() : "DENGUE-01";
        String contagion = info != null && info.getContagionType() != null ? info.getContagionType() : "CONTAGIOUS";

        TextView diseaseName = new TextView(this);
        diseaseName.setText(name);
        diseaseName.setTextSize(20f);
        diseaseName.setTextColor(Color.WHITE);
        diseaseName.setTypeface(Typeface.DEFAULT_BOLD);

        TextView diseaseCode = new TextView(this);
        diseaseCode.setText("CODE: " + code + " • " + contagion);
        diseaseCode.setTextSize(12f);
        diseaseCode.setTextColor(Color.parseColor("#38BDF8"));
        diseaseCode.setPadding(0, 4, 0, 16);

        diagCard.addView(diseaseName);
        diagCard.addView(diseaseCode);

        // Status Badge
        String status = diseaseCase.getCaseStatus() != null ? diseaseCase.getCaseStatus() : "CONFIRMED";
        TextView statusBadge = new TextView(this);
        statusBadge.setText("CASE STATUS: " + status);
        statusBadge.setTextSize(12f);
        statusBadge.setTextColor(Color.WHITE);
        statusBadge.setTypeface(Typeface.DEFAULT_BOLD);
        if ("CONFIRMED".equalsIgnoreCase(status)) {
            statusBadge.setBackgroundColor(Color.parseColor("#E11D48")); // Red
        } else if ("RECOVERED".equalsIgnoreCase(status)) {
            statusBadge.setBackgroundColor(Color.parseColor("#059669")); // Green
        } else {
            statusBadge.setBackgroundColor(Color.parseColor("#D97706")); // Amber
        }
        statusBadge.setPadding(16, 8, 16, 8);
        diagCard.addView(statusBadge);

        contentContainer.addView(diagCard);

        // Card 2: Epidemiological Metadata
        LinearLayout metaCard = new LinearLayout(this);
        metaCard.setOrientation(LinearLayout.VERTICAL);
        metaCard.setBackgroundColor(Color.parseColor("#1E293B"));
        metaCard.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams metaParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        metaParams.setMargins(0, 0, 0, 20);
        metaCard.setLayoutParams(metaParams);

        addMetaRow(metaCard, "Diagnosis Date", diseaseCase.getDiagnosisDate() != null ? diseaseCase.getDiagnosisDate() : "—");
        addMetaRow(metaCard, "Severity Classification", diseaseCase.getSeverity() != null ? diseaseCase.getSeverity() : "—");
        addMetaRow(metaCard, "Surveillance Data Source", diseaseCase.getSource() != null ? diseaseCase.getSource() : "SIMULATED");
        addMetaRow(metaCard, "Clinical Notes", diseaseCase.getClinicalNotes() != null ? diseaseCase.getClinicalNotes() : "Patient presenting with acute vector-borne symptoms under isolation.");

        contentContainer.addView(metaCard);
    }

    private void addMetaRow(LinearLayout parent, String label, String value) {
        TextView labelView = new TextView(this);
        labelView.setText(label);
        labelView.setTextSize(11f);
        labelView.setTextColor(Color.parseColor("#94A3B8"));

        TextView valueView = new TextView(this);
        valueView.setText(value);
        valueView.setTextSize(13f);
        valueView.setTextColor(Color.WHITE);
        valueView.setPadding(0, 2, 0, 12);

        parent.addView(labelView);
        parent.addView(valueView);
    }
}
