package com.healthwatch.ui

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.healthwatch.data.api.HealthWatchApiClient
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.SessionStartRequest
import com.healthwatch.data.model.SessionStopRequest
import com.healthwatch.service.LocationMonitoringService
import kotlinx.coroutines.launch

class MonitoringActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient

    private lateinit var statusBadgeText: TextView
    private lateinit var monitoringStartText: TextView
    private lateinit var monitoringEndText: TextView
    private lateinit var samplingIntervalText: TextView
    private lateinit var noticeText: TextView
    private lateinit var startMonitoringButton: Button
    private lateinit var stopMonitoringButton: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var alertMessageText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)

        buildUi()
        refreshMonitoringStatus()
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
            text = "My Monitoring"
            textSize = 24f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 16, 0, 16)
        }
        container.addView(headerTitle)

        // Main Monitoring Card
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(32, 28, 32, 28)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 24) }
            layoutParams = params
        }

        // 1. Monitoring Status: ACTIVE / INACTIVE
        val statusLabel = TextView(this).apply {
            text = "Monitoring Status:"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
        }
        statusBadgeText = TextView(this).apply {
            text = "CHECKING..."
            textSize = 18f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 4, 0, 20)
        }
        card.addView(statusLabel)
        card.addView(statusBadgeText)

        // 2. Monitoring Start: ...
        val startLabel = TextView(this).apply {
            text = "Monitoring Start:"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
        }
        monitoringStartText = TextView(this).apply {
            text = "—"
            textSize = 14f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 4, 0, 20)
        }
        card.addView(startLabel)
        card.addView(monitoringStartText)

        // 3. Monitoring End: ...
        val endLabel = TextView(this).apply {
            text = "Monitoring End:"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
        }
        monitoringEndText = TextView(this).apply {
            text = "—"
            textSize = 14f
            setTextColor(Color.parseColor("#38BDF8"))
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 4, 0, 20)
        }
        card.addView(endLabel)
        card.addView(monitoringEndText)

        // 4. Sampling Interval: Approximately 15 minutes
        val intervalLabel = TextView(this).apply {
            text = "Sampling Interval:"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
        }
        samplingIntervalText = TextView(this).apply {
            text = "Approximately 15 minutes"
            textSize = 14f
            setTextColor(Color.parseColor("#34D399")) // Emerald 400
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 4, 0, 12)
        }
        card.addView(intervalLabel)
        card.addView(samplingIntervalText)

        container.addView(card)

        // Explanation Notice
        noticeText = TextView(this).apply {
            text = "HealthWatch collects location observations approximately every 15 minutes under authorized consent. GPS observations are submitted via background foreground service."
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 0, 0, 20)
        }
        container.addView(noticeText)

        alertMessageText = TextView(this).apply {
            textSize = 12f
            setTextColor(Color.parseColor("#FDA4AF"))
            visibility = View.GONE
            setPadding(0, 0, 0, 16)
        }
        container.addView(alertMessageText)

        progressBar = ProgressBar(this).apply {
            visibility = View.GONE
            setPadding(0, 0, 0, 16)
        }
        container.addView(progressBar)

        // Action Buttons: START MONITORING vs STOP MONITORING
        startMonitoringButton = Button(this).apply {
            text = "START MONITORING"
            textSize = 14f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setBackgroundColor(Color.parseColor("#059669")) // Emerald 600
            visibility = View.GONE
            setOnClickListener { startMonitoring() }
        }
        container.addView(startMonitoringButton)

        stopMonitoringButton = Button(this).apply {
            text = "STOP MONITORING"
            textSize = 14f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setBackgroundColor(Color.parseColor("#E11D48")) // Rose 600
            visibility = View.GONE
            setOnClickListener { stopMonitoring() }
        }
        container.addView(stopMonitoringButton)

        root.addView(container)
        setContentView(root)
    }

    private fun refreshMonitoringStatus() {
        progressBar.visibility = View.VISIBLE
        alertMessageText.visibility = View.GONE

        lifecycleScope.launch {
            val result = apiClient.getMonitoringStatus()
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                val status = result.getOrThrow()
                samplingIntervalText.text = status.samplingIntervalDescription

                if (status.hasActiveSession && status.activeSession != null) {
                    val s = status.activeSession
                    statusBadgeText.text = "ACTIVE"
                    statusBadgeText.setTextColor(Color.parseColor("#34D399")) // Emerald 400
                    monitoringStartText.text = s.startTime
                    monitoringEndText.text = s.endTime

                    startMonitoringButton.visibility = View.GONE
                    stopMonitoringButton.visibility = View.VISIBLE

                    // Ensure Foreground Service is running
                    startForegroundLocationService()
                } else {
                    statusBadgeText.text = "INACTIVE"
                    statusBadgeText.setTextColor(Color.parseColor("#94A3B8"))
                    monitoringStartText.text = "—"
                    monitoringEndText.text = "—"

                    startMonitoringButton.visibility = View.VISIBLE
                    stopMonitoringButton.visibility = View.GONE
                }
            } else {
                alertMessageText.text = "Failed to load monitoring status: ${result.exceptionOrNull()?.message}"
                alertMessageText.visibility = View.VISIBLE
            }
        }
    }

    private fun startMonitoring() {
        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = apiClient.startMonitoringSession(SessionStartRequest(durationHours = 24))
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                val session = result.getOrThrow()
                sessionManager.saveActiveSessionId(session.id)
                startForegroundLocationService()
                refreshMonitoringStatus()
            } else {
                alertMessageText.text = "Cannot start monitoring: ${result.exceptionOrNull()?.message}"
                alertMessageText.visibility = View.VISIBLE
            }
        }
    }

    private fun stopMonitoring() {
        progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = apiClient.stopMonitoringSession(SessionStopRequest())
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                sessionManager.saveActiveSessionId(null)
                stopForegroundLocationService()
                refreshMonitoringStatus()
            } else {
                alertMessageText.text = "Failed to stop session: ${result.exceptionOrNull()?.message}"
                alertMessageText.visibility = View.VISIBLE
            }
        }
    }

    private fun startForegroundLocationService() {
        val serviceIntent = Intent(this, LocationMonitoringService::class.java).apply {
            action = LocationMonitoringService.ACTION_START
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ContextCompat.startForegroundService(this, serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun stopForegroundLocationService() {
        val serviceIntent = Intent(this, LocationMonitoringService::class.java).apply {
            action = LocationMonitoringService.ACTION_STOP
        }
        startService(serviceIntent)
    }
}
