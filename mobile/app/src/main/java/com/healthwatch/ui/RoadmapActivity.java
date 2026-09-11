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
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.RoadmapModels.MobilePoint;
import com.healthwatch.data.model.RoadmapModels.MobileRoadmapObservation;
import com.healthwatch.data.model.RoadmapModels.MobileRoadmapResponse;
import com.healthwatch.data.model.RoadmapModels.MobileRoadmapStatistics;
import java.util.List;
import java.util.Locale;

public class RoadmapActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;

    private LinearLayout container;
    private ProgressBar progressBar;
    private TextView errorText;
    private LinearLayout statsContainer;
    private LinearLayout timelineContainer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        buildUi();
        loadRoadmap();
    }


    private void buildUi() {
        ScrollView root = new ScrollView(this);
        root.setBackgroundColor(Color.parseColor("#0B1120"));
        root.setFillViewport(true);

        container = new LinearLayout(this);
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
        headerTitle.setText("Movement Roadmap");
        headerTitle.setTextSize(22f);
        headerTitle.setTextColor(Color.WHITE);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setPadding(0, 16, 0, 4);

        TextView headerSubtitle = new TextView(this);
        headerSubtitle.setText("Sequential discrete location observations stream");
        headerSubtitle.setTextSize(12f);
        headerSubtitle.setTextColor(Color.parseColor("#94A3B8"));
        headerSubtitle.setPadding(0, 0, 0, 20);

        container.addView(headerTitle);
        container.addView(headerSubtitle);

        // Technical Notice Card
        LinearLayout noticeCard = new LinearLayout(this);
        noticeCard.setOrientation(LinearLayout.VERTICAL);
        noticeCard.setBackgroundColor(Color.parseColor("#1C1917")); // Stone 900
        noticeCard.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 24);
        noticeCard.setLayoutParams(params);

        TextView noticeTitle = new TextView(this);
        noticeTitle.setText("⚠️ IMPORTANT TECHNICAL CLARIFICATION");
        noticeTitle.setTextSize(12f);
        noticeTitle.setTextColor(Color.parseColor("#FBBF24")); // Amber 400
        noticeTitle.setTypeface(Typeface.DEFAULT_BOLD);

        TextView noticeBody = new TextView(this);
        noticeBody.setText("HealthWatch is NOT performing continuous second-by-second GPS tracking.\n\nObservations are recorded periodically (approx. 15-minute sampling interval). The connecting polyline represents a sequential visual timeline, NOT an exact continuous travel trajectory.");
        noticeBody.setTextSize(12f);
        noticeBody.setTextColor(Color.parseColor("#CBD5E1"));
        noticeBody.setLineSpacing(4f, 1.2f);
        noticeBody.setPadding(0, 8, 0, 0);

        noticeCard.addView(noticeTitle);
        noticeCard.addView(noticeBody);
        container.addView(noticeCard);

        // Progress Bar
        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.VISIBLE);
        progressBar.setPadding(0, 16, 0, 16);
        container.addView(progressBar);

        // Error Text
        errorText = new TextView(this);
        errorText.setTextSize(12f);
        errorText.setTextColor(Color.parseColor("#FDA4AF"));
        errorText.setVisibility(View.GONE);
        errorText.setPadding(0, 0, 0, 16);
        container.addView(errorText);

        // Statistics Container
        statsContainer = new LinearLayout(this);
        statsContainer.setOrientation(LinearLayout.VERTICAL);
        container.addView(statsContainer);

        // Timeline Section Title
        TextView timelineTitle = new TextView(this);
        timelineTitle.setText("CHRONOLOGICAL OBSERVATION TIMELINE (~15 MIN)");
        timelineTitle.setTextSize(11f);
        timelineTitle.setTextColor(Color.parseColor("#64748B"));
        timelineTitle.setTypeface(Typeface.DEFAULT_BOLD);
        timelineTitle.setPadding(0, 24, 0, 12);
        container.addView(timelineTitle);

        // Timeline Container
        timelineContainer = new LinearLayout(this);
        timelineContainer.setOrientation(LinearLayout.VERTICAL);
        container.addView(timelineContainer);

        root.addView(container);
        setContentView(root);
    }

    private void loadRoadmap() {
        progressBar.setVisibility(View.VISIBLE);
        errorText.setVisibility(View.GONE);

        apiClient.getMovementRoadmap(null, new HealthWatchApiClient.ApiCallback<MobileRoadmapResponse>() {
            @Override
            public void onSuccess(MobileRoadmapResponse roadmap) {
                progressBar.setVisibility(View.GONE);
                if (roadmap != null) {
                    renderRoadmap(roadmap);
                } else {
                    errorText.setText("No roadmap data returned by the server.");
                    errorText.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                String msg = e != null && e.getMessage() != null ? e.getMessage() : "Unknown error";
                errorText.setText("Failed to load roadmap: " + msg);
                errorText.setVisibility(View.VISIBLE);
            }
        });
    }

    private void renderRoadmap(MobileRoadmapResponse roadmap) {
        statsContainer.removeAllViews();
        timelineContainer.removeAllViews();

        // 1. Render Statistics Card
        LinearLayout statsCard = new LinearLayout(this);
        statsCard.setOrientation(LinearLayout.VERTICAL);
        statsCard.setBackgroundColor(Color.parseColor("#1E293B"));
        statsCard.setPadding(28, 24, 28, 24);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 16);
        statsCard.setLayoutParams(params);

        MobileRoadmapStatistics s = roadmap.getStatistics();
        int totalObs = s != null ? s.getTotalObservations() : 0;
        String start = s != null && s.getMonitoringStart() != null ? s.getMonitoringStart() : "—";
        String end = s != null && s.getMonitoringEnd() != null ? s.getMonitoringEnd() : "—";
        String accStr = (s != null && s.getAverageAccuracy() != null)
                ? String.format(Locale.US, "±%.1fm", s.getAverageAccuracy())
                : "N/A";

        addStatRow(statsCard, "Total Discrete Observations", totalObs + " points recorded");
        addStatRow(statsCard, "Surveillance Cadence", "Periodic Discrete Observations");
        addStatRow(statsCard, "First Recorded Point", start);
        addStatRow(statsCard, "Last Recorded Point", end);
        addStatRow(statsCard, "Average Accuracy", accStr);

        if (!roadmap.isHasPhone() || roadmap.isStaticAdminLocation()) {
            addStatRow(statsCard, "Location Mode", "STATIC_ADMIN_LOCATION (No smartphone registered)");
        }

        statsContainer.addView(statsCard);

        // 2. Render Timeline Points
        List<MobileRoadmapObservation> observations = roadmap.getObservations();
        if (observations == null || observations.isEmpty()) {
            TextView empty = new TextView(this);
            empty.setText("No recorded location observations available.");
            empty.setTextColor(Color.parseColor("#94A3B8"));
            empty.setTextSize(13f);
            timelineContainer.addView(empty);
            return;
        }

        int total = observations.size();
        for (int idx = 0; idx < total; idx++) {
            MobileRoadmapObservation obs = observations.get(idx);
            boolean isStart = (idx == 0);
            boolean isEnd = (idx == total - 1 && total > 1);
            int pointNumber = obs.getObservationNumber() != null ? obs.getObservationNumber() : (idx + 1);

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

            // Header row: Point N • Source
            LinearLayout headerRow = new LinearLayout(this);
            headerRow.setOrientation(LinearLayout.HORIZONTAL);
            headerRow.setGravity(Gravity.CENTER_VERTICAL);

            String badgeText;
            if (isStart) {
                badgeText = "Point " + pointNumber + " (START)";
            } else if (isEnd) {
                badgeText = "Point " + pointNumber + " (END)";
            } else {
                badgeText = "Point " + pointNumber;
            }

            TextView titleView = new TextView(this);
            titleView.setText(badgeText);
            titleView.setTextSize(14f);
            if (isStart) {
                titleView.setTextColor(Color.parseColor("#34D399"));
            } else if (isEnd) {
                titleView.setTextColor(Color.parseColor("#F43F5E"));
            } else {
                titleView.setTextColor(Color.parseColor("#38BDF8"));
            }
            titleView.setTypeface(Typeface.DEFAULT_BOLD);
            titleView.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

            TextView sourceView = new TextView(this);
            sourceView.setText(obs.getSource());
            sourceView.setTextSize(10f);
            sourceView.setTextColor(Color.WHITE);
            sourceView.setTypeface(Typeface.DEFAULT_BOLD);
            sourceView.setBackgroundColor(
                    "PATIENT_GPS".equals(obs.getSource()) ? Color.parseColor("#059669") : Color.parseColor("#4F46E5")
            );
            sourceView.setPadding(12, 4, 12, 4);

            headerRow.addView(titleView);
            headerRow.addView(sourceView);
            itemCard.addView(headerRow);

            // Coordinates & Accuracy
            String acc = obs.getAccuracy() != null ? String.format(Locale.US, "±%.1fm", obs.getAccuracy()) : "N/A";
            TextView coordView = new TextView(this);
            coordView.setText(String.format(Locale.US, "📍 Lat: %.4f, Lng: %.4f • Acc: %s", obs.getLatitude(), obs.getLongitude(), acc));
            coordView.setTextSize(12f);
            coordView.setTextColor(Color.WHITE);
            coordView.setPadding(0, 6, 0, 4);

            TextView timeView = new TextView(this);
            timeView.setText("Recorded At: " + obs.getRecordedAt());
            timeView.setTextSize(11f);
            timeView.setTextColor(Color.parseColor("#94A3B8"));

            itemCard.addView(coordView);
            itemCard.addView(timeView);
            timelineContainer.addView(itemCard);
        }
    }

    private void addStatRow(LinearLayout parent, String label, String value) {
        TextView labelView = new TextView(this);
        labelView.setText(label);
        labelView.setTextSize(11f);
        labelView.setTextColor(Color.parseColor("#94A3B8"));

        TextView valueView = new TextView(this);
        valueView.setText(value);
        valueView.setTextSize(13f);
        valueView.setTextColor(Color.WHITE);
        valueView.setTypeface(Typeface.DEFAULT_BOLD);
        valueView.setPadding(0, 2, 0, 10);

        parent.addView(labelView);
        parent.addView(valueView);
    }
}
