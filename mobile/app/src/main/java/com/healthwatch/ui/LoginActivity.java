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

        // If already authenticated, directly navigate to Dashboard
        if (sessionManager.isLoggedIn()) {
            startActivity(new Intent(this, DashboardActivity.class));
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

        // Email input
        TextView emailLabel = new TextView(this);
        emailLabel.setText("Registered Email Address:");
        emailLabel.setTextSize(13f);
        emailLabel.setTextColor(Color.parseColor("#CBD5E1"));
        emailLabel.setPadding(0, 0, 0, 8);

        emailInput = new EditText(this);
        emailInput.setHint("patient@healthwatch.org");
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

        // Password input
        TextView passwordLabel = new TextView(this);
        passwordLabel.setText("Password:");
        passwordLabel.setTextSize(13f);
        passwordLabel.setTextColor(Color.parseColor("#CBD5E1"));
        passwordLabel.setPadding(0, 0, 0, 8);

        passwordInput = new EditText(this);
        passwordInput.setHint("Enter account password");
        passwordInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        passwordInput.setTextColor(Color.WHITE);
        passwordInput.setHintTextColor(Color.parseColor("#64748B"));
        passwordInput.setBackgroundColor(Color.parseColor("#1E293B"));
        passwordInput.setPadding(28, 28, 28, 28);
        passwordInput.setTextSize(15f);

        container.addView(passwordLabel);
        container.addView(passwordInput);

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

        root.addView(container);
        setContentView(root);
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
