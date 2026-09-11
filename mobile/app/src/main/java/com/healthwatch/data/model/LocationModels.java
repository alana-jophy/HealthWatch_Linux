package com.healthwatch.data.model;

import com.google.gson.annotations.SerializedName;
import java.util.ArrayList;
import java.util.List;

public class LocationModels {

    public static class LocationObservationSubmit {
        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("monitoring_session_id")
        private String monitoringSessionId;

        @SerializedName("latitude")
        private double latitude;

        @SerializedName("longitude")
        private double longitude;

        @SerializedName("accuracy")
        private Float accuracy;

        @SerializedName("recorded_at")
        private String recordedAt;

        @SerializedName("source")
        private String source = "PATIENT_GPS";

        @SerializedName("speed_mps")
        private Float speedMps;

        @SerializedName("altitude")
        private Double altitude;

        @SerializedName("is_mock_provider")
        private boolean isMockProvider = false;

        public LocationObservationSubmit() {}

        public LocationObservationSubmit(String patientId, String monitoringSessionId, double latitude, double longitude, Float accuracy, String recordedAt, String source) {
            this.patientId = patientId;
            this.monitoringSessionId = monitoringSessionId;
            this.latitude = latitude;
            this.longitude = longitude;
            this.accuracy = accuracy;
            this.recordedAt = recordedAt;
            this.source = source != null ? source : "PATIENT_GPS";
        }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getMonitoringSessionId() { return monitoringSessionId; }
        public void setMonitoringSessionId(String monitoringSessionId) { this.monitoringSessionId = monitoringSessionId; }

        public double getLatitude() { return latitude; }
        public void setLatitude(double latitude) { this.latitude = latitude; }

        public double getLongitude() { return longitude; }
        public void setLongitude(double longitude) { this.longitude = longitude; }

        public Float getAccuracy() { return accuracy; }
        public void setAccuracy(Float accuracy) { this.accuracy = accuracy; }

        public String getRecordedAt() { return recordedAt; }
        public void setRecordedAt(String recordedAt) { this.recordedAt = recordedAt; }

        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }

        public Float getSpeedMps() { return speedMps; }
        public void setSpeedMps(Float speedMps) { this.speedMps = speedMps; }

        public Double getAltitude() { return altitude; }
        public void setAltitude(Double altitude) { this.altitude = altitude; }

