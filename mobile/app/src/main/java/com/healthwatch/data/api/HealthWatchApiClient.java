package com.healthwatch.data.api;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import com.healthwatch.data.local.OfflineLocationQueue;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.AuthModels.LoginRequest;
import com.healthwatch.data.model.AuthModels.TokenResponse;
import com.healthwatch.data.model.AuthModels.UserResponse;
import com.healthwatch.data.model.ConsentModels.ConsentGrantRequest;
import com.healthwatch.data.model.ConsentModels.ConsentResponse;
import com.healthwatch.data.model.ConsentModels.ConsentRevokeRequest;
import com.healthwatch.data.model.ConsentModels.MonitoringSessionResponse;
import com.healthwatch.data.model.ConsentModels.PatientMonitoringStatusResponse;
import com.healthwatch.data.model.ConsentModels.SessionStartRequest;
import com.healthwatch.data.model.ConsentModels.SessionStopRequest;
import com.healthwatch.data.model.LocationModels.BatchLocationSyncRequest;
import com.healthwatch.data.model.LocationModels.BatchLocationSyncResponse;
import com.healthwatch.data.model.LocationModels.LocationObservationResponse;
import com.healthwatch.data.model.LocationModels.LocationObservationSubmit;
import com.healthwatch.data.model.LocationModels.QueuedLocationObservation;
import com.healthwatch.data.model.PatientModels.DiseaseCase;
import com.healthwatch.data.model.PatientModels.PaginatedResponse;
import com.healthwatch.data.model.PatientModels.PatientProfile;
import com.healthwatch.data.model.RoadmapModels.MobileRoadmapResponse;
import java.io.IOException;
import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class HealthWatchApiClient {

    private static final String TAG = "HealthWatchApiClient";
    private static final MediaType JSON_MEDIA_TYPE = MediaType.parse("application/json; charset=utf-8");

    public interface ApiCallback<T> {
        void onSuccess(T result);
        void onError(Exception e);
    }

    private final SessionManager sessionManager;
    private final Gson gson;
    private final OkHttpClient client;
    private final ExecutorService executor;
    private final Handler mainHandler;

    public HealthWatchApiClient(SessionManager sessionManager) {
        this.sessionManager = sessionManager;
        this.gson = new Gson();
        this.executor = Executors.newCachedThreadPool();
        this.mainHandler = new Handler(Looper.getMainLooper());

        this.client = new OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .writeTimeout(15, TimeUnit.SECONDS)
                .addInterceptor(chain -> {
                    Request.Builder requestBuilder = chain.request().newBuilder();
                    String token = sessionManager.getAuthToken();
                    if (token != null && !token.trim().isEmpty()) {
                        requestBuilder.addHeader("Authorization", "Bearer " + token);
                    }
                    return chain.proceed(requestBuilder.build());
                })
                .build();
    }

    private String getBaseUrl() {
        return sessionManager.getBaseUrl();
    }

    private <T> void postSuccess(ApiCallback<T> callback, T result) {
        if (callback != null) {
            mainHandler.post(() -> callback.onSuccess(result));
        }
    }

    private <T> void postError(ApiCallback<T> callback, Exception e) {
        if (callback != null) {
            mainHandler.post(() -> callback.onError(e));
        }
    }

    /**
     * Authenticate user with credentials and store token and profile.
     */
    public void login(LoginRequest loginRequest, ApiCallback<TokenResponse> callback) {
        executor.execute(() -> {
            try {
                Log.d(TAG, "LOGIN_REQUEST_STARTED");
                String json = gson.toJson(loginRequest);
                RequestBody body = RequestBody.create(json, JSON_MEDIA_TYPE);
                Request request = new Request.Builder()
                        .url(getBaseUrl() + "/api/auth/login")
                        .post(body)
                        .build();

                Response response = client.newCall(request).execute();
                int code = response.code();
                Log.d(TAG, "LOGIN_RESPONSE_CODE: " + code);
                String respBody = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    TokenResponse tokenResponse = gson.fromJson(respBody, TokenResponse.class);
                    Log.d(TAG, "LOGIN_RESPONSE_PARSED");

                    if (tokenResponse == null || tokenResponse.getAccessToken() == null || tokenResponse.getAccessToken().trim().isEmpty()) {
                        throw new IOException("Authentication response missing valid access token.");
                    }

                    UserResponse user = tokenResponse.getUser();
                    if (user == null || user.getEmail() == null || user.getEmail().trim().isEmpty()) {
                        throw new IOException("Login succeeded, but the server returned an incomplete user profile (missing email).");
                    }

                    Log.d(TAG, "AUTH_USER_PARSED: role=" + user.getRole() + ", has_patient_id=" + (user.getPatientId() != null));

                    sessionManager.saveAuthToken(tokenResponse.getAccessToken());
                    sessionManager.saveUser(
                            user.getEmail(),
                            user.getFullName(),
                            user.getRole(),
                            user.getPatientPseudoId(),
                            user.getPatientId()
                    );

                    Log.d(TAG, "LOGIN_SUCCESS");
                    postSuccess(callback, tokenResponse);
                } else {
                    postError(callback, new IOException("Authentication failed: HTTP " + code + " " + respBody));
                }
            } catch (Exception e) {
                Log.e(TAG, "Login exception: " + e.getMessage());
                postError(callback, e);
            }
        });
    }

    /**
     * Verify active session and fetch current authenticated user profile.
     */
    public void getMe(ApiCallback<UserResponse> callback) {
        executor.execute(() -> {
            try {
                Request request = new Request.Builder()
                        .url(getBaseUrl() + "/api/auth/me")
                        .get()
                        .build();

                Response response = client.newCall(request).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    UserResponse user = gson.fromJson(body, UserResponse.class);
                    if (user == null || user.getEmail() == null || user.getEmail().trim().isEmpty()) {
                        throw new IOException("Profile verification failed: server returned incomplete user record.");
                    }
                    postSuccess(callback, user);
                } else {
                    postError(callback, new IOException("Failed to get profile: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    /**
     * Get patient monitoring status and active session metadata.
     */
    public void getMonitoringStatus(ApiCallback<PatientMonitoringStatusResponse> callback) {
        executor.execute(() -> {
            try {
                Request request = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/monitoring/status")
                        .get()
                        .build();

                Response response = client.newCall(request).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    PatientMonitoringStatusResponse status = gson.fromJson(body, PatientMonitoringStatusResponse.class);
                    if (status != null) {
                        sessionManager.savePatientInfo(status.getPatientId(), status.getPatientPseudoId());
                        if (status.getActiveSession() != null) {
                            sessionManager.saveActiveSessionId(status.getActiveSession().getId());
                        } else {
                            sessionManager.saveActiveSessionId(null);
                        }
                    }
                    postSuccess(callback, status);
                } else {
                    postError(callback, new IOException("Status query failed: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    /**
     * Synchronous status retrieval (for Background Service use).
     */
    public PatientMonitoringStatusResponse getMonitoringStatusSync() throws IOException {
        Request request = new Request.Builder()
                .url(getBaseUrl() + "/api/v1/monitoring/status")
                .get()
                .build();

        Response response = client.newCall(request).execute();
        String body = response.body() != null ? response.body().string() : "";
        if (response.isSuccessful()) {
            return gson.fromJson(body, PatientMonitoringStatusResponse.class);
        } else {
            throw new IOException("Status query failed: HTTP " + response.code() + " " + body);
        }
    }

    public void grantConsent(ConsentGrantRequest request, ApiCallback<ConsentResponse> callback) {
        executor.execute(() -> {
            try {
                String json = gson.toJson(request);
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/monitoring/consent/grant")
                        .post(RequestBody.create(json, JSON_MEDIA_TYPE))
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    ConsentResponse consent = gson.fromJson(body, ConsentResponse.class);
                    postSuccess(callback, consent);
                } else {
                    postError(callback, new IOException("Failed to grant consent: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public void revokeConsent(ConsentRevokeRequest request, ApiCallback<ConsentResponse> callback) {
        executor.execute(() -> {
            try {
                String json = gson.toJson(request);
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/monitoring/consent/revoke")
                        .post(RequestBody.create(json, JSON_MEDIA_TYPE))
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    ConsentResponse consent = gson.fromJson(body, ConsentResponse.class);
                    sessionManager.saveActiveSessionId(null);
                    postSuccess(callback, consent);
                } else {
                    postError(callback, new IOException("Failed to revoke consent: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public void startMonitoringSession(SessionStartRequest request, ApiCallback<MonitoringSessionResponse> callback) {
        executor.execute(() -> {
            try {
                String json = gson.toJson(request);
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/monitoring/sessions/start")
                        .post(RequestBody.create(json, JSON_MEDIA_TYPE))
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    MonitoringSessionResponse session = gson.fromJson(body, MonitoringSessionResponse.class);
                    if (session != null) {
                        sessionManager.saveActiveSessionId(session.getId());
                    }
                    postSuccess(callback, session);
                } else {
                    postError(callback, new IOException("Failed to start session: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public void stopMonitoringSession(SessionStopRequest request, ApiCallback<MonitoringSessionResponse> callback) {
        executor.execute(() -> {
            try {
                String json = gson.toJson(request);
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/monitoring/sessions/stop")
                        .post(RequestBody.create(json, JSON_MEDIA_TYPE))
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    MonitoringSessionResponse session = gson.fromJson(body, MonitoringSessionResponse.class);
                    sessionManager.saveActiveSessionId(null);
                    postSuccess(callback, session);
                } else {
                    postError(callback, new IOException("Failed to stop session: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public void submitLocationObservation(LocationObservationSubmit obs, ApiCallback<LocationObservationResponse> callback) {
        executor.execute(() -> {
            try {
                LocationObservationResponse resp = submitLocationObservationSync(obs);
                postSuccess(callback, resp);
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    /**
     * Synchronous submission (for Foreground Service use).
     */
    public LocationObservationResponse submitLocationObservationSync(LocationObservationSubmit obs) throws IOException {
        String json = gson.toJson(obs);
        Request req = new Request.Builder()
                .url(getBaseUrl() + "/api/v1/monitoring/locations/submit")
                .post(RequestBody.create(json, JSON_MEDIA_TYPE))
                .build();

        Response response = client.newCall(req).execute();
        String body = response.body() != null ? response.body().string() : "";

        if (response.isSuccessful()) {
            return gson.fromJson(body, LocationObservationResponse.class);
        } else {
            throw new IOException("Location rejected: HTTP " + response.code() + " " + body);
        }
    }

    public void getPatientProfile(ApiCallback<PatientProfile> callback) {
        executor.execute(() -> {
            try {
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/patients/me")
                        .get()
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    PatientProfile patient = gson.fromJson(body, PatientProfile.class);
                    postSuccess(callback, patient);
                } else {
                    // Fallback to searching by pseudo ID
                    String pseudoId = sessionManager.getPatientPseudoId();
                    Request fallbackReq = new Request.Builder()
                            .url(getBaseUrl() + "/api/v1/patients/?q=" + (pseudoId != null ? pseudoId : ""))
                            .get()
                            .build();
                    Response fallbackRes = client.newCall(fallbackReq).execute();
                    String fallbackBody = fallbackRes.body() != null ? fallbackRes.body().string() : "";

                    Type type = new TypeToken<PaginatedResponse<PatientProfile>>() {}.getType();
                    PaginatedResponse<PatientProfile> paginated = gson.fromJson(fallbackBody, type);

                    if (paginated != null && !paginated.getItems().isEmpty()) {
                        postSuccess(callback, paginated.getItems().get(0));
                    } else {
                        postError(callback, new IOException("Patient profile not found."));
                    }
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public void getDiseaseCases(ApiCallback<List<DiseaseCase>> callback) {
        executor.execute(() -> {
            try {
                Request req = new Request.Builder()
                        .url(getBaseUrl() + "/api/v1/cases/")
                        .get()
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    Type type = new TypeToken<PaginatedResponse<DiseaseCase>>() {}.getType();
                    PaginatedResponse<DiseaseCase> paginated = gson.fromJson(body, type);
                    List<DiseaseCase> items = paginated != null ? paginated.getItems() : new ArrayList<>();
                    postSuccess(callback, items);
                } else {
                    postError(callback, new IOException("Failed to query cases: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public BatchLocationSyncResponse batchSyncLocationsSync(BatchLocationSyncRequest request) throws IOException {
        String json = gson.toJson(request);
        Request req = new Request.Builder()
                .url(getBaseUrl() + "/api/v1/monitoring/locations/sync")
                .post(RequestBody.create(json, JSON_MEDIA_TYPE))
                .build();

        Response response = client.newCall(req).execute();
        String body = response.body() != null ? response.body().string() : "";

        if (response.isSuccessful()) {
            return gson.fromJson(body, BatchLocationSyncResponse.class);
        } else {
            throw new IOException("Batch location sync rejected: HTTP " + response.code() + " " + body);
        }
    }

    /**
     * Flush and upload queued offline observations once network is available.
     * Returns int[]{syncedCount, failedCount}.
     */
    public int[] flushOfflineQueueSync(OfflineLocationQueue queue) {
        List<QueuedLocationObservation> pending = queue.getPendingObservations(100);
        if (pending.isEmpty()) {
            return new int[]{0, 0};
        }

        List<LocationObservationSubmit> batchPayload = new ArrayList<>();
        for (QueuedLocationObservation item : pending) {
            batchPayload.add(new LocationObservationSubmit(
                    item.getPatientId(),
                    item.getMonitoringSessionId(),
                    item.getLatitude(),
                    item.getLongitude(),
                    item.getAccuracy(),
                    item.getRecordedAt(),
                    item.getSource()
            ));
        }

        String sessionId = pending.get(0).getMonitoringSessionId();
        try {
            BatchLocationSyncResponse batchResult = batchSyncLocationsSync(new BatchLocationSyncRequest(sessionId, batchPayload));
            if (batchResult != null && "COMPLETED".equalsIgnoreCase(batchResult.getStatus())) {
                for (QueuedLocationObservation item : pending) {
                    queue.markSynced(item.getLocalId());
                }
                return new int[]{pending.size(), 0};
            }
        } catch (Exception e) {
            Log.w(TAG, "Batch sync failed, falling back to individual submit: " + e.getMessage());
        }

        int synced = 0;
        int failed = 0;
        for (QueuedLocationObservation item : pending) {
            LocationObservationSubmit submitPayload = new LocationObservationSubmit(
                    item.getPatientId(),
                    item.getMonitoringSessionId(),
                    item.getLatitude(),
                    item.getLongitude(),
                    item.getAccuracy(),
                    item.getRecordedAt(),
                    item.getSource()
            );
            try {
                submitLocationObservationSync(submitPayload);
                queue.markSynced(item.getLocalId());
                synced++;
            } catch (Exception ex) {
                queue.markFailed(item.getLocalId());
                failed++;
            }
        }
        return new int[]{synced, failed};
    }

    public void flushOfflineQueue(OfflineLocationQueue queue, ApiCallback<int[]> callback) {
        executor.execute(() -> {
            try {
                int[] counts = flushOfflineQueueSync(queue);
                postSuccess(callback, counts);
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }

    public void getMovementRoadmap(String date, ApiCallback<MobileRoadmapResponse> callback) {
        executor.execute(() -> {
            try {
                StringBuilder urlBuilder = new StringBuilder(getBaseUrl()).append("/api/v1/monitoring/roadmap");
                if (date != null && !date.trim().isEmpty()) {
                    urlBuilder.append("?date=").append(date.trim());
                }

                Request req = new Request.Builder()
                        .url(urlBuilder.toString())
                        .get()
                        .build();

                Response response = client.newCall(req).execute();
                String body = response.body() != null ? response.body().string() : "";

                if (response.isSuccessful()) {
                    MobileRoadmapResponse roadmap = gson.fromJson(body, MobileRoadmapResponse.class);
                    postSuccess(callback, roadmap);
                } else {
                    postError(callback, new IOException("Failed to query roadmap: HTTP " + response.code() + " " + body));
                }
            } catch (Exception e) {
                postError(callback, e);
            }
        });
    }
}
