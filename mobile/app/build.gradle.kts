plugins {
    id("com.android.application")
}

android {
    namespace = "com.healthwatch"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.healthwatch"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

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
