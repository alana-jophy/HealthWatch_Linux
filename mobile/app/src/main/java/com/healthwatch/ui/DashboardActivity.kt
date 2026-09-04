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
import com.healthwatch.data.local.OfflineLocationQueue
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.PatientMonitoringStatusResponse
import kotlinx.coroutines.launch

class DashboardActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient
    private lateinit var offlineQueue: OfflineLocationQueue

    private lateinit var patientNameText: TextView
    private lateinit var patientPseudoText: TextView
    private lateinit var statusBadgeText: TextView
    private lateinit var queueStatusText: TextView
    private lateinit var refreshProgressBar: ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)
        offlineQueue = OfflineLocationQueue(this)

        if (!sessionManager.isLoggedIn()) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        buildUi()
    }

    override fun onResume() {
        super.onResume()
        refreshDashboardData()
    }

    private fun buildUi() {
        val root = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#0B1120")) // Slate 950
            isFillViewport = true
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 48, 40, 48)
        }

        // Header Title
        val appTitle = TextView(this).apply {
            text = "HealthWatch Patient Portal"
            textSize = 20f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
        }
        val appSubtitle = TextView(this).apply {
            text = "Intelligent Disease Surveillance & Contact Tracing"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 4, 0, 32)
        }
        container.addView(appTitle)
        container.addView(appSubtitle)

        // Patient ID Card
        val patientCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(32, 32, 32, 32)
        }

        patientNameText = TextView(this).apply {
            text = sessionManager.getUserName() ?: "Synthetic Patient 101"
            textSize = 18f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
        }
        patientPseudoText = TextView(this).apply {
            text = "ID: ${sessionManager.getPatientPseudoId()}"
            textSize = 13f
            setTextColor(Color.parseColor("#38BDF8")) // Cyan 400
            setPadding(0, 4, 0, 16)
        }

        statusBadgeText = TextView(this).apply {
            text = "MONITORING STATUS: CHECKING..."
            textSize = 12f
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.parseColor("#334155"))
            setPadding(20, 10, 20, 10)
            gravity = Gravity.CENTER
        }

        queueStatusText = TextView(this).apply {
            text = "Offline Queue: 0 pending"
            textSize = 11f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 12, 0, 0)
        }

        patientCard.addView(patientNameText)
        patientCard.addView(patientPseudoText)
        patientCard.addView(statusBadgeText)
        patientCard.addView(queueStatusText)
        container.addView(patientCard)

        // Loading indicator
        refreshProgressBar = ProgressBar(this).apply {
            visibility = View.GONE
            setPadding(0, 16, 0, 16)
        }
        container.addView(refreshProgressBar)

        // Navigation Action Buttons Grid
        val sectionTitle = TextView(this).apply {
            text = "PATIENT MODULES"
            textSize = 12f
            setTextColor(Color.parseColor("#64748B"))
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 32, 0, 16)
        }
        container.addView(sectionTitle)

        // 1. My Monitoring Button
        container.addView(createModuleButton("1. My Monitoring", "Control observation sessions & view interval") {
            startActivity(Intent(this, MonitoringActivity::class.java))
        })

        // 2. Location Consent Button
        container.addView(createModuleButton("2. Location Consent", "Manage explicit 14-day surveillance agreement") {
            startActivity(Intent(this, ConsentActivity::class.java))
        })

        // 3. My Profile Button
        container.addView(createModuleButton("3. My Profile", "View demographics & assigned Kerala ward") {
            startActivity(Intent(this, ProfileActivity::class.java))
        })

        // 4. My Disease Case Button
        container.addView(createModuleButton("4. My Disease Case", "Clinical details, diagnosis & recovery status") {
            startActivity(Intent(this, DiseaseCaseActivity::class.java))
        })

        // 5. Location History Button
        container.addView(createModuleButton("5. Location History", "Review collected GPS points & sync offline queue") {
            startActivity(Intent(this, LocationHistoryActivity::class.java))
        })

        // 6. Movement Roadmap Button
        container.addView(createModuleButton("6. Movement Roadmap", "Sequential spatial observation roadmap") {
            startActivity(Intent(this, RoadmapActivity::class.java))
        })

        // Logout Button
        val logoutButton = Button(this).apply {
            text = "LOG OUT"
            textSize = 12f
            setTextColor(Color.parseColor("#FDA4AF"))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener {
                sessionManager.clearSession()
                startActivity(Intent(this@DashboardActivity, LoginActivity::class.java))
                finish()
            }
        }
        container.addView(logoutButton)

        root.addView(container)
        setContentView(root)
    }

    private fun createModuleButton(title: String, subtitle: String, onClick: () -> Unit): View {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 16) }
            layoutParams = params
            isClickable = true
            setOnClickListener { onClick() }
        }

        val titleView = TextView(this).apply {
            text = title
            textSize = 15f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
        }

        val subtitleView = TextView(this).apply {
            text = subtitle
            textSize = 11f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 4, 0, 0)
        }

        layout.addView(titleView)
        layout.addView(subtitleView)
        return layout
    }

    private fun refreshDashboardData() {
        val pendingCount = offlineQueue.getPendingCount()
        queueStatusText.text = "Offline Queue: $pendingCount observations pending upload"

        refreshProgressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = apiClient.getMonitoringStatus()
            refreshProgressBar.visibility = View.GONE

            if (result.isSuccess) {
                val status: PatientMonitoringStatusResponse = result.getOrThrow()
                patientPseudoText.text = "ID: ${status.patientPseudoId}"

                if (status.hasActiveSession) {
                    statusBadgeText.text = "MONITORING STATUS: ACTIVE"
                    statusBadgeText.setBackgroundColor(Color.parseColor("#059669")) // Emerald 600
                } else {
                    statusBadgeText.text = "MONITORING STATUS: INACTIVE"
                    statusBadgeText.setBackgroundColor(Color.parseColor("#475569")) // Slate 600
                }
            } else {
                statusBadgeText.text = "STATUS: OFFLINE / UNREACHABLE"
                statusBadgeText.setBackgroundColor(Color.parseColor("#E11D48")) // Rose 600
            }
        }
    }
}
