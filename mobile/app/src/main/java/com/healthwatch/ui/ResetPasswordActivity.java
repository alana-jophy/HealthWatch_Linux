package com.healthwatch.ui;

import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.text.method.HideReturnsTransformationMethod;
import android.text.method.PasswordTransformationMethod;
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
import com.healthwatch.data.model.AuthModels.ChangePasswordResponse;

public class ResetPasswordActivity extends AppCompatActivity {

    private SessionManager sessionManager;
    private HealthWatchApiClient apiClient;

    private EditText currentPasswordInput;
    private EditText newPasswordInput;
    private EditText confirmPasswordInput;

    private Button submitButton;
    private Button logoutButton;
    private ProgressBar progressBar;
    private TextView errorTextView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        sessionManager = new SessionManager(this);
        apiClient = new HealthWatchApiClient(sessionManager);

        buildUi();
    }

    private void buildUi() {
        ScrollView root = new ScrollView(this);
        root.setBackgroundColor(Color.parseColor("#0F172A")); // Slate 900
        root.setFillViewport(true);

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setGravity(Gravity.CENTER_HORIZONTAL);
        container.setPadding(48, 64, 48, 64);

        // Header Title
        TextView titleText = new TextView(this);
        titleText.setText("HealthWatch");
        titleText.setTextSize(28f);
        titleText.setTextColor(Color.WHITE);
        titleText.setTypeface(Typeface.DEFAULT_BOLD);
        titleText.setGravity(Gravity.CENTER);

        boolean isEnforcedFirstLogin = sessionManager.mustChangePassword();

        TextView subtitleText = new TextView(this);
        subtitleText.setText(isEnforcedFirstLogin ? "First-Time Login Security Setup" : "Account Password Security");
        subtitleText.setTextSize(15f);
        subtitleText.setTextColor(Color.parseColor("#38BDF8")); // Cyan 400
        subtitleText.setTypeface(Typeface.DEFAULT_BOLD);
        subtitleText.setGravity(Gravity.CENTER);
        subtitleText.setPadding(0, 8, 0, 24);

        container.addView(titleText);
        container.addView(subtitleText);

        // Explanatory Info Card
        LinearLayout infoCard = new LinearLayout(this);
        infoCard.setOrientation(LinearLayout.VERTICAL);
        infoCard.setBackgroundColor(Color.parseColor("#1E293B")); // Slate 800
        infoCard.setPadding(32, 28, 32, 28);
        infoCard.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView infoTitle = new TextView(this);
        infoTitle.setText(isEnforcedFirstLogin ? "Temporary Password Detected" : "Update Account Password");
        infoTitle.setTextSize(13f);
        infoTitle.setTextColor(isEnforcedFirstLogin ? Color.parseColor("#F59E0B") : Color.parseColor("#38BDF8"));
        infoTitle.setTypeface(Typeface.DEFAULT_BOLD);

        TextView infoDesc = new TextView(this);
        infoDesc.setText(isEnforcedFirstLogin
                ? "You are logging in with the initial password received during registration. For your account security, please set your personal password to proceed."
                : "Enter your current password and your desired new password below to update your login credentials.");
        infoDesc.setTextSize(12f);
        infoDesc.setTextColor(Color.parseColor("#CBD5E1"));
        infoDesc.setPadding(0, 8, 0, 0);

        String userEmail = sessionManager.getUserEmail();
        String pseudoId = sessionManager.getPatientPseudoId();
        if (userEmail != null && !userEmail.isEmpty()) {
            TextView userBadge = new TextView(this);
            userBadge.setText("Account: " + (pseudoId != null ? pseudoId + " (" + userEmail + ")" : userEmail));
            userBadge.setTextSize(11f);
            userBadge.setTextColor(Color.parseColor("#94A3B8"));
            userBadge.setPadding(0, 12, 0, 0);
            userBadge.setTypeface(Typeface.MONOSPACE);
            infoCard.addView(infoTitle);
            infoCard.addView(infoDesc);
            infoCard.addView(userBadge);
        } else {
            infoCard.addView(infoTitle);
            infoCard.addView(infoDesc);
        }

        container.addView(infoCard);

        // Spacer
        View spacer1 = new View(this);
        spacer1.setLayoutParams(new LinearLayout.LayoutParams(1, 32));
        container.addView(spacer1);

        // 1. Current Registration Password Input
        TextView currentLabel = new TextView(this);
        currentLabel.setText("Current Registration Password:");
        currentLabel.setTextSize(12f);
        currentLabel.setTextColor(Color.parseColor("#CBD5E1"));
        currentLabel.setPadding(0, 0, 0, 6);
        container.addView(currentLabel);

        currentPasswordInput = new EditText(this);
        LinearLayout currentContainer = createPasswordInputContainer(currentPasswordInput, "Enter temporary password");
        container.addView(currentContainer);

        // Spacer
        View spacer2 = new View(this);
        spacer2.setLayoutParams(new LinearLayout.LayoutParams(1, 24));
        container.addView(spacer2);

        // 2. New Password Input
        TextView newLabel = new TextView(this);
        newLabel.setText("New Password (min 6 characters):");
        newLabel.setTextSize(12f);
        newLabel.setTextColor(Color.parseColor("#CBD5E1"));
        newLabel.setPadding(0, 0, 0, 6);
        container.addView(newLabel);

        newPasswordInput = new EditText(this);
        LinearLayout newContainer = createPasswordInputContainer(newPasswordInput, "Enter your new password");
        container.addView(newContainer);

        // Spacer
        View spacer3 = new View(this);
        spacer3.setLayoutParams(new LinearLayout.LayoutParams(1, 24));
        container.addView(spacer3);

        // 3. Confirm New Password Input
        TextView confirmLabel = new TextView(this);
        confirmLabel.setText("Confirm New Password:");
        confirmLabel.setTextSize(12f);
        confirmLabel.setTextColor(Color.parseColor("#CBD5E1"));
        confirmLabel.setPadding(0, 0, 0, 6);
        container.addView(confirmLabel);

        confirmPasswordInput = new EditText(this);
        LinearLayout confirmContainer = createPasswordInputContainer(confirmPasswordInput, "Re-enter your new password");
        container.addView(confirmContainer);

        // Error message view
        errorTextView = new TextView(this);
        errorTextView.setTextSize(12f);
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
        View spacer4 = new View(this);
        spacer4.setLayoutParams(new LinearLayout.LayoutParams(1, 32));
        container.addView(spacer4);

        // Submit Button
        submitButton = new Button(this);
        submitButton.setText("SET PASSWORD & CONTINUE");
        submitButton.setTextColor(Color.WHITE);
        submitButton.setBackgroundColor(Color.parseColor("#0284C7")); // Brand Cyan 600
        submitButton.setTypeface(Typeface.DEFAULT_BOLD);
        submitButton.setTextSize(15f);
        submitButton.setPadding(0, 24, 0, 24);
        submitButton.setOnClickListener(v -> attemptChangePassword());
        container.addView(submitButton);

        // Spacer
        View spacer5 = new View(this);
        spacer5.setLayoutParams(new LinearLayout.LayoutParams(1, 16));
        container.addView(spacer5);

        // Logout or Cancel Button
        logoutButton = new Button(this);
        if (isEnforcedFirstLogin) {
            logoutButton.setText("SIGN OUT");
            logoutButton.setTextColor(Color.parseColor("#94A3B8"));
            logoutButton.setBackgroundColor(Color.parseColor("#1E293B"));
            logoutButton.setTextSize(13f);
            logoutButton.setPadding(0, 20, 0, 20);
            logoutButton.setOnClickListener(v -> {
                sessionManager.clearSession();
                startActivity(new Intent(ResetPasswordActivity.this, LoginActivity.class));
                finish();
            });
        } else {
            logoutButton.setText("CANCEL / RETURN TO DASHBOARD");
            logoutButton.setTextColor(Color.parseColor("#94A3B8"));
            logoutButton.setBackgroundColor(Color.parseColor("#1E293B"));
            logoutButton.setTextSize(13f);
            logoutButton.setPadding(0, 20, 0, 20);
            logoutButton.setOnClickListener(v -> finish());
        }
        container.addView(logoutButton);

        root.addView(container);
        setContentView(root);
    }

    private LinearLayout createPasswordInputContainer(EditText editText, String hint) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setBackgroundColor(Color.parseColor("#1E293B"));
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        editText.setHint(hint);
        editText.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        editText.setTextColor(Color.WHITE);
        editText.setHintTextColor(Color.parseColor("#64748B"));
        editText.setBackgroundColor(Color.TRANSPARENT);
        editText.setPadding(28, 24, 12, 24);
        editText.setTextSize(14f);
        LinearLayout.LayoutParams inputParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
        editText.setLayoutParams(inputParams);

        TextView eyeButton = new TextView(this);
        eyeButton.setText("👁");
        eyeButton.setTextSize(18f);
        eyeButton.setPadding(20, 16, 28, 16);
        eyeButton.setTextColor(Color.parseColor("#94A3B8"));
        eyeButton.setGravity(Gravity.CENTER);
        eyeButton.setContentDescription("Show or hide password");

        final boolean[] isVisible = {false};
        eyeButton.setOnClickListener(v -> {
            if (isVisible[0]) {
                editText.setTransformationMethod(PasswordTransformationMethod.getInstance());
                eyeButton.setText("👁");
                eyeButton.setTextColor(Color.parseColor("#94A3B8"));
                isVisible[0] = false;
            } else {
                editText.setTransformationMethod(HideReturnsTransformationMethod.getInstance());
                eyeButton.setText("👁‍🗨");
                eyeButton.setTextColor(Color.parseColor("#38BDF8"));
                isVisible[0] = true;
            }
            if (editText.getText() != null) {
                editText.setSelection(editText.getText().length());
            }
        });

        row.addView(editText);
        row.addView(eyeButton);
        return row;
    }

    private void attemptChangePassword() {
        String currentPassword = currentPasswordInput.getText() != null ? currentPasswordInput.getText().toString() : "";
        String newPassword = newPasswordInput.getText() != null ? newPasswordInput.getText().toString() : "";
        String confirmPassword = confirmPasswordInput.getText() != null ? confirmPasswordInput.getText().toString() : "";

        if (currentPassword.isEmpty()) {
            showError("Please enter your current registration password.");
            return;
        }

        if (newPassword.isEmpty() || newPassword.length() < 6) {
            showError("New password must be at least 6 characters long.");
            return;
        }

        if (newPassword.equals(currentPassword)) {
            showError("Your new password cannot be the same as your registration password.");
            return;
        }

        if (!newPassword.equals(confirmPassword)) {
            showError("New password and confirmation password do not match.");
            return;
        }

        hideError();
        progressBar.setVisibility(View.VISIBLE);
        submitButton.setEnabled(false);
        logoutButton.setEnabled(false);

        apiClient.changePassword(currentPassword, newPassword, new HealthWatchApiClient.ApiCallback<ChangePasswordResponse>() {
            @Override
            public void onSuccess(ChangePasswordResponse result) {
                progressBar.setVisibility(View.GONE);
                submitButton.setEnabled(true);
                logoutButton.setEnabled(true);

                Toast.makeText(ResetPasswordActivity.this, "Password set successfully! Welcome to HealthWatch.", Toast.LENGTH_SHORT).show();
                startActivity(new Intent(ResetPasswordActivity.this, DashboardActivity.class));
                finish();
            }

            @Override
            public void onError(Exception e) {
                progressBar.setVisibility(View.GONE);
                submitButton.setEnabled(true);
                logoutButton.setEnabled(true);

                String msg = (e != null && e.getMessage() != null)
                        ? e.getMessage()
                        : "Failed to update password. Please check your credentials.";
                showError(msg);
            }
        });
    }

    private void showError(String msg) {
        errorTextView.setText(msg);
        errorTextView.setVisibility(View.VISIBLE);
    }

    private void hideError() {
        errorTextView.setVisibility(View.GONE);
    }
}
