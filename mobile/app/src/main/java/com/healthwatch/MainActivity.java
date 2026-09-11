package com.healthwatch;

import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.AuthModels.UserResponse;
import com.healthwatch.ui.DashboardActivity;
import com.healthwatch.ui.LoginActivity;

/**
 * HealthWatch Mobile Main Entry Point.
 * Inspects authentication session, verifies token validity against backend,
 * clears stale sessions, and routes to Dashboard or Login.
 */
public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        SessionManager sessionManager = new SessionManager(this);
        HealthWatchApiClient apiClient = new HealthWatchApiClient(sessionManager);

        if (!sessionManager.isLoggedIn()) {
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }

        // Validate token against backend /api/auth/me
        apiClient.getMe(new HealthWatchApiClient.ApiCallback<UserResponse>() {
            @Override
            public void onSuccess(UserResponse user) {
                if (user != null && user.getEmail() != null && !user.getEmail().trim().isEmpty()) {
                    sessionManager.saveUser(
                            user.getEmail(),
                            user.getFullName(),
                            user.getRole(),
                            user.getPatientPseudoId(),
                            user.getPatientId()
                    );
                    startActivity(new Intent(MainActivity.this, DashboardActivity.class));
                } else {
                    sessionManager.clearSession();
                    startActivity(new Intent(MainActivity.this, LoginActivity.class));
                }
                finish();
            }

            @Override
            public void onError(Exception e) {
                String errorMsg = e != null && e.getMessage() != null ? e.getMessage() : "";
                if (errorMsg.contains("401") || errorMsg.contains("Authentication failed")) {
                    // Stale or expired token - clear session and require fresh login
                    sessionManager.clearSession();
                    startActivity(new Intent(MainActivity.this, LoginActivity.class));
                } else {
                    // Network unreachable or temporary timeout - allow dashboard with cached session
                    startActivity(new Intent(MainActivity.this, DashboardActivity.class));
                }
                finish();
            }
        });
    }
}
