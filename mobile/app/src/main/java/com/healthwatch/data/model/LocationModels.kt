package com.healthwatch.data.model

import com.google.gson.annotations.SerializedName

/**
 * Android GPS Observation Record submitted to HealthWatch Backend.
 * Source tag is strictly PATIENT_GPS.
 */
data class LocationObservationSubmit(
    @SerializedName("patient_id") val patientId: String? = null,
    @SerializedName("monitoring_session_id") val monitoringSessionId: String,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float? = null,
    @SerializedName("recorded_at") val recordedAt: String? = null,
    val source: String = "PATIENT_GPS",
    @SerializedName("speed_mps") val speedMps: Float? = null,
    val altitude: Double? = null,
    @SerializedName("is_mock_provider") val isMockProvider: Boolean = false
)

data class LocationObservationResponse(
    val id: String,
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("patient_id") val patientId: String,
    @SerializedName("recorded_at") val recordedAt: String,
    val latitude: Double,
    val longitude: Double,
    @SerializedName("accuracy_meters") val accuracyMeters: Float?,
    val source: String,
    val status: String,
    val message: String
)

/**
 * Local offline queue entity stored on-device when network is unavailable.
 */
data class QueuedLocationObservation(
    val localId: Long = 0,
    val patientId: String,
    val monitoringSessionId: String,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float?,
    val recordedAt: String,
    val source: String = "PATIENT_GPS",
    val syncStatus: String = "PENDING", // PENDING, SYNCED, FAILED
    val retryCount: Int = 0,
    val createdAt: Long = System.currentTimeMillis()
)
