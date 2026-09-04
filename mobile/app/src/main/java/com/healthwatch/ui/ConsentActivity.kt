package com.healthwatch.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.healthwatch.data.api.HealthWatchApiClient
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.ConsentGrantRequest
import com.healthwatch.data.model.ConsentRevokeRequest
import kotlinx.coroutines.launch

class ConsentActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient

    private lateinit var consentStatusBadge: TextView
    private lateinit var consentValidUntilText: TextView
    private lateinit var permissionStatusText: TextView
    private lateinit var grantButton: Button
    private lateinit var revokeButton: Button
    private lateinit var permissionButton: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var feedbackMessageText: TextView

    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val fineGranted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] ?: false
        val coarseGranted = permissions[Manifest.permission.ACCESS_COARSE_LOCATION] ?: false
        if (fineGranted || coarseGranted) {
            updatePermissionStatus(true)
            Toast.makeText(this, "Android location permission granted.", Toast.LENGTH_SHORT).show()
        } else {
            updatePermissionStatus(false)
            Toast.makeText(this, "Location permission is required for monitoring.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)

        buildUi()
        refreshConsentState()
    }

    private fun buildUi() {
        val root = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#0B1120"))
            isFillViewport = true
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 48, 40, 48)
        }

        val backButton = Button(this).apply {
            text = "← Back to Dashboard"
            textSize = 12f
            setTextColor(Color.parseColor("#38BDF8"))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener { finish() }
        }
        container.addView(backButton)

        val headerTitle = TextView(this).apply {
            text = "Location Consent Agreement"
            textSize = 22f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 16, 0, 8)
        }
        container.addView(headerTitle)

        // Mandatory Transparency Disclosure Box
        val disclosureBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 12, 0, 24) }
            layoutParams = params
        }

        val disclosureTitle = TextView(this).apply {
            text = "MANDATORY TRANSPARENCY NOTICE"
            textSize = 11f
            setTextColor(Color.parseColor("#38BDF8"))
            typeface = Typeface.DEFAULT_BOLD
        }
        val disclosureBody = TextView(this).apply {
            text = "“HealthWatch will collect your location approximately every 15 minutes during the authorized monitoring period.”"
            textSize = 14f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 8, 0, 12)
        }
        val disclosureTerms = TextView(this).apply {
            text = "Location data is recorded solely for quarantine compliance verification, spatial outbreak hotspot detection, and contact safety. HealthWatch strictly prohibits hidden or covert tracking. You may revoke this authorization at any time."
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
        }

        disclosureBox.addView(disclosureTitle)
        disclosureBox.addView(disclosureBody)
        disclosureBox.addView(disclosureTerms)
        container.addView(disclosureBox)

        // Consent Status Card
        val statusCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 24) }
            layoutParams = params
        }

        consentStatusBadge = TextView(this).apply {
            text = "CONSENT: LOADING..."
            textSize = 13f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setBackgroundColor(Color.parseColor("#334155"))
            setPadding(16, 8, 16, 8)
        }
        consentValidUntilText = TextView(this).apply {
            text = "Authorized Window: —"
            textSize = 12f
            setTextColor(Color.parseColor("#CBD5E1"))
            setPadding(0, 12, 0, 8)
        }
        permissionStatusText = TextView(this).apply {
            text = "Android OS Permission: Checking..."
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
        }

        statusCard.addView(consentStatusBadge)
        statusCard.addView(consentValidUntilText)
        statusCard.addView(permissionStatusText)
        container.addView(statusCard)

        // Feedback / Alert Text
        feedbackMessageText = TextView(this).apply {
            textSize = 12f
            setTextColor(Color.parseColor("#38BDF8"))
            visibility = View.GONE
            setPadding(0, 0, 0, 16)
        }
        container.addView(feedbackMessageText)

        progressBar = ProgressBar(this).apply {
            visibility = View.GONE
            setPadding(0, 8, 0, 16)
        }
        container.addView(progressBar)

        // Android Permission Button
        permissionButton = Button(this).apply {
            text = "REQUEST ANDROID LOCATION PERMISSION"
            textSize = 12f
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.parseColor("#334155"))
            setOnClickListener { requestAndroidPermissions() }
        }
        container.addView(permissionButton)

        // Spacer
        container.addView(View(this).apply { layoutParams = LinearLayout.LayoutParams(1, 16) })

        // Grant Consent Button
        grantButton = Button(this).apply {
            text = "I AGREE & GRANT CONSENT (14 DAYS)"
            textSize = 13f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setBackgroundColor(Color.parseColor("#0284C7")) // Cyan 600
            setOnClickListener { grantConsent() }
        }
        container.addView(grantButton)

        // Spacer
        container.addView(View(this).apply { layoutParams = LinearLayout.LayoutParams(1, 16) })

        // Revoke Consent Button
        revokeButton = Button(this).apply {
            text = "REVOKE CONSENT & TERMINATE MONITORING"
            textSize = 12f
            setTextColor(Color.parseColor("#FDA4AF"))
            setBackgroundColor(Color.parseColor("#881337")) // Rose 900
            setOnClickListener { revokeConsent() }
        }
        container.addView(revokeButton)

        root.addView(container)
        setContentView(root)
    }

    private fun checkAndroidPermissions(): Boolean {
        val fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        return fine || coarse
    }

    private fun updatePermissionStatus(granted: Boolean) {
        if (granted) {
            permissionStatusText.text = "Android OS Permission: GRANTED ✓"
            permissionStatusText.setTextColor(Color.parseColor("#34D399")) // Emerald 400
            permissionButton.visibility = View.GONE
        } else {
            permissionStatusText.text = "Android OS Permission: NOT GRANTED"
            permissionStatusText.setTextColor(Color.parseColor("#F43F5E")) // Rose 500
            permissionButton.visibility = View.VISIBLE
        }
    }

    private fun requestAndroidPermissions() {
        val perms = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        locationPermissionLauncher.launch(perms.toTypedArray())
    }

    private fun refreshConsentState() {
        updatePermissionStatus(checkAndroidPermissions())

        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = apiClient.getMonitoringStatus()
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                val status = result.getOrThrow()
                if (status.hasActiveConsent && status.activeConsent != null) {
                    consentStatusBadge.text = "CONSENT: ACTIVE (${status.activeConsent.consentVersion})"
                    consentStatusBadge.setBackgroundColor(Color.parseColor("#059669")) // Emerald 600
                    consentValidUntilText.text = "Authorized Window: Valid until ${status.activeConsent.monitoringEnd}"
                    grantButton.visibility = View.GONE
                    revokeButton.visibility = View.VISIBLE
                } else {
                    consentStatusBadge.text = "CONSENT: NOT ACTIVE / REVOKED"
                    consentStatusBadge.setBackgroundColor(Color.parseColor("#475569"))
                    consentValidUntilText.text = "Authorized Window: Explicit agreement required."
                    grantButton.visibility = View.VISIBLE
                    revokeButton.visibility = View.GONE
                }
            } else {
                feedbackMessageText.text = "Failed to query consent: ${result.exceptionOrNull()?.message}"
                feedbackMessageText.visibility = View.VISIBLE
            }
        }
    }

    private fun grantConsent() {
        if (!checkAndroidPermissions()) {
            requestAndroidPermissions()
            return
        }

        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = apiClient.grantConsent(ConsentGrantRequest(durationDays = 14))
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                feedbackMessageText.text = "Explicit 14-day consent granted successfully."
                feedbackMessageText.setTextColor(Color.parseColor("#34D399"))
                feedbackMessageText.visibility = View.VISIBLE
                refreshConsentState()
            } else {
                feedbackMessageText.text = "Error granting consent: ${result.exceptionOrNull()?.message}"
                feedbackMessageText.setTextColor(Color.parseColor("#FDA4AF"))
                feedbackMessageText.visibility = View.VISIBLE
            }
        }
    }

    private fun revokeConsent() {
        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = apiClient.revokeConsent(ConsentRevokeRequest())
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                feedbackMessageText.text = "Location consent revoked. All active sessions stopped."
                feedbackMessageText.setTextColor(Color.parseColor("#FDA4AF"))
                feedbackMessageText.visibility = View.VISIBLE
                refreshConsentState()
            } else {
                feedbackMessageText.text = "Error revoking consent: ${result.exceptionOrNull()?.message}"
                feedbackMessageText.visibility = View.VISIBLE
            }
        }
    }
}
