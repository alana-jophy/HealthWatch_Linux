package com.healthwatch.ui;

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
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.OfflineLocationQueue;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.LocationModels.QueuedLocationObservation;
import java.util.List;
import java.util.Locale;

public class LocationHistoryActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;
    private OfflineLocationQueue offlineQueue;

    private TextView summaryText;
    private Button syncButton;
    private LinearLayout listContainer;
    private ProgressBar progressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);
        offlineQueue = new OfflineLocationQueue(this);

        buildUi();
        loadLocationHistory();
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
        headerTitle.setText("Location Telemetry History");
        headerTitle.setTextSize(22f);
        headerTitle.setTextColor(Color.WHITE);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setPadding(0, 16, 0, 8);
        container.addView(headerTitle);

        // Queue Control Panel Card
        LinearLayout controlCard = new LinearLayout(this);
        controlCard.setOrientation(LinearLayout.VERTICAL);
        controlCard.setBackgroundColor(Color.parseColor("#1E293B"));
        controlCard.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 8, 0, 24);
        controlCard.setLayoutParams(params);

        summaryText = new TextView(this);
        summaryText.setText("Checking offline storage...");
        summaryText.setTextSize(13f);
        summaryText.setTextColor(Color.WHITE);
        summaryText.setPadding(0, 0, 0, 16);
        controlCard.addView(summaryText);

        syncButton = new Button(this);
        syncButton.setText("SYNC OFFLINE QUEUE NOW");
        syncButton.setTextSize(12f);
        syncButton.setTextColor(Color.WHITE);
        syncButton.setTypeface(Typeface.DEFAULT_BOLD);
        syncButton.setBackgroundColor(Color.parseColor("#0284C7"));
        syncButton.setOnClickListener(v -> syncOfflineQueue());
        controlCard.addView(syncButton);

        Button clearButton = new Button(this);
        clearButton.setText("CLEAR LOCAL CACHE");
        clearButton.setTextSize(12f);
        clearButton.setTextColor(Color.parseColor("#FDA4AF"));
        clearButton.setBackgroundColor(Color.parseColor("#334155"));
        LinearLayout.LayoutParams clearParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        clearParams.setMargins(0, 10, 0, 0);
        clearButton.setLayoutParams(clearParams);
        clearButton.setOnClickListener(v -> {
            offlineQueue.clearAllObservations();
            Toast.makeText(this, "Local offline location queue cleared.", Toast.LENGTH_SHORT).show();
            loadLocationHistory();
        });
        controlCard.addView(clearButton);

        container.addView(controlCard);

        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.GONE);
        progressBar.setPadding(0, 0, 0, 16);
        container.addView(progressBar);

        TextView listTitle = new TextView(this);
        listTitle.setText("RECORDED OBSERVATIONS (SOURCE: PATIENT_GPS)");
        listTitle.setTextSize(11f);
        listTitle.setTextColor(Color.parseColor("#64748B"));
        listTitle.setTypeface(Typeface.DEFAULT_BOLD);
        listTitle.setPadding(0, 8, 0, 12);
        container.addView(listTitle);

        listContainer = new LinearLayout(this);
        listContainer.setOrientation(LinearLayout.VERTICAL);
        container.addView(listContainer);

        root.addView(container);
        setContentView(root);
    }

    private void loadLocationHistory() {
        String pseudoId = sessionManager.getPatientPseudoId();
        String uuidId = sessionManager.getPatientId();

        // Enforce strict device isolation: purge any orphan/prior patient records on this phone
        offlineQueue.purgeOtherPatients(pseudoId, uuidId);

        List<QueuedLocationObservation> observations = offlineQueue.getAllObservationsForPatient(pseudoId, uuidId, 100);
        int pendingCount = offlineQueue.getPendingCountForPatient(pseudoId, uuidId);

        String idLabel = (pseudoId != null && !pseudoId.trim().isEmpty()) ? pseudoId : "Current Patient";
        summaryText.setText("Patient: " + idLabel + "\nStored: " + observations.size() + " observations (" + pendingCount + " pending server upload)");

        listContainer.removeAllViews();

        if (observations.isEmpty()) {
            TextView emptyView = new TextView(this);
            emptyView.setText("No location observations collected yet for patient (" + idLabel + ").\n\nStart an active monitoring session to begin periodic ~15-minute telemetry.");
            emptyView.setTextSize(13f);
            emptyView.setTextColor(Color.parseColor("#94A3B8"));
            emptyView.setLineSpacing(4f, 1.2f);
            emptyView.setPadding(0, 16, 0, 0);
            listContainer.addView(emptyView);
            return;
        }

        for (QueuedLocationObservation item : observations) {
            LinearLayout itemCard = new LinearLayout(this);
            itemCard.setOrientation(LinearLayout.VERTICAL);
            itemCard.setBackgroundColor(Color.parseColor("#1E293B"));
            itemCard.setPadding(24, 20, 24, 20);
            LinearLayout.LayoutParams itemParams = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
            );
            itemParams.setMargins(0, 0, 0, 12);
            itemCard.setLayoutParams(itemParams);

            TextView coordText = new TextView(this);
            coordText.setText(String.format(Locale.US, "📍 Lat: %.5f, Lng: %.5f", item.getLatitude(), item.getLongitude()));
            coordText.setTextSize(14f);
            coordText.setTextColor(Color.WHITE);
            coordText.setTypeface(Typeface.DEFAULT_BOLD);

            String acc = item.getAccuracy() != null ? String.format(Locale.US, "±%.1fm", item.getAccuracy()) : "N/A";
            TextView metaText = new TextView(this);
            metaText.setText("Accuracy: " + acc + " • Source: " + item.getSource() + " • Time: " + item.getRecordedAt());
            metaText.setTextSize(11f);
            metaText.setTextColor(Color.parseColor("#94A3B8"));
            metaText.setPadding(0, 4, 0, 8);

            TextView statusBadge = new TextView(this);
            boolean isSynced = "SYNCED".equals(item.getSyncStatus());
            statusBadge.setText(isSynced ? "SYNCED TO SERVER ✓" : "QUEUED OFFLINE (PENDING)");
            statusBadge.setTextSize(10f);
            statusBadge.setTextColor(Color.WHITE);
            statusBadge.setTypeface(Typeface.DEFAULT_BOLD);
            statusBadge.setBackgroundColor(isSynced ? Color.parseColor("#059669") : Color.parseColor("#D97706"));
            statusBadge.setPadding(12, 6, 12, 6);
            statusBadge.setGravity(Gravity.CENTER_VERTICAL);

            itemCard.addView(coordText);
            itemCard.addView(metaText);
            itemCard.addView(statusBadge);
            listContainer.addView(itemCard);
        }
    }

    private void syncOfflineQueue() {
        String pseudoId = sessionManager.getPatientPseudoId();
        String uuidId = sessionManager.getPatientId();
        int pending = offlineQueue.getPendingCountForPatient(pseudoId, uuidId);
        if (pending == 0) {
            Toast.makeText(this, "No pending offline observations to sync for this patient profile.", Toast.LENGTH_SHORT).show();
            return;
        }

        progressBar.setVisibility(View.VISIBLE);
        syncButton.setEnabled(false);

        apiClient.flushOfflineQueue(offlineQueue, new HealthWatchApiClient.ApiCallback<int[]>() {
            @Override
            public void onSuccess(int[] counts) {
                progressBar.setVisibility(View.GONE);
                syncButton.setEnabled(true);
                int synced = counts != null && counts.length > 0 ? counts[0] : 0;
                int failed = counts != null && counts.length > 1 ? counts[1] : 0;
                Toast.makeText(LocationHistoryActivity.this, "Sync Complete: " + synced + " uploaded, " + failed + " failed/offline.", Toast.LENGTH_SHORT).show();
                loadLocationHistory();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                syncButton.setEnabled(true);
                Toast.makeText(LocationHistoryActivity.this, "Sync Error: " + (e != null ? e.getMessage() : "Unknown"), Toast.LENGTH_SHORT).show();
                loadLocationHistory();
            }
        });
    }
}
