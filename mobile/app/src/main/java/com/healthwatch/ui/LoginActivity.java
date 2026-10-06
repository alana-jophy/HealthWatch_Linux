package com.healthwatch.ui;

import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import com.healthwatch.data.api.HealthWatchApiClient;
import com.healthwatch.data.local.SessionManager;
import com.healthwatch.data.model.AuthModels.LoginRequest;
import com.healthwatch.data.model.AuthModels.TokenResponse;
import com.healthwatch.data.model.AuthModels.UserResponse;

public class LoginActivity extends AppCompatActivity {

    private static final String TAG = "HealthWatchLogin";

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;

    private EditText emailInput;
    private EditText passwordInput;
    private Button loginButton;
    private ProgressBar progressBar;
    private TextView errorTextView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        // If already authenticated, directly navigate to Dashboard or ResetPassword
        if (sessionManager.isLoggedIn()) {
            if (sessionManager.mustChangePassword()) {
                startActivity(new Intent(this, ResetPasswordActivity.class));
            } else {
                startActivity(new Intent(this, DashboardActivity.class));
            }
            finish();
            return;
        }

        buildUi();
    }

    private void buildUi() {
        ScrollView root = new ScrollView(this);
        root.setBackgroundColor(Color.parseColor("#0F172A")); // Slate 900
        root.setFillViewport(true);

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setGravity(Gravity.CENTER_HORIZONTAL);
        container.setPadding(48, 80, 48, 80);

        // App Logo & Title
        TextView titleText = new TextView(this);
        titleText.setText("HealthWatch");
        titleText.setTextSize(30f);
        titleText.setTextColor(Color.WHITE);
        titleText.setTypeface(Typeface.DEFAULT_BOLD);
        titleText.setGravity(Gravity.CENTER);

        TextView subtitleText = new TextView(this);
        subtitleText.setText("Disease Surveillance & Patient Portal");
        subtitleText.setTextSize(14f);
        subtitleText.setTextColor(Color.parseColor("#94A3B8")); // Slate 400
        subtitleText.setGravity(Gravity.CENTER);
        subtitleText.setPadding(0, 8, 0, 48);

        container.addView(titleText);
        container.addView(subtitleText);

        // Email / Patient ID / Phone input
        TextView emailLabel = new TextView(this);
        emailLabel.setText("Registered Email, Patient ID, or Phone:");
        emailLabel.setTextSize(13f);
        emailLabel.setTextColor(Color.parseColor("#CBD5E1"));
        emailLabel.setPadding(0, 0, 0, 8);

        emailInput = new EditText(this);
        emailInput.setHint("e.g. PAT-..., email, or 10-digit phone");
        emailInput.setTextColor(Color.WHITE);
        emailInput.setHintTextColor(Color.parseColor("#64748B"));
        emailInput.setBackgroundColor(Color.parseColor("#1E293B"));
        emailInput.setPadding(28, 28, 28, 28);
        emailInput.setTextSize(15f);

        container.addView(emailLabel);
        container.addView(emailInput);

        // Spacer
        View spacer1 = new View(this);
        spacer1.setLayoutParams(new LinearLayout.LayoutParams(1, 32));
        container.addView(spacer1);

        // Password input with Eye Toggle Button
        TextView passwordLabel = new TextView(this);
        passwordLabel.setText("Password:");
        passwordLabel.setTextSize(13f);
        passwordLabel.setTextColor(Color.parseColor("#CBD5E1"));
        passwordLabel.setPadding(0, 0, 0, 8);

        LinearLayout passwordContainer = new LinearLayout(this);
        passwordContainer.setOrientation(LinearLayout.HORIZONTAL);
        passwordContainer.setBackgroundColor(Color.parseColor("#1E293B"));
        passwordContainer.setGravity(Gravity.CENTER_VERTICAL);
        passwordContainer.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        passwordInput = new EditText(this);
        passwordInput.setHint("Enter account password");
        passwordInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        passwordInput.setTextColor(Color.WHITE);
        passwordInput.setHintTextColor(Color.parseColor("#64748B"));
        passwordInput.setBackgroundColor(Color.TRANSPARENT);
        passwordInput.setPadding(28, 28, 12, 28);
        passwordInput.setTextSize(15f);
        LinearLayout.LayoutParams passParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
        passwordInput.setLayoutParams(passParams);

        TextView eyeToggleButton = new TextView(this);
        eyeToggleButton.setText("👁");
        eyeToggleButton.setTextSize(18f);
        eyeToggleButton.setPadding(20, 20, 28, 20);
        eyeToggleButton.setTextColor(Color.parseColor("#94A3B8"));
        eyeToggleButton.setGravity(Gravity.CENTER);
        eyeToggleButton.setContentDescription("Show or hide password");

        final boolean[] isPasswordVisible = {false};
        eyeToggleButton.setOnClickListener(v -> {
            if (isPasswordVisible[0]) {
                passwordInput.setTransformationMethod(android.text.method.PasswordTransformationMethod.getInstance());
                eyeToggleButton.setText("👁");
                eyeToggleButton.setTextColor(Color.parseColor("#94A3B8"));
                isPasswordVisible[0] = false;
            } else {
                passwordInput.setTransformationMethod(android.text.method.HideReturnsTransformationMethod.getInstance());
                eyeToggleButton.setText("👁‍🗨");
                eyeToggleButton.setTextColor(Color.parseColor("#38BDF8"));
                isPasswordVisible[0] = true;
            }
            if (passwordInput.getText() != null) {
                passwordInput.setSelection(passwordInput.getText().length());
            }
        });

        passwordContainer.addView(passwordInput);
        passwordContainer.addView(eyeToggleButton);

        container.addView(passwordLabel);
        container.addView(passwordContainer);

        // Error message text
        errorTextView = new TextView(this);
        errorTextView.setTextSize(13f);
        errorTextView.setTextColor(Color.parseColor("#F43F5E")); // Rose 500
        errorTextView.setVisibility(View.GONE);
        errorTextView.setPadding(0, 20, 0, 8);
        container.addView(errorTextView);

        // Progress Bar
        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.GONE);
        progressBar.setPadding(0, 20, 0, 20);
        container.addView(progressBar);

        // Spacer
        View spacer2 = new View(this);
        spacer2.setLayoutParams(new LinearLayout.LayoutParams(1, 32));
        container.addView(spacer2);

        // Login Button
        loginButton = new Button(this);
        loginButton.setText("SIGN IN");
        loginButton.setTextColor(Color.WHITE);
        loginButton.setBackgroundColor(Color.parseColor("#0284C7")); // Brand Cyan 600
        loginButton.setTypeface(Typeface.DEFAULT_BOLD);
        loginButton.setTextSize(16f);
        loginButton.setPadding(0, 28, 0, 28);
        loginButton.setOnClickListener(v -> attemptLogin());
        container.addView(loginButton);

        // Server Domain / URL Configuration Button
        TextView serverConfigText = new TextView(this);
        serverConfigText.setText("⚙️ Server Domain: " + sessionManager.getBaseUrl());
        serverConfigText.setTextSize(12f);
        serverConfigText.setTextColor(Color.parseColor("#38BDF8"));
        serverConfigText.setGravity(Gravity.CENTER);
        serverConfigText.setPadding(0, 36, 0, 16);
        serverConfigText.setOnClickListener(v -> showServerConfigDialog(serverConfigText));
        container.addView(serverConfigText);

        root.addView(container);
        setContentView(root);
    }

    private void showServerConfigDialog(TextView serverConfigText) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Server Domain & API URL");

        LinearLayout dialogLayout = new LinearLayout(this);
        dialogLayout.setOrientation(LinearLayout.VERTICAL);
        dialogLayout.setPadding(50, 24, 50, 12);

        TextView infoText = new TextView(this);
        infoText.setText("Enter the backend server domain or IP address to sync data (e.g., http://192.168.0.119:8000 or https://healthwatch.example.com):");
        infoText.setTextSize(13f);
        infoText.setTextColor(Color.parseColor("#475569"));
        infoText.setPadding(0, 0, 0, 16);
        dialogLayout.addView(infoText);

        EditText input = new EditText(this);
        input.setText(sessionManager.getBaseUrl());
        input.setSingleLine(true);
        input.setTextSize(14f);
        dialogLayout.addView(input);

        builder.setView(dialogLayout);

        builder.setPositiveButton("Save", (dialog, which) -> {
            String newUrl = input.getText() != null ? input.getText().toString().trim() : "";
            if (!newUrl.isEmpty()) {
                sessionManager.saveBaseUrl(newUrl);
                String updatedUrl = sessionManager.getBaseUrl();
                serverConfigText.setText("⚙️ Server Domain: " + updatedUrl);
                Toast.makeText(this, "Server domain updated to: " + updatedUrl, Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNeutralButton("Reset Default", (dialog, which) -> {
            sessionManager.saveBaseUrl(SessionManager.DEFAULT_BASE_URL);
            String defaultUrl = sessionManager.getBaseUrl();
            serverConfigText.setText("⚙️ Server Domain: " + defaultUrl);
            Toast.makeText(this, "Reset to default: " + defaultUrl, Toast.LENGTH_SHORT).show();
        });

        builder.setNegativeButton("Cancel", (dialog, which) -> dialog.dismiss());

        builder.show();
    }

    private void attemptLogin() {
        String email = emailInput.getText() != null ? emailInput.getText().toString().trim() : "";
        String password = passwordInput.getText() != null ? passwordInput.getText().toString() : "";

        if (email.isEmpty() || password.isEmpty()) {
            errorTextView.setText("Please enter both email and password.");
            errorTextView.setVisibility(View.VISIBLE);
            return;
        }

        errorTextView.setVisibility(View.GONE);
        progressBar.setVisibility(View.VISIBLE);
        loginButton.setEnabled(false);

        LoginRequest loginRequest = new LoginRequest(email, password);
        apiClient.login(loginRequest, new HealthWatchApiClient.ApiCallback<TokenResponse>() {
            @Override
            public void onSuccess(TokenResponse tokenResponse) {
                progressBar.setVisibility(View.GONE);
                loginButton.setEnabled(true);

                if (tokenResponse == null || tokenResponse.getUser() == null) {
                    errorTextView.setText("Login succeeded, but the server returned an incomplete user profile.");
                    errorTextView.setVisibility(View.VISIBLE);
                    return;
                }

                UserResponse user = tokenResponse.getUser();
                if (user.getEmail() == null || user.getEmail().trim().isEmpty()) {
                    errorTextView.setText("Login succeeded, but the server returned an incomplete user profile (missing email).");
                    errorTextView.setVisibility(View.VISIBLE);
                    return;
                }

                String displayName = user.getFullName() != null && !user.getFullName().isEmpty()
                        ? user.getFullName()
                        : user.getEmail();

                if (user.isMustChangePassword()) {
                    Toast.makeText(LoginActivity.this, "First login detected. Please set your permanent account password.", Toast.LENGTH_LONG).show();
                    Intent resetIntent = new Intent(LoginActivity.this, ResetPasswordActivity.class);
                    startActivity(resetIntent);
                    finish();
                    return;
                }

                Toast.makeText(LoginActivity.this, "Welcome, " + displayName, Toast.LENGTH_SHORT).show();
                startActivity(new Intent(LoginActivity.this, DashboardActivity.class));
                finish();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                loginButton.setEnabled(true);

                String errorMsg = e != null && e.getMessage() != null
                        ? e.getMessage()
                        : "Login failed. Check server connectivity or credentials.";
                errorTextView.setText(errorMsg);
                errorTextView.setVisibility(View.VISIBLE);
            }
        });
    }
}
