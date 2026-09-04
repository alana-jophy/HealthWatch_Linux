package com.healthwatch.data.model

import com.google.gson.annotations.SerializedName

data class MobileRoadmapResponse(
    @SerializedName("patient_id") val patientId: String,
    @SerializedName("patient_pseudo_id") val patientPseudoId: String,
    @SerializedName("patient_name") val patientName: String?,
    @SerializedName("session_id") val sessionId: String?,
    @SerializedName("filter_date") val filterDate: String?,
    val disclaimer: String,
    val statistics: MobileRoadmapStatistics,
    val observations: List<MobileRoadmapObservation>
)

data class MobileRoadmapStatistics(
    @SerializedName("total_observations") val totalObservations: Int,
    @SerializedName("monitoring_start") val monitoringStart: String?,
    @SerializedName("monitoring_end") val monitoringEnd: String?,
    @SerializedName("first_recorded_location") val firstRecordedLocation: MobilePoint?,
    @SerializedName("last_recorded_location") val lastRecordedLocation: MobilePoint?,
    @SerializedName("average_accuracy") val averageAccuracy: Float?
)

data class MobilePoint(
    val latitude: Double,
    val longitude: Double
)

data class MobileRoadmapObservation(
    val id: String,
    @SerializedName("recorded_at") val recordedAt: String,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float?,
    val source: String,
    @SerializedName("session_id") val sessionId: String?
)
