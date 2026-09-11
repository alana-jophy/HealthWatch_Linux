package com.healthwatch.data.model;

import com.google.gson.annotations.SerializedName;
import java.util.ArrayList;
import java.util.List;

public class RoadmapModels {

    public static class MobilePoint {
        @SerializedName("latitude")
        private double latitude;

        @SerializedName("longitude")
        private double longitude;

        public MobilePoint() {}

        public MobilePoint(double latitude, double longitude) {
            this.latitude = latitude;
            this.longitude = longitude;
        }

        public double getLatitude() { return latitude; }
        public void setLatitude(double latitude) { this.latitude = latitude; }

        public double getLongitude() { return longitude; }
        public void setLongitude(double longitude) { this.longitude = longitude; }
    }

    public static class MobileRoadmapStatistics {
        @SerializedName("total_observations")
        private int totalObservations;

        @SerializedName("monitoring_start")
        private String monitoringStart;

        @SerializedName("monitoring_end")
        private String monitoringEnd;

        @SerializedName("first_recorded_location")
        private MobilePoint firstRecordedLocation;

        @SerializedName("last_recorded_location")
        private MobilePoint lastRecordedLocation;

        @SerializedName("average_accuracy")
        private Float averageAccuracy;

        public MobileRoadmapStatistics() {}

        public int getTotalObservations() { return totalObservations; }
        public void setTotalObservations(int totalObservations) { this.totalObservations = totalObservations; }

        public String getMonitoringStart() { return monitoringStart; }
        public void setMonitoringStart(String monitoringStart) { this.monitoringStart = monitoringStart; }

        public String getMonitoringEnd() { return monitoringEnd; }
        public void setMonitoringEnd(String monitoringEnd) { this.monitoringEnd = monitoringEnd; }

        public MobilePoint getFirstRecordedLocation() { return firstRecordedLocation; }
        public void setFirstRecordedLocation(MobilePoint firstRecordedLocation) { this.firstRecordedLocation = firstRecordedLocation; }

        public MobilePoint getLastRecordedLocation() { return lastRecordedLocation; }
        public void setLastRecordedLocation(MobilePoint lastRecordedLocation) { this.lastRecordedLocation = lastRecordedLocation; }

        public Float getAverageAccuracy() { return averageAccuracy; }
        public void setAverageAccuracy(Float averageAccuracy) { this.averageAccuracy = averageAccuracy; }
    }

    public static class MobileRoadmapObservation {
        @SerializedName("id")
        private String id;

        @SerializedName("observation_number")
        private Integer observationNumber;

        @SerializedName("recorded_at")
        private String recordedAt;

        @SerializedName("latitude")
        private double latitude;

        @SerializedName("longitude")
        private double longitude;

        @SerializedName("accuracy")
        private Float accuracy;

        @SerializedName("source")
        private String source = "PATIENT_GPS";

        @SerializedName("session_id")
        private String sessionId;

        public MobileRoadmapObservation() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public Integer getObservationNumber() { return observationNumber; }
        public void setObservationNumber(Integer observationNumber) { this.observationNumber = observationNumber; }

        public String getRecordedAt() { return recordedAt; }
        public void setRecordedAt(String recordedAt) { this.recordedAt = recordedAt; }

        public double getLatitude() { return latitude; }
        public void setLatitude(double latitude) { this.latitude = latitude; }

        public double getLongitude() { return longitude; }
        public void setLongitude(double longitude) { this.longitude = longitude; }

        public Float getAccuracy() { return accuracy; }
        public void setAccuracy(Float accuracy) { this.accuracy = accuracy; }

        public String getSource() { return source != null ? source : "PATIENT_GPS"; }
        public void setSource(String source) { this.source = source; }

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    }

    public static class MobileRoadmapResponse {
        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("patient_pseudo_id")
        private String patientPseudoId;

        @SerializedName("patient_name")
        private String patientName;

        @SerializedName("session_id")
        private String sessionId;

        @SerializedName("filter_date")
        private String filterDate;

        @SerializedName("disclaimer")
        private String disclaimer;

        @SerializedName("disclaimer_title")
        private String disclaimerTitle;

        @SerializedName("disclaimer_text")
        private String disclaimerText;

        @SerializedName("has_phone")
        private boolean hasPhone = true;

        @SerializedName("is_static_admin_location")
        private boolean isStaticAdminLocation = false;

        @SerializedName("statistics")
        private MobileRoadmapStatistics statistics;

        @SerializedName("observations")
        private List<MobileRoadmapObservation> observations = new ArrayList<>();

        public MobileRoadmapResponse() {}

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getPatientPseudoId() { return patientPseudoId; }
        public void setPatientPseudoId(String patientPseudoId) { this.patientPseudoId = patientPseudoId; }

        public String getPatientName() { return patientName; }
        public void setPatientName(String patientName) { this.patientName = patientName; }

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }

        public String getFilterDate() { return filterDate; }
        public void setFilterDate(String filterDate) { this.filterDate = filterDate; }

        public String getDisclaimer() { return disclaimer; }
        public void setDisclaimer(String disclaimer) { this.disclaimer = disclaimer; }

        public String getDisclaimerTitle() { return disclaimerTitle; }
        public void setDisclaimerTitle(String disclaimerTitle) { this.disclaimerTitle = disclaimerTitle; }

        public String getDisclaimerText() { return disclaimerText; }
        public void setDisclaimerText(String disclaimerText) { this.disclaimerText = disclaimerText; }

        public boolean isHasPhone() { return hasPhone; }
        public void setHasPhone(boolean hasPhone) { this.hasPhone = hasPhone; }

        public boolean isStaticAdminLocation() { return isStaticAdminLocation; }
        public void setStaticAdminLocation(boolean staticAdminLocation) { isStaticAdminLocation = staticAdminLocation; }

        public MobileRoadmapStatistics getStatistics() { return statistics; }
        public void setStatistics(MobileRoadmapStatistics statistics) { this.statistics = statistics; }

        public List<MobileRoadmapObservation> getObservations() { return observations != null ? observations : new ArrayList<MobileRoadmapObservation>(); }
        public void setObservations(List<MobileRoadmapObservation> observations) { this.observations = observations; }
    }
}
