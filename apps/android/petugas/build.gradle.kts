plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "id.polri.jaksel.presisi"
    compileSdk = 34

    defaultConfig {
        // applicationId berbeda dari aplikasi warga supaya keduanya dapat terpasang
        // berdampingan di satu ponsel — berguna saat paparan.
        applicationId = "id.polri.jaksel.presisi"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        buildConfigField(
            "String",
            "API_BASE",
            "\"${project.findProperty("apiBase") ?: "https://siintel.awansurya.com:8998"}\"",
        )
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
    // Penyimpanan token terenkripsi. Dipakai daripada SharedPreferences biasa karena
    // token akses adalah kredensial: pada ponsel yang di-root, preferensi biasa terbaca
    // aplikasi lain.
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
}
