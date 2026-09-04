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
import com.healthwatch.data.model.PatientProfile
import kotlinx.coroutines.launch

class ProfileActivity : AppCompatActivity() {

    private lateinit var sessionManager: SessionManager
    private lateinit var apiClient: HealthWatchApiClient
    private lateinit var contentContainer: LinearLayout
    private lateinit var progressBar: ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager(this)
        apiClient = HealthWatchApiClient(sessionManager)

        buildUi()
        loadProfile()
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
            text = "My Patient Profile"
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

    private fun loadProfile() {
        lifecycleScope.launch {
            val result = apiClient.getPatientProfile()
            progressBar.visibility = View.GONE
            contentContainer.visibility = View.VISIBLE

            if (result.isSuccess) {
                val profile = result.getOrThrow()
                renderProfileDetails(profile)
            } else {
                val errorView = TextView(this@ProfileActivity).apply {
                    text = "Failed to load patient profile: ${result.exceptionOrNull()?.message}"
                    setTextColor(Color.parseColor("#FDA4AF"))
                    textSize = 13f
                }
                contentContainer.addView(errorView)
            }
        }
    }

    private fun renderProfileDetails(profile: PatientProfile) {
        contentContainer.removeAllViews()

        // Card 1: Identity
        val identityCard = createInfoCard("IDENTIFICATION & DEMOGRAPHICS", listOf(
            "Pseudo Identifier" to profile.pseudoId,
            "Full Legal Name" to profile.fullName,
            "Age / Gender" to "${profile.age} Years • ${profile.gender}",
            "Contact Phone" to profile.contactNumber,
            "Residential Address" to profile.address
        ))
        contentContainer.addView(identityCard)

        // Card 2: Kerala Geographic Hierarchy
        val geoCard = createInfoCard("ASSIGNED SURVEILLANCE GEOGRAPHY", listOf(
            "District" to profile.districtName,
            "Local Body (Panchayat / Corp)" to profile.localBodyName,
            "Ward Number" to "Ward ${profile.wardNumber}",
            "Surveillance State" to "Kerala, India"
        ))
        contentContainer.addView(geoCard)
    }

    private fun createInfoCard(title: String, fields: List<Pair<String, String>>): View {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#1E293B"))
            setPadding(28, 24, 28, 24)
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 0, 0, 20) }
            layoutParams = params
        }

        val titleView = TextView(this).apply {
            text = title
            textSize = 11f
            setTextColor(Color.parseColor("#38BDF8"))
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 0, 0, 16)
        }
        card.addView(titleView)

        for ((label, value) in fields) {
            val labelView = TextView(this).apply {
                text = label
                textSize = 11f
                setTextColor(Color.parseColor("#94A3B8"))
            }
            val valueView = TextView(this).apply {
                text = value
                textSize = 14f
                setTextColor(Color.WHITE)
                typeface = Typeface.DEFAULT_BOLD
                setPadding(0, 2, 0, 12)
            }
            card.addView(labelView)
            card.addView(valueView)
        }

        return card
    }
}
