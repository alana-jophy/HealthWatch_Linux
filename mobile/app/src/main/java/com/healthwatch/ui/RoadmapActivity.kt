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
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.MobileRoadmapObservation
import com.healthwatch.data.model.MobileRoadmapResponse
import kotlinx.coroutines.launch

class RoadmapActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient

    private lateinit var container: LinearLayout
    private lateinit var progressBar: ProgressBar
    private lateinit var errorText: TextView
    private lateinit var statsContainer: LinearLayout
    private lateinit var timelineContainer: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)

        buildUi()
        loadRoadmap()
    }

    private fun buildUi() {
        val root = ScrollView(this).apply {
            setBackgroundColor(Color.parseColor("#0B1120"))
            isFillViewport = true
        }

        container = LinearLayout(this).apply {
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
            text = "Movement Roadmap"
            textSize = 22f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 16, 0, 4)
        }
        val headerSubtitle = TextView(this).apply {
            text = "Sequential discrete location observations stream"
            textSize = 12f
            setTextColor(Color.parseColor("#94A3B8"))
            setPadding(0, 0, 0, 20)
        }
        container.addView(headerTitle)
        container.addView(headerSubtitle)

        // Mandatory Technical Limitation Notice Card
        val noticeCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1C1917")) // Stone 900
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 24) }
            layoutParams = params
        }

        val noticeTitle = TextView(this).apply {
            text = "⚠️ IMPORTANT TECHNICAL CLARIFICATION"
            textSize = 12f
            setTextColor(Color.parseColor("#FBBF24")) // Amber 400
            typeface = Typeface.DEFAULT_BOLD
        }
        val noticeBody = TextView(this).apply {
            text = "HealthWatch is NOT performing continuous second-by-second GPS tracking.\n\nObservations are recorded periodically (approx. 15-minute sampling interval). The connecting polyline represents a sequential visual timeline, NOT an exact continuous travel trajectory."
            textSize = 12f
            setTextColor(Color.parseColor("#CBD5E1"))
            setLineSpacing(4f, 1.2f)
            setPadding(0, 8, 0, 0)
        }
        noticeCard.addView(noticeTitle)
        noticeCard.addView(noticeBody)
        container.addView(noticeCard)

        // Progress Bar
        progressBar = ProgressBar(this).apply {
            visibility = View.VISIBLE
            setPadding(0, 16, 0, 16)
        }
        container.addView(progressBar)

        // Error Text
        errorText = TextView(this).apply {
            textSize = 12f
            setTextColor(Color.parseColor("#FDA4AF"))
            visibility = View.GONE
            setPadding(0, 0, 0, 16)
        }
        container.addView(errorText)

        // Statistics Container
        statsContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        container.addView(statsContainer)

        // Timeline Section Title
        val timelineTitle = TextView(this).apply {
            text = "CHRONOLOGICAL OBSERVATION TIMELINE (~15 MIN)"
            textSize = 11f
            setTextColor(Color.parseColor("#64748B"))
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 24, 0, 12)
        }
        container.addView(timelineTitle)

        // Timeline Container
        timelineContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        container.addView(timelineContainer)

        root.addView(container)
        setContentView(root)
    }

    private fun loadRoadmap() {
        progressBar.visibility = View.VISIBLE
        errorText.visibility = View.GONE

        lifecycleScope.launch {
            val result = apiClient.getMovementRoadmap("2026-09-05")
            progressBar.visibility = View.GONE

            if (result.isSuccess) {
                val roadmap = result.getOrThrow()
                renderRoadmap(roadmap)
            } else {
                errorText.text = "Failed to load roadmap: ${result.exceptionOrNull()?.message}"
                errorText.visibility = View.VISIBLE
            }
        }
    }

    private fun renderRoadmap(roadmap: MobileRoadmapResponse) {
        statsContainer.removeAllViews()
        timelineContainer.removeAllViews()

        // 1. Render Statistics Card
        val statsCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 16) }
            layoutParams = params
        }

        val s = roadmap.statistics
        val accStr = s.averageAccuracy?.let { "±%.1fm".format(it) } ?: "N/A"
        addStatRow(statsCard, "Total Discrete Observations", "${s.totalObservations} points recorded")
        addStatRow(statsCard, "Sampling Cadence", "Approximately 15 minutes")
        addStatRow(statsCard, "First Recorded Point", s.monitoringStart ?: "—")
        addStatRow(statsCard, "Last Recorded Point", s.monitoringEnd ?: "—")
        addStatRow(statsCard, "Average Accuracy", accStr)

        statsContainer.addView(statsCard)

        // 2. Render Timeline Points
        if (roadmap.observations.isEmpty()) {
            val empty = TextView(this).apply {
                text = "No observations recorded for this date."
                setTextColor(Color.parseColor("#94A3B8"))
                textSize = 13f
            }
            timelineContainer.addView(empty)
            return
        }

        val total = roadmap.observations.size
        for ((idx, obs) in roadmap.observations.withIndex()) {
            val isStart = idx == 0
            val isEnd = idx == total - 1 && total > 1
            val letter = ('A'.code + idx).toChar().toString()

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

            // Header line: Point A • 09:00:00 • Source Tag
            val headerRow = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }

            val badgeText = when {
                isStart -> "Point $letter (START)"
                isEnd -> "Point $letter (END)"
                else -> "Point $letter"
            }
            val titleView = TextView(this).apply {
                text = badgeText
                textSize = 14f
                setTextColor(
                    when {
                        isStart -> Color.parseColor("#34D399")
                        isEnd -> Color.parseColor("#F43F5E")
                        else -> Color.parseColor("#38BDF8")
                    }
                )
                typeface = Typeface.DEFAULT_BOLD
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }

            val sourceView = TextView(this).apply {
                text = obs.source
                textSize = 10f
                setTextColor(Color.WHITE)
                typeface = Typeface.DEFAULT_BOLD
                setBackgroundColor(
                    if (obs.source == "PATIENT_GPS") Color.parseColor("#059669") else Color.parseColor("#4F46E5")
                )
                setPadding(12, 4, 12, 4)
            }

            headerRow.addView(titleView)
            headerRow.addView(sourceView)
            itemCard.addView(headerRow)

            // Coordinates & Accuracy
            val coordView = TextView(this).apply {
                val acc = obs.accuracy?.let { "±%.1fm".format(it) } ?: "N/A"
                text = "📍 Lat: %.4f, Lng: %.4f • Acc: %s".format(obs.latitude, obs.longitude, acc)
                textSize = 12f
                setTextColor(Color.WHITE)
                setPadding(0, 6, 0, 4)
            }
            val timeView = TextView(this).apply {
                text = "Recorded At: ${obs.recordedAt}"
                textSize = 11f
                setTextColor(Color.parseColor("#94A3B8"))
            }

            itemCard.addView(coordView)
            itemCard.addView(timeView)
            timelineContainer.addView(itemCard)
        }
    }

    private fun addStatRow(parent: LinearLayout, label: String, value: String) {
        val labelView = TextView(this).apply {
            text = label
            textSize = 11f
            setTextColor(Color.parseColor("#94A3B8"))
        }
        val valueView = TextView(this).apply {
            text = value
            textSize = 13f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 2, 0, 10)
        }
        parent.addView(labelView)
        parent.addView(valueView)
    }
}
