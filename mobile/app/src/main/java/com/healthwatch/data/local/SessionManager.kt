package com.healthwatch.data.local

import android.content.Context
import android.content.SharedPreferences

class SessionManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

    companion object {
        private const val PREF_NAME = "healthwatch_session"
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_USER_NAME = "user_name"
        private const val KEY_USER_ROLE = "user_role"
        private const val KEY_PATIENT_ID = "patient_id"
        private const val KEY_PATIENT_PSEUDO_ID = "patient_pseudo_id"
        private const val KEY_ACTIVE_SESSION_ID = "active_session_id"
        private const val KEY_BASE_URL = "base_url"
        
        // Default LAN server host for physical phone testing
        const val DEFAULT_BASE_URL = "http://192.168.0.109:8000"
    }

    fun saveAuthToken(token: String) {
        prefs.edit().putString(KEY_AUTH_TOKEN, token).apply()
    }

    fun getAuthToken(): String? {
        return prefs.getString(KEY_AUTH_TOKEN, null)
    }

    fun saveUser(email: String, fullName: String, role: String) {
        prefs.edit()
            .putString(KEY_USER_EMAIL, email)
            .putString(KEY_USER_NAME, fullName)
            .putString(KEY_USER_ROLE, role)
            .apply()
    }

    fun getUserEmail(): String? = prefs.getString(KEY_USER_EMAIL, null)
    fun getUserName(): String? = prefs.getString(KEY_USER_NAME, null)
    fun getUserRole(): String? = prefs.getString(KEY_USER_ROLE, null)

    fun savePatientInfo(patientId: String, pseudoId: String) {
        prefs.edit()
            .putString(KEY_PATIENT_ID, patientId)
            .putString(KEY_PATIENT_PSEUDO_ID, pseudoId)
            .apply()
    }

    fun getPatientId(): String? = prefs.getString(KEY_PATIENT_ID, null)
    fun getPatientPseudoId(): String? = prefs.getString(KEY_PATIENT_PSEUDO_ID, "PAT-SYNTH-101")

    fun saveActiveSessionId(sessionId: String?) {
        prefs.edit().putString(KEY_ACTIVE_SESSION_ID, sessionId).apply()
    }

    fun getActiveSessionId(): String? = prefs.getString(KEY_ACTIVE_SESSION_ID, null)

    fun saveBaseUrl(url: String) {
        prefs.edit().putString(KEY_BASE_URL, url).apply()
    }

    fun getBaseUrl(): String = prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL

    fun isLoggedIn(): Boolean = !getAuthToken().isNullOrBlank()

    fun clearSession() {
        prefs.edit().clear().apply()
    }
}
