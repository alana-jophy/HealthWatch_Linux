package com.healthwatch

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.healthwatch.data.local.SessionManager
import com.healthwatch.ui.DashboardActivity
import com.healthwatch.ui.LoginActivity

/**
 * HealthWatch Mobile Main Entry Point.
 * Inspects authentication session and routes to Dashboard or Login.
 */
class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val sessionManager = SessionManager(this)

        if (sessionManager.isLoggedIn()) {
            startActivity(Intent(this, DashboardActivity::class.java))
        } else {
            startActivity(Intent(this, LoginActivity::class.java))
        }
        finish()
    }
}
