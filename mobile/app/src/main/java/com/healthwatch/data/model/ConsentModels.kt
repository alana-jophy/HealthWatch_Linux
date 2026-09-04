package com.healthwatch.data.model

import com.google.gson.annotations.SerializedName

data class ConsentResponse(
    val id: String,
    @SerializedName("patient_id") val patientId: String,
    @SerializedName("consent_status") val consentStatus: String,
    @SerializedName("consent_given_at") val consentGivenAt: String,
    @SerializedName("consent_version") val consentVersion: String,
    @SerializedName("monitoring_start") val monitoringStart: String,
    @SerializedName("monitoring_end") val monitoringEnd: String,
    @SerializedName("revoked_at") val revokedAt: String?,
    val purpose: String
)

data class ConsentGrantRequest(
    @SerializedName("patient_id") val patientId: String? = null,
    @SerializedName("consent_version") val consentVersion: String = "v1.0",
    @SerializedName("duration_days") val durationDays: Int = 14,
    @SerializedName("monitoring_start") val monitoringStart: String? = null,
    @SerializedName("monitoring_end") val monitoringEnd: String? = null,
    val purpose: String = "Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)"
)

data class ConsentRevokeRequest(
    @SerializedName("consent_id") val consentId: String? = null,
    val reason: String = "Patient opted out via mobile application"
)

data class MonitoringSessionResponse(
    val id: String,
    @SerializedName("patient_id") val patientId: String,
    @SerializedName("consent_id") val consentId: String?,
    @SerializedName("start_time") val startTime: String,
    @SerializedName("end_time") val endTime: String,
    val status: String,
    @SerializedName("stopped_at") val stoppedAt: String?,
    @SerializedName("sampling_interval_seconds") val samplingIntervalSeconds: Int = 900,
    @SerializedName("sampling_interval_description") val samplingIntervalDescription: String = "Approximately 15 minutes"
)

data class SessionStartRequest(
    @SerializedName("consent_id") val consentId: String? = null,
    @SerializedName("start_time") val startTime: String? = null,
    @SerializedName("end_time") val endTime: String? = null,
    @SerializedName("duration_hours") val durationHours: Int = 24
)

data class SessionStopRequest(
    @SerializedName("session_id") val sessionId: String? = null
)

data class PatientMonitoringStatusResponse(
    @SerializedName("patient_id") val patientId: String,
    @SerializedName("patient_pseudo_id") val patientPseudoId: String,
    @SerializedName("has_active_consent") val hasActiveConsent: Boolean,
    @SerializedName("active_consent") val activeConsent: ConsentResponse?,
    @SerializedName("has_active_session") val hasActiveSession: Boolean,
    @SerializedName("active_session") val activeSession: MonitoringSessionResponse?,
    @SerializedName("can_collect_location") val canCollectLocation: Boolean,
    @SerializedName("sampling_interval_minutes") val samplingIntervalMinutes: Int = 15,
    @SerializedName("sampling_interval_seconds") val samplingIntervalSeconds: Int = 900,
    @SerializedName("sampling_interval_description") val samplingIntervalDescription: String = "Approximately 15 minutes",
    @SerializedName("explanation_notice") val explanationNotice: String
)
