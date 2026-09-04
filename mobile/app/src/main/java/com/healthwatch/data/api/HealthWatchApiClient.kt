package com.healthwatch.data.api

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.healthwatch.data.local.OfflineLocationQueue
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class HealthWatchApiClient(
    private val sessionManager: SessionManager
) {

    private val gson = Gson()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val requestBuilder = chain.request().newBuilder()
            sessionManager.getAuthToken()?.let { token ->
                requestBuilder.addHeader("Authorization", "Bearer $token")
            }
            chain.proceed(requestBuilder.build())
        }
        .build()

    private fun getBaseUrl(): String = sessionManager.getBaseUrl()

    suspend fun login(loginRequest: LoginRequest): Result<TokenResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(loginRequest)
            val request = Request.Builder()
                .url("${getBaseUrl()}/api/auth/login")
                .post(json.toRequestBody(jsonMediaType))
                .build()

            val response = client.newCall(request).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val tokenResponse = gson.fromJson(body, TokenResponse::class.java)
                sessionManager.saveAuthToken(tokenResponse.accessToken)
                sessionManager.saveUser(tokenResponse.email, tokenResponse.fullName, tokenResponse.role)
                Result.success(tokenResponse)
            } else {
                Result.failure(IOException("Authentication failed: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getMe(): Result<UserProfile> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("${getBaseUrl()}/api/auth/me")
                .get()
                .build()

            val response = client.newCall(request).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val profile = gson.fromJson(body, UserProfile::class.java)
                Result.success(profile)
            } else {
                Result.failure(IOException("Failed to get profile: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getMonitoringStatus(): Result<PatientMonitoringStatusResponse> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("${getBaseUrl()}/api/v1/monitoring/status")
                .get()
                .build()

            val response = client.newCall(request).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val status = gson.fromJson(body, PatientMonitoringStatusResponse::class.java)
                sessionManager.savePatientInfo(status.patientId, status.patientPseudoId)
                sessionManager.saveActiveSessionId(status.activeSession?.id)
                Result.success(status)
            } else {
                Result.failure(IOException("Status query failed: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun grantConsent(request: ConsentGrantRequest): Result<ConsentResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/monitoring/consent/grant")
                .post(json.toRequestBody(jsonMediaType))
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val consent = gson.fromJson(body, ConsentResponse::class.java)
                Result.success(consent)
            } else {
                Result.failure(IOException("Failed to grant consent: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun revokeConsent(request: ConsentRevokeRequest): Result<ConsentResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/monitoring/consent/revoke")
                .post(json.toRequestBody(jsonMediaType))
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val consent = gson.fromJson(body, ConsentResponse::class.java)
                sessionManager.saveActiveSessionId(null)
                Result.success(consent)
            } else {
                Result.failure(IOException("Failed to revoke consent: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun startMonitoringSession(request: SessionStartRequest): Result<MonitoringSessionResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/monitoring/sessions/start")
                .post(json.toRequestBody(jsonMediaType))
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val session = gson.fromJson(body, MonitoringSessionResponse::class.java)
                sessionManager.saveActiveSessionId(session.id)
                Result.success(session)
            } else {
                Result.failure(IOException("Failed to start session: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun stopMonitoringSession(request: SessionStopRequest): Result<MonitoringSessionResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/monitoring/sessions/stop")
                .post(json.toRequestBody(jsonMediaType))
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val session = gson.fromJson(body, MonitoringSessionResponse::class.java)
                sessionManager.saveActiveSessionId(null)
                Result.success(session)
            } else {
                Result.failure(IOException("Failed to stop session: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitLocationObservation(obs: LocationObservationSubmit): Result<LocationObservationResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(obs)
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/monitoring/locations/submit")
                .post(json.toRequestBody(jsonMediaType))
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val obsResponse = gson.fromJson(body, LocationObservationResponse::class.java)
                Result.success(obsResponse)
            } else {
                Result.failure(IOException("Location rejected: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getPatientProfile(): Result<PatientProfile> = withContext(Dispatchers.IO) {
        try {
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/patients/me")
                .get()
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val patient = gson.fromJson(body, PatientProfile::class.java)
                Result.success(patient)
            } else {
                // Fallback: search by patient pseudo ID if /me endpoint not dedicated
                val fallbackReq = Request.Builder()
                    .url("${getBaseUrl()}/api/v1/patients/?q=${sessionManager.getPatientPseudoId()}")
                    .get()
                    .build()
                val fallbackRes = client.newCall(fallbackReq).execute()
                val fallbackBody = fallbackRes.body?.string() ?: ""
                val type = object : TypeToken<PaginatedResponse<PatientProfile>>() {}.type
                val paginated: PaginatedResponse<PatientProfile> = gson.fromJson(fallbackBody, type)
                if (paginated.items.isNotEmpty()) {
                    Result.success(paginated.items[0])
                } else {
                    Result.failure(IOException("Patient profile not found"))
                }
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getDiseaseCases(): Result<List<DiseaseCase>> = withContext(Dispatchers.IO) {
        try {
            val req = Request.Builder()
                .url("${getBaseUrl()}/api/v1/cases/")
                .get()
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val type = object : TypeToken<PaginatedResponse<DiseaseCase>>() {}.type
                val paginated: PaginatedResponse<DiseaseCase> = gson.fromJson(body, type)
                Result.success(paginated.items)
            } else {
                Result.failure(IOException("Failed to query cases: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Flush and upload queued offline observations once network is available.
     * Returns Pair(syncedCount, failedCount).
     */
    suspend fun flushOfflineQueue(queue: OfflineLocationQueue): Pair<Int, Int> = withContext(Dispatchers.IO) {
        val pending = queue.getPendingObservations(50)
        var synced = 0
        var failed = 0

        for (item in pending) {
            val submitPayload = LocationObservationSubmit(
                patientId = item.patientId,
                monitoringSessionId = item.monitoringSessionId,
                latitude = item.latitude,
                longitude = item.longitude,
                accuracy = item.accuracy,
                recordedAt = item.recordedAt,
                source = item.source
            )

            val result = submitLocationObservation(submitPayload)
            if (result.isSuccess) {
                queue.markSynced(item.localId)
                synced++
            } else {
                queue.markFailed(item.localId)
                failed++
            }
        }
        Pair(synced, failed)
    }

    suspend fun getMovementRoadmap(date: String? = null): Result<MobileRoadmapResponse> = withContext(Dispatchers.IO) {
        try {
            val urlBuilder = StringBuilder("${getBaseUrl()}/api/v1/monitoring/roadmap")
            if (!date.isNullOrBlank()) {
                urlBuilder.append("?date=").append(date)
            }

            val req = Request.Builder()
                .url(urlBuilder.toString())
                .get()
                .build()

            val response = client.newCall(req).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val roadmap = gson.fromJson(body, MobileRoadmapResponse::class.java)
                Result.success(roadmap)
            } else {
                Result.failure(IOException("Failed to query roadmap: HTTP ${response.code} $body"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
