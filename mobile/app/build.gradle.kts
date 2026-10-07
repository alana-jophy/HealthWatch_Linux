plugins {
    id("com.android.application")
}

android {
    namespace = "com.healthwatch"
    compileSdk = 34

    val resolvedVersion: String = run {
        var ver = (project.findProperty("APP_VERSION") as? String)
            ?: System.getenv("APP_VERSION")
        if (ver.isNullOrBlank()) {
            val rootEnvProd = file("../../.env.production")
            val rootEnv = file("../../.env")
            val targetEnv = if (rootEnvProd.exists()) rootEnvProd else if (rootEnv.exists()) rootEnv else null
            if (targetEnv != null) {
                val match = Regex("""^APP_VERSION\s*=\s*["']?([^"'\r\n]+)["']?""", RegexOption.MULTILINE).find(targetEnv.readText())
                if (match != null) {
                    ver = match.groupValues[1].trim()
                }
            }
        }
        ver?.takeIf { it.isNotBlank() } ?: "1.0.0"
    }

    val computedVersionCode: Int = run {
        try {
            val nums = resolvedVersion.split(".").map { it.filter { ch -> ch.isDigit() }.toIntOrNull() ?: 0 }
            when (nums.size) {
                1 -> nums[0]
                2 -> nums[0] * 10000 + nums[1] * 100
                else -> nums[0] * 10000 + nums[1] * 100 + nums[2]
            }
        } catch (_: Exception) {
            1
        }
    }

    defaultConfig {
        applicationId = "com.healthwatch"
        minSdk = 24
        targetSdk = 34
        versionCode = computedVersionCode
        versionName = resolvedVersion

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        val rawDomain: String = (project.findProperty("SERVER_DOMAIN") as? String)
            ?: System.getenv("SERVER_DOMAIN")
            ?: System.getenv("DOMAIN_NAME")
            ?: "http://192.168.0.119:8000"

        val serverUrl = when {
            rawDomain.startsWith("http://") || rawDomain.startsWith("https://") -> rawDomain
            System.getenv("ENABLE_HTTPS") == "true" -> "https://$rawDomain"
            else -> "http://$rawDomain"
        }.trimEnd('/')

        buildConfigField("String", "DEFAULT_SERVER_URL", "\"$serverUrl\"")
        buildConfigField("String", "APP_VERSION_NAME", "\"$resolvedVersion\"")
    }

    signingConfigs {
        getByName("debug") {
            enableV1Signing = true
            enableV2Signing = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        viewBinding = false
        buildConfig = true
    }

    applicationVariants.all {
        val variant = this
        variant.outputs.all {
            val output = this as? com.android.build.gradle.internal.api.BaseVariantOutputImpl
            val vName = variant.versionName ?: resolvedVersion
            output?.outputFileName = "HealthWatch-v${vName}.apk"
        }
    }
}

dependencies {
    implementation("androidx.core:core:1.13.1")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.lifecycle:lifecycle-viewmodel:2.7.0")
    implementation("androidx.lifecycle:lifecycle-livedata:2.7.0")
    implementation("androidx.activity:activity:1.9.0")

    // Google Play Services Location (Official Location APIs)
    implementation("com.google.android.gms:play-services-location:21.2.0")

    // Networking & Serialization
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.google.code.gson:gson:2.10.1")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.mockito:mockito-core:5.11.0")
}
