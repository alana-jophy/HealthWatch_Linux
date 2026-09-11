package com.healthwatch.data.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class ConsentModels {

    public static class ConsentResponse {
        @SerializedName("id")
        private String id;

        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("consent_status")
        private String consentStatus;

        @SerializedName("consent_given_at")
        private String consentGivenAt;

        @SerializedName("consent_version")
        private String consentVersion;

        @SerializedName("monitoring_start")
        private String monitoringStart;

        @SerializedName("monitoring_end")
        private String monitoringEnd;

        @SerializedName("revoked_at")
        private String revokedAt;

        @SerializedName("purpose")
        private String purpose;

        public ConsentResponse() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getConsentStatus() { return consentStatus; }
        public void setConsentStatus(String consentStatus) { this.consentStatus = consentStatus; }

        public String getConsentGivenAt() { return consentGivenAt; }
        public void setConsentGivenAt(String consentGivenAt) { this.consentGivenAt = consentGivenAt; }

        public String getConsentVersion() { return consentVersion; }
        public void setConsentVersion(String consentVersion) { this.consentVersion = consentVersion; }

        public String getMonitoringStart() { return monitoringStart; }
        public void setMonitoringStart(String monitoringStart) { this.monitoringStart = monitoringStart; }

        public String getMonitoringEnd() { return monitoringEnd; }
        public void setMonitoringEnd(String monitoringEnd) { this.monitoringEnd = monitoringEnd; }

        public String getRevokedAt() { return revokedAt; }
        public void setRevokedAt(String revokedAt) { this.revokedAt = revokedAt; }

        public String getPurpose() { return purpose; }
        public void setPurpose(String purpose) { this.purpose = purpose; }
    }

    public static class ConsentGrantRequest {
        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("consent_version")
        private String consentVersion = "v1.0";

        @SerializedName("duration_days")
        private int durationDays = 14;

        @SerializedName("monitoring_start")
        private String monitoringStart;

        @SerializedName("monitoring_end")
        private String monitoringEnd;

        @SerializedName("purpose")
        private String purpose = "Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)";

        public ConsentGrantRequest() {}

        public ConsentGrantRequest(int durationDays) {
            this.durationDays = durationDays;
        }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getConsentVersion() { return consentVersion; }
        public void setConsentVersion(String consentVersion) { this.consentVersion = consentVersion; }

        public int getDurationDays() { return durationDays; }
        public void setDurationDays(int durationDays) { this.durationDays = durationDays; }

        public String getMonitoringStart() { return monitoringStart; }
        public void setMonitoringStart(String monitoringStart) { this.monitoringStart = monitoringStart; }

        public String getMonitoringEnd() { return monitoringEnd; }
        public void setMonitoringEnd(String monitoringEnd) { this.monitoringEnd = monitoringEnd; }

        public String getPurpose() { return purpose; }
        public void setPurpose(String purpose) { this.purpose = purpose; }
    }

    public static class ConsentRevokeRequest {
        @SerializedName("consent_id")
        private String consentId;

        @SerializedName("reason")
        private String reason = "Patient opted out via mobile application";

        public ConsentRevokeRequest() {}

        public ConsentRevokeRequest(String consentId, String reason) {
            this.consentId = consentId;
            if (reason != null) this.reason = reason;
        }

        public String getConsentId() { return consentId; }
        public void setConsentId(String consentId) { this.consentId = consentId; }

        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
    }

    public static class MonitoringSessionResponse {
        @SerializedName("id")
        private String id;

        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("consent_id")
        private String consentId;

        @SerializedName("start_time")
        private String startTime;

        @SerializedName("end_time")
        private String endTime;

        @SerializedName("status")
        private String status;

        @SerializedName("stopped_at")
        private String stoppedAt;

        @SerializedName("sampling_interval_seconds")
        private int samplingIntervalSeconds = 900;

        @SerializedName("sampling_interval_description")
        private String samplingIntervalDescription = "Approximately 15 minutes";

        public MonitoringSessionResponse() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getConsentId() { return consentId; }
        public void setConsentId(String consentId) { this.consentId = consentId; }

        public String getStartTime() { return startTime; }
        public void setStartTime(String startTime) { this.startTime = startTime; }

        public String getEndTime() { return endTime; }
        public void setEndTime(String endTime) { this.endTime = endTime; }

        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }

        public String getStoppedAt() { return stoppedAt; }
        public void setStoppedAt(String stoppedAt) { this.stoppedAt = stoppedAt; }

        public int getSamplingIntervalSeconds() { return samplingIntervalSeconds; }
        public void setSamplingIntervalSeconds(int samplingIntervalSeconds) { this.samplingIntervalSeconds = samplingIntervalSeconds; }

        public String getSamplingIntervalDescription() { return samplingIntervalDescription; }
        public void setSamplingIntervalDescription(String samplingIntervalDescription) { this.samplingIntervalDescription = samplingIntervalDescription; }
    }

    public static class SessionStartRequest {
        @SerializedName("consent_id")
        private String consentId;

        @SerializedName("start_time")
        private String startTime;

        @SerializedName("end_time")
        private String endTime;

        @SerializedName("duration_hours")
        private int durationHours = 24;

        public SessionStartRequest() {}

        public SessionStartRequest(int durationHours) {
            this.durationHours = durationHours;
        }

        public String getConsentId() { return consentId; }
        public void setConsentId(String consentId) { this.consentId = consentId; }

        public String getStartTime() { return startTime; }
        public void setStartTime(String startTime) { this.startTime = startTime; }

        public String getEndTime() { return endTime; }
        public void setEndTime(String endTime) { this.endTime = endTime; }

        public int getDurationHours() { return durationHours; }
        public void setDurationHours(int durationHours) { this.durationHours = durationHours; }
    }

    public static class SessionStopRequest {
        @SerializedName("session_id")
        private String sessionId;

        public SessionStopRequest() {}

        public SessionStopRequest(String sessionId) {
            this.sessionId = sessionId;
        }

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    }

    public static class PatientMonitoringStatusResponse {
        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("patient_pseudo_id")
        private String patientPseudoId;

        @SerializedName("has_active_consent")
        private boolean hasActiveConsent;

        @SerializedName("active_consent")
        private ConsentResponse activeConsent;

        @SerializedName("has_active_session")
        private boolean hasActiveSession;

        @SerializedName("active_session")
        private MonitoringSessionResponse activeSession;

        @SerializedName("can_collect_location")
        private boolean canCollectLocation;

        @SerializedName("sampling_interval_minutes")
        private int samplingIntervalMinutes = 15;

        @SerializedName("sampling_interval_seconds")
        private int samplingIntervalSeconds = 900;

        @SerializedName("sampling_interval_description")
        private String samplingIntervalDescription = "Approximately 15 minutes";

        @SerializedName("tracking_days")
        private List<String> trackingDays;

        @SerializedName("is_tracking_day_today")
        private boolean isTrackingDayToday = true;

        @SerializedName("has_phone")
        private boolean hasPhone = true;

        @SerializedName("explanation_notice")
        private String explanationNotice;

        public PatientMonitoringStatusResponse() {}

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getPatientPseudoId() { return patientPseudoId; }
        public void setPatientPseudoId(String patientPseudoId) { this.patientPseudoId = patientPseudoId; }

        public boolean isHasActiveConsent() { return hasActiveConsent; }
        public void setHasActiveConsent(boolean hasActiveConsent) { this.hasActiveConsent = hasActiveConsent; }

        public ConsentResponse getActiveConsent() { return activeConsent; }
        public void setActiveConsent(ConsentResponse activeConsent) { this.activeConsent = activeConsent; }

        public boolean isHasActiveSession() { return hasActiveSession; }
        public void setHasActiveSession(boolean hasActiveSession) { this.hasActiveSession = hasActiveSession; }

        public MonitoringSessionResponse getActiveSession() { return activeSession; }
        public void setActiveSession(MonitoringSessionResponse activeSession) { this.activeSession = activeSession; }

        public boolean isCanCollectLocation() { return canCollectLocation; }
        public void setCanCollectLocation(boolean canCollectLocation) { this.canCollectLocation = canCollectLocation; }

        public int getSamplingIntervalMinutes() { return samplingIntervalMinutes; }
        public void setSamplingIntervalMinutes(int samplingIntervalMinutes) { this.samplingIntervalMinutes = samplingIntervalMinutes; }

        public int getSamplingIntervalSeconds() { return samplingIntervalSeconds; }
        public void setSamplingIntervalSeconds(int samplingIntervalSeconds) { this.samplingIntervalSeconds = samplingIntervalSeconds; }

        public String getSamplingIntervalDescription() { return samplingIntervalDescription; }
        public void setSamplingIntervalDescription(String samplingIntervalDescription) { this.samplingIntervalDescription = samplingIntervalDescription; }

        public List<String> getTrackingDays() { return trackingDays; }
        public void setTrackingDays(List<String> trackingDays) { this.trackingDays = trackingDays; }

        public boolean isTrackingDayToday() { return isTrackingDayToday; }
        public void setTrackingDayToday(boolean trackingDayToday) { isTrackingDayToday = trackingDayToday; }

        public boolean isHasPhone() { return hasPhone; }
        public void setHasPhone(boolean hasPhone) { this.hasPhone = hasPhone; }

        public String getExplanationNotice() { return explanationNotice; }
        public void setExplanationNotice(String explanationNotice) { this.explanationNotice = explanationNotice; }
    }
}
