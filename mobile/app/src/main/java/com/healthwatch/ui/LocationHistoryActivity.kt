package com.healthwatch.ui

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
import com.healthwatch.data.model.QueuedLocationObservation
import kotlinx.coroutines.launch

class LocationHistoryActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient
    private lateinit var offlineQueue: OfflineLocationQueue

    private lateinit var summaryText: TextView
    private lateinit var syncButton: Button
    private lateinit var listContainer: LinearLayout
    private lateinit var progressBar: ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)
        offlineQueue = OfflineLocationQueue(this)

        buildUi()
        loadLocationHistory()
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
            text = "Location Telemetry History"
            textSize = 22f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 16, 0, 8)
        }
        container.addView(headerTitle)

        // Queue Control Panel Card
        val controlCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 8, 0, 24) }
            layoutParams = params
        }

        summaryText = TextView(this).apply {
            text = "Checking offline storage..."
            textSize = 13f
            setTextColor(Color.WHITE)
            setPadding(0, 0, 0, 16)
        }
        controlCard.addView(summaryText)

        syncButton = Button(this).apply {
            text = "SYNC OFFLINE QUEUE NOW"
            textSize = 12f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setBackgroundColor(Color.parseColor("#0284C7")) // Cyan 600
            setOnClickListener { syncOfflineQueue() }
        }
        controlCard.addView(syncButton)
        container.addView(controlCard)

        progressBar = ProgressBar(this).apply {
            visibility = View.GONE
            setPadding(0, 0, 0, 16)
        }
        container.addView(progressBar)

        val listTitle = TextView(this).apply {
            text = "RECORDED OBSERVATIONS (SOURCE: PATIENT_GPS)"
            textSize = 11f
            setTextColor(Color.parseColor("#64748B"))
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 8, 0, 12)
        }
        container.addView(listTitle)

        listContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        container.addView(listContainer)

        root.addView(container)
        setContentView(root)
    }

    private fun loadLocationHistory() {
        val observations = offlineQueue.getAllObservations(100)
        val pendingCount = offlineQueue.getPendingCount()

        summaryText.text = "Stored: ${observations.size} observations ($pendingCount pending server upload)"

        listContainer.removeAllViews()

        if (observations.isEmpty()) {
            val emptyView = TextView(this).apply {
                text = "No location observations collected yet. Start an active monitoring session to begin periodic ~15-minute telemetry."
                textSize = 13f
                setTextColor(Color.parseColor("#94A3B8"))
                setPadding(0, 16, 0, 0)
            }
            listContainer.addView(emptyView)
            return
        }

        for (item in observations) {
            val itemCard = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setBackgroundColor(Color.parseColor("#1E293B"))
                setPadding(24, 20, 24, 20)
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply { setMargins(0, 0, 0, 12) }
                layoutParams = params
            }

            val coordText = TextView(this).apply {
                text = "📍 Lat: %.5f, Lng: %.5f".format(item.latitude, item.longitude)
                textSize = 14f
                setTextColor(Color.WHITE)
                typeface = Typeface.DEFAULT_BOLD
            }
            val metaText = TextView(this).apply {
                val acc = item.accuracy?.let { "±%.1fm".format(it) } ?: "N/A"
                text = "Accuracy: $acc • Source: ${item.source} • Time: ${item.recordedAt}"
                textSize = 11f
                setTextColor(Color.parseColor("#94A3B8"))
                setPadding(0, 4, 0, 8)
            }

            val statusBadge = TextView(this).apply {
                text = if (item.syncStatus == "SYNCED") "SYNCED TO SERVER ✓" else "QUEUED OFFLINE (PENDING)"
                textSize = 10f
                setTextColor(Color.WHITE)
                typeface = Typeface.DEFAULT_BOLD
                setBackgroundColor(
                    if (item.syncStatus == "SYNCED") Color.parseColor("#059669") else Color.parseColor("#D97706")
                )
                setPadding(12, 6, 12, 6)
                gravity = Gravity.CENTER_VERTICAL
            }

            itemCard.addView(coordText)
            itemCard.addView(metaText)
            itemCard.addView(statusBadge)
            listContainer.addView(itemCard)
        }
    }

    private fun syncOfflineQueue() {
        progressBar.visibility = View.VISIBLE
        syncButton.isEnabled = false

        lifecycleScope.launch {
            val (synced, failed) = apiClient.flushOfflineQueue(offlineQueue)
            progressBar.visibility = View.GONE
            syncButton.isEnabled = true

            Toast.makeText(
                this@LocationHistoryActivity,
                "Sync Complete: $synced uploaded, $failed failed/offline.",
                Toast.LENGTH_SHORT
            ).show()

            loadLocationHistory()
        }
    }
}
