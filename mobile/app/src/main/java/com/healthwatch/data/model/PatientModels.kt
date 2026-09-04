package com.healthwatch.data.model

import com.google.gson.annotations.SerializedName

data class PatientProfile(
    val id: String,
    @SerializedName("pseudo_id") val pseudoId: String,
    @SerializedName("user_id") val userId: String?,
    @SerializedName("full_name") val fullName: String,
    val age: Int,
    val gender: String,
    @SerializedName("contact_number") val contactNumber: String,
    val address: String,
    @SerializedName("district_name") val districtName: String,
    @SerializedName("local_body_name") val localBodyName: String,
    @SerializedName("ward_number") val wardNumber: Int,
    @SerializedName("is_active") val isActive: Boolean
)

data class DiseaseCase(
    val id: String,
    @SerializedName("patient_id") val patientId: String,
    @SerializedName("disease_id") val diseaseId: String,
    @SerializedName("case_status") val caseStatus: String, // SUSPECTED, CONFIRMED, RECOVERED, DECEASED
    val severity: String, // MILD, MODERATE, SEVERE, CRITICAL
    @SerializedName("diagnosis_date") val diagnosisDate: String,
    val latitude: Double?,
    val longitude: Double?,
    val source: String?,
    @SerializedName("clinical_notes") val clinicalNotes: String?,
    val disease: DiseaseInfo?
)

data class DiseaseInfo(
    val id: String,
    val code: String,
    val name: String,
    @SerializedName("contagion_type") val contagionType: String,
    val category: String,
    @SerializedName("incubation_period_days") val incubationPeriodDays: Int
)

data class PaginatedResponse<T>(
    val total: Int,
    val items: List<T>
)
