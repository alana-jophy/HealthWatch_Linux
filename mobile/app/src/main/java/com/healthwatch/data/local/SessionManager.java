package com.healthwatch.data.local;

import android.content.Context;
import android.content.SharedPreferences;

public class SessionManager {

    private static final String PREF_NAME = "healthwatch_session";
    private static final String KEY_AUTH_TOKEN = "auth_token";
    private static final String KEY_USER_EMAIL = "user_email";
    private static final String KEY_USER_NAME = "user_name";
    private static final String KEY_USER_ROLE = "user_role";
    private static final String KEY_PATIENT_ID = "patient_id";
    private static final String KEY_PATIENT_PSEUDO_ID = "patient_pseudo_id";
    private static final String KEY_ACTIVE_SESSION_ID = "active_session_id";
    private static final String KEY_BASE_URL = "base_url";
    private static final String KEY_MUST_CHANGE_PASSWORD = "must_change_password";

    public static final String DEFAULT_BASE_URL = com.healthwatch.BuildConfig.DEFAULT_SERVER_URL;

    private final Context context;
    private final SharedPreferences prefs;

    public SessionManager(Context context) {
        this.context = context.getApplicationContext();
        this.prefs = this.context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public void saveAuthToken(String token) {
        prefs.edit().putString(KEY_AUTH_TOKEN, token).apply();
    }

    public String getAuthToken() {
        return prefs.getString(KEY_AUTH_TOKEN, null);
    }

    public void saveUser(String email, String fullName, String role, String patientPseudoId, String patientId) {
        saveUser(email, fullName, role, patientPseudoId, patientId, false);
    }

    public void saveUser(String email, String fullName, String role, String patientPseudoId, String patientId, boolean mustChangePassword) {
        if (email == null || email.trim().isEmpty()) {
            throw new IllegalArgumentException("User email cannot be null or empty.");
        }

        SharedPreferences.Editor editor = prefs.edit()
                .putString(KEY_USER_EMAIL, email.trim())
                .putString(KEY_USER_NAME, fullName != null ? fullName.trim() : "")
                .putString(KEY_USER_ROLE, role != null ? role.trim() : "")
                .putBoolean(KEY_MUST_CHANGE_PASSWORD, mustChangePassword);

        if (patientPseudoId != null && !patientPseudoId.trim().isEmpty()) {
            editor.putString(KEY_PATIENT_PSEUDO_ID, patientPseudoId.trim());
        } else {
            editor.remove(KEY_PATIENT_PSEUDO_ID);
        }

        if (patientId != null && !patientId.trim().isEmpty()) {
            editor.putString(KEY_PATIENT_ID, patientId.trim());
        } else {
            editor.remove(KEY_PATIENT_ID);
        }

        editor.apply();

        if ((patientPseudoId != null && !patientPseudoId.trim().isEmpty()) || (patientId != null && !patientId.trim().isEmpty())) {
            try {
                new OfflineLocationQueue(context).purgeOtherPatients(patientPseudoId, patientId);
            } catch (Exception ignored) {}
        }
    }

    public void saveMustChangePassword(boolean mustChange) {
        prefs.edit().putBoolean(KEY_MUST_CHANGE_PASSWORD, mustChange).apply();
    }

    public boolean mustChangePassword() {
        return prefs.getBoolean(KEY_MUST_CHANGE_PASSWORD, false);
    }

    public String getUserEmail() {
        return prefs.getString(KEY_USER_EMAIL, null);
    }

    public String getUserName() {
        return prefs.getString(KEY_USER_NAME, null);
    }

    public String getUserRole() {
        return prefs.getString(KEY_USER_ROLE, null);
    }

    public void savePatientInfo(String patientId, String pseudoId) {
        SharedPreferences.Editor editor = prefs.edit();
        if (patientId != null && !patientId.trim().isEmpty()) {
            editor.putString(KEY_PATIENT_ID, patientId.trim());
        }
        if (pseudoId != null && !pseudoId.trim().isEmpty()) {
            editor.putString(KEY_PATIENT_PSEUDO_ID, pseudoId.trim());
        }
        editor.apply();
    }

    public String getPatientId() {
        return prefs.getString(KEY_PATIENT_ID, null);
    }

    public String getPatientPseudoId() {
        return prefs.getString(KEY_PATIENT_PSEUDO_ID, null);
    }

    public void saveActiveSessionId(String sessionId) {
        if (sessionId != null && !sessionId.trim().isEmpty()) {
            prefs.edit().putString(KEY_ACTIVE_SESSION_ID, sessionId.trim()).apply();
        } else {
            prefs.edit().remove(KEY_ACTIVE_SESSION_ID).apply();
        }
    }

    public String getActiveSessionId() {
        return prefs.getString(KEY_ACTIVE_SESSION_ID, null);
    }

    public void saveBaseUrl(String url) {
        if (url != null && !url.trim().isEmpty()) {
            String cleanUrl = url.trim();
            if (!cleanUrl.startsWith("http://") && !cleanUrl.startsWith("https://")) {
                cleanUrl = "http://" + cleanUrl;
            }
            while (cleanUrl.endsWith("/")) {
                cleanUrl = cleanUrl.substring(0, cleanUrl.length() - 1);
            }
            prefs.edit().putString(KEY_BASE_URL, cleanUrl).apply();
        }
    }

    public String getBaseUrl() {
        return prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL);
    }

    public boolean isLoggedIn() {
        String token = getAuthToken();
        return token != null && !token.trim().isEmpty();
    }

    public void clearSession() {
        String currentBaseUrl = getBaseUrl();
        prefs.edit().clear().apply();
        saveBaseUrl(currentBaseUrl);
        try {
            new OfflineLocationQueue(context).clearAllObservations();
        } catch (Exception ignored) {}
    }
}
