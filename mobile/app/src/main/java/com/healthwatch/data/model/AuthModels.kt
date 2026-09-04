package com.healthwatch.data.model

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val email: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Long,
    val role: String,
    val email: String,
    @SerializedName("full_name") val fullName: String
)

data class UserProfile(
    val id: String,
    val email: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("is_superuser") val isSuperuser: Boolean,
    val role: RoleInfo?
)

data class RoleInfo(
    val id: String,
    val name: String,
    val description: String?
)
