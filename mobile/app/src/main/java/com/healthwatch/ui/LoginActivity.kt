package com.healthwatch.ui

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.healthwatch.data.api.HealthWatchApiClient
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.LoginRequest
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient

    private lateinit var emailInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var serverUrlInput: EditText
    private lateinit var loginButton: Button
    private lateinit var demoPatientButton: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var errorTextView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)

        // Check if already authenticated
        if (sessionManager.isLoggedIn()) {
            startActivity(Intent(this, DashboardActivity::class.java))
            finish()
            return
        }

        buildUi()
    }

    private fun buildUi() {
        val root = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#0F172A")) // Slate 900
            isFillViewport = true
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(48, 64, 48, 64)
        }

        // App Logo & Title
        val titleText = TextView(this).apply {
            text = "HealthWatch"
            textSize = 28f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
        }

        val subtitleText = TextView(this).apply {
            text = "Disease Surveillance & Patient Monitoring"
            textSize = 14f
            setTextColor(Color.parseColor("#94A3B8")) // Slate 400
            gravity = Gravity.CENTER
            setPadding(0, 8, 0, 48)
        }

        container.addView(titleText)
        container.addView(subtitleText)

        // Server URL input
        val serverLabel = TextView(this).apply {
            text = "Backend Server URL:"
            textSize = 12f
            setTextColor(Color.parseColor("#CBD5E1"))
        }
        serverUrlInput = EditText(this).apply {
            setText(sessionManager.getBaseUrl())
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(24, 24, 24, 24)
            textSize = 14f
        }
        container.addView(serverLabel)
        container.addView(serverUrlInput)

        // Spacer
        container.addView(View(this).apply { layoutParams = LinearLayout.LayoutParams(1, 24) })

        // Email input
        val emailLabel = TextView(this).apply {
            text = "Patient Email:"
            textSize = 12f
            setTextColor(Color.parseColor("#CBD5E1"))
        }
        emailInput = EditText(this).apply {
            hint = "patient@healthwatch.org"
            setText("patient.synth101@healthwatch.org")
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(24, 24, 24, 24)
            textSize = 14f
        }
        container.addView(emailLabel)
        container.addView(emailInput)

        // Spacer
        container.addView(View(this).apply { layoutParams = LinearLayout.LayoutParams(1, 24) })

        // Password input
        val passwordLabel = TextView(this).apply {
            text = "Password:"
            textSize = 12f
            setTextColor(Color.parseColor("#CBD5E1"))
        }
        passwordInput = EditText(this).apply {
            hint = "••••••••"
            setText("Patient@HealthWatch2026")
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(24, 24, 24, 24)
            textSize = 14f
        }
        container.addView(passwordLabel)
        container.addView(passwordInput)

        // Error message text
        errorTextView = TextView(this).apply {
            textSize = 12f
            setTextColor(Color.parseColor("#F43F5E")) // Rose 500
            visibility = View.GONE
            setPadding(0, 16, 0, 8)
        }
        container.addView(errorTextView)

        // Progress Bar
        progressBar = ProgressBar(this).apply {
            visibility = View.GONE
            setPadding(0, 16, 0, 16)
        }
        container.addView(progressBar)

        // Login Button
        loginButton = Button(this).apply {
            text = "LOG IN"
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.parseColor("#0284C7")) // Brand Cyan 600
            typeface = Typeface.DEFAULT_BOLD
            setOnClickListener { attemptLogin() }
        }
        container.addView(loginButton)

        // Quick Demo Fill Button
        demoPatientButton = Button(this).apply {
            text = "Use Synthetic Patient 101"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener {
                emailInput.setText("patient.synth101@healthwatch.org")
                passwordInput.setText("Patient@HealthWatch2026")
            }
        }
        container.addView(demoPatientButton)

        root.addView(container)
        setContentView(root)
    }

    private fun attemptLogin() {
        val email = emailInput.text.toString().trim()
        val password = passwordInput.text.toString().trim()
        val serverUrl = serverUrlInput.text.toString().trim()

        if (email.isEmpty() || password.isEmpty()) {
            errorTextView.text = "Please enter both email and password."
            errorTextView.visibility = View.VISIBLE
            return
        }

        if (serverUrl.isNotEmpty()) {
            sessionManager.saveBaseUrl(serverUrl)
        }

        errorTextView.visibility = View.GONE
        progressBar.visibility = View.VISIBLE
        loginButton.isEnabled = false

        lifecycleScope.launch {
            val result = apiClient.login(LoginRequest(email, password))
            progressBar.visibility = View.GONE
            loginButton.isEnabled = true

            if (result.isSuccess) {
                val tokenResp = result.getOrNull()
                Toast.makeText(this@LoginActivity, "Welcome, ${tokenResp?.fullName}", Toast.LENGTH_SHORT).show()
                startActivity(Intent(this@LoginActivity, DashboardActivity::class.java))
                finish()
            } else {
                errorTextView.text = result.exceptionOrNull()?.message ?: "Login failed. Check server connectivity."
                errorTextView.visibility = View.VISIBLE
            }
        }
    }
}