        public boolean isMockProvider() { return isMockProvider; }
        public void setMockProvider(boolean mockProvider) { isMockProvider = mockProvider; }
    }

    public static class LocationObservationResponse {
        @SerializedName("id")
        private String id;

        @SerializedName("session_id")
        private String sessionId;

        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("recorded_at")
        private String recordedAt;

        @SerializedName("latitude")
        private double latitude;

        @SerializedName("longitude")
        private double longitude;

        @SerializedName("accuracy_meters")
        private Float accuracyMeters;

        @SerializedName("source")
        private String source;

        @SerializedName("status")
        private String status;

        @SerializedName("message")
        private String message;

        public LocationObservationResponse() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getRecordedAt() { return recordedAt; }
        public void setRecordedAt(String recordedAt) { this.recordedAt = recordedAt; }

        public double getLatitude() { return latitude; }
        public void setLatitude(double latitude) { this.latitude = latitude; }

        public double getLongitude() { return longitude; }
        public void setLongitude(double longitude) { this.longitude = longitude; }

        public Float getAccuracyMeters() { return accuracyMeters; }
        public void setAccuracyMeters(Float accuracyMeters) { this.accuracyMeters = accuracyMeters; }

        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }

        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }

        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
    }

    public static class BatchLocationSyncRequest {
        @SerializedName("session_id")
        private String sessionId;

        @SerializedName("locations")
        private List<LocationObservationSubmit> locations = new ArrayList<>();

        public BatchLocationSyncRequest() {}

        public BatchLocationSyncRequest(String sessionId, List<LocationObservationSubmit> locations) {
            this.sessionId = sessionId;
            this.locations = locations;
        }

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }

        public List<LocationObservationSubmit> getLocations() { return locations; }
        public void setLocations(List<LocationObservationSubmit> locations) { this.locations = locations; }
    }

    public static class BatchLocationSyncResponse {
        @SerializedName("status")
        private String status;

        @SerializedName("synced_count")
        private int syncedCount;

        @SerializedName("duplicate_count")
        private int duplicateCount;

        @SerializedName("total_received")
        private int totalReceived;

        @SerializedName("observation_ids")
        private List<String> observationIds = new ArrayList<>();

        public BatchLocationSyncResponse() {}

        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }

        public int getSyncedCount() { return syncedCount; }
        public void setSyncedCount(int syncedCount) { this.syncedCount = syncedCount; }

        public int getDuplicateCount() { return duplicateCount; }
        public void setDuplicateCount(int duplicateCount) { this.duplicateCount = duplicateCount; }

        public int getTotalReceived() { return totalReceived; }
        public void setTotalReceived(int totalReceived) { this.totalReceived = totalReceived; }

        public List<String> getObservationIds() { return observationIds; }
        public void setObservationIds(List<String> observationIds) { this.observationIds = observationIds; }
    }

    public static class QueuedLocationObservation {
        private long localId = 0;
        private String patientId;
        private String monitoringSessionId;
        private double latitude;
        private double longitude;
        private Float accuracy;
        private String recordedAt;
        private String source = "PATIENT_GPS";
        private String syncStatus = "PENDING";
        private int retryCount = 0;
        private long createdAt = System.currentTimeMillis();

        public QueuedLocationObservation() {}

        public QueuedLocationObservation(long localId, String patientId, String monitoringSessionId, double latitude, double longitude, Float accuracy, String recordedAt, String source, String syncStatus, int retryCount, long createdAt) {
            this.localId = localId;
            this.patientId = patientId;
            this.monitoringSessionId = monitoringSessionId;
            this.latitude = latitude;
            this.longitude = longitude;
            this.accuracy = accuracy;
            this.recordedAt = recordedAt;
            this.source = source != null ? source : "PATIENT_GPS";
            this.syncStatus = syncStatus != null ? syncStatus : "PENDING";
            this.retryCount = retryCount;
            this.createdAt = createdAt;
        }

        public QueuedLocationObservation(String patientId, String monitoringSessionId, double latitude, double longitude, Float accuracy, String recordedAt, String source) {
            this.patientId = patientId;
            this.monitoringSessionId = monitoringSessionId;
            this.latitude = latitude;
            this.longitude = longitude;
            this.accuracy = accuracy;
            this.recordedAt = recordedAt;
            this.source = source != null ? source : "PATIENT_GPS";
            this.syncStatus = "PENDING";
            this.retryCount = 0;
            this.createdAt = System.currentTimeMillis();
        }

        public long getLocalId() { return localId; }
        public void setLocalId(long localId) { this.localId = localId; }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getMonitoringSessionId() { return monitoringSessionId; }
        public void setMonitoringSessionId(String monitoringSessionId) { this.monitoringSessionId = monitoringSessionId; }

        public double getLatitude() { return latitude; }
        public void setLatitude(double latitude) { this.latitude = latitude; }

        public double getLongitude() { return longitude; }
        public void setLongitude(double longitude) { this.longitude = longitude; }

        public Float getAccuracy() { return accuracy; }
        public void setAccuracy(Float accuracy) { this.accuracy = accuracy; }

        public String getRecordedAt() { return recordedAt; }
        public void setRecordedAt(String recordedAt) { this.recordedAt = recordedAt; }

        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }

        public String getSyncStatus() { return syncStatus; }
        public void setSyncStatus(String syncStatus) { this.syncStatus = syncStatus; }

        public int getRetryCount() { return retryCount; }
        public void setRetryCount(int retryCount) { this.retryCount = retryCount; }

        public long getCreatedAt() { return createdAt; }
        public void setCreatedAt(long createdAt) { this.createdAt = createdAt; }
    }
}
