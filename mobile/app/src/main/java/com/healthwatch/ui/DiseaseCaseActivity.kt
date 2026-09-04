package com.healthwatch.ui

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.healthwatch.data.api.HealthWatchApiClient
import com.healthwatch.data.local.SessionManager
import com.healthwatch.data.model.DiseaseCase
import kotlinx.coroutines.launch

class DiseaseCaseActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient
    private lateinit var contentContainer: LinearLayout
    private lateinit var progressBar: ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)

        buildUi()
        loadCaseData()
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
            text = "My Disease Case"
            textSize = 22f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 16, 0, 8)
        }
        container.addView(headerTitle)

        progressBar = ProgressBar(this).apply {
            visibility = View.VISIBLE
            setPadding(0, 32, 0, 32)
        }
        container.addView(progressBar)

        contentContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        container.addView(contentContainer)

        root.addView(container)
        setContentView(root)
    }

    private fun loadCaseData() {
        lifecycleScope.launch {
            val result = apiClient.getDiseaseCases()
            progressBar.visibility = View.GONE
            contentContainer.visibility = View.VISIBLE

            if (result.isSuccess) {
                val cases = result.getOrThrow()
                if (cases.isNotEmpty()) {
                    renderCaseDetails(cases[0])
                } else {
                    renderEmptyCase()
                }
            } else {
                val errorView = TextView(this@DiseaseCaseActivity).apply {
                    text = "Failed to load clinical case: ${result.exceptionOrNull()?.message}"
                    setTextColor(Color.parseColor("#FDA4AF"))
                    textSize = 13f
                }
                contentContainer.addView(errorView)
            }
        }
    }

    private fun renderEmptyCase() {
        val view = TextView(this).apply {
            text = "No active clinical disease case registered for this patient profile."
            setTextColor(Color.parseColor("#94A3B8"))
            textSize = 14f
            setPadding(0, 24, 0, 0)
        }
        contentContainer.addView(view)
    }

    private fun renderCaseDetails(case: DiseaseCase) {
        contentContainer.removeAllViews()

        // Card 1: Clinical Diagnosis
        val diagCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 20) }
            layoutParams = params
        }

        val diseaseName = TextView(this).apply {
            text = case.disease?.name ?: "Dengue Fever"
            textSize = 20f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
        }
        val diseaseCode = TextView(this).apply {
            text = "CODE: ${case.disease?.code ?: "DENGUE-01"} • ${case.disease?.contagionType ?: "CONTAGIOUS"}"
            textSize = 12f
            setTextColor(Color.parseColor("#38BDF8"))
            setPadding(0, 4, 0, 16)
        }
        diagCard.addView(diseaseName)
        diagCard.addView(diseaseCode)

        // Status Badge
        val statusBadge = TextView(this).apply {
            text = "CASE STATUS: ${case.caseStatus}"
            textSize = 12f
            setTextColor(Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            setBackgroundColor(
                when (case.caseStatus) {
                    "CONFIRMED" -> Color.parseColor("#E11D48") // Red
                    "RECOVERED" -> Color.parseColor("#059669") // Green
                    else -> Color.parseColor("#D97706") // Amber
                }
            )
            setPadding(16, 8, 16, 8)
        }
        diagCard.addView(statusBadge)
        contentContainer.addView(diagCard)

        // Card 2: Epidemiological Metadata
        val metaCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 20) }
            layoutParams = params
        }

        addMetaRow(metaCard, "Diagnosis Date", case.diagnosisDate)
        addMetaRow(metaCard, "Severity Classification", case.severity)
        addMetaRow(metaCard, "Surveillance Data Source", case.source ?: "SIMULATED")
        addMetaRow(metaCard, "Clinical Notes", case.clinicalNotes ?: "Patient presenting with acute vector-borne symptoms under isolation.")

        contentContainer.addView(metaCard)
    }

    private fun addMetaRow(parent: LinearLayout, label: String, value: String) {
        val labelView = TextView(this).apply {
            text = label
            textSize = 11f
            setTextColor(Color.parseColor("#94A3B8"))
        }
        val valueView = TextView(this).apply {
            text = value
            textSize = 13f
            setTextColor(Color.WHITE)
            setPadding(0, 2, 0, 12)
        }
        parent.addView(labelView)
        parent.addView(valueView)
    }
}
