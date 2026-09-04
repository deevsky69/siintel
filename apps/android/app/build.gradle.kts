plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "id.polri.jaksel.laporpresisi"
    compileSdk = 34

    defaultConfig {
        applicationId = "id.polri.jaksel.laporpresisi"
        // 24 = Android 7.0. Dipilih rendah dengan sengaja: kanal laporan masyarakat harus
        // dapat dipasang pada ponsel murah yang sudah lama, bukan hanya pada ponsel baru.
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        // Alamat API dibaca dari sini, bukan ditanam di kode: server demo memakai port
        // tidak lazim, dan alamat produksi kelak berbeda lagi.
        buildConfigField("String", "API_BASE", "\"${project.findProperty("apiBase") ?: "https://siintel.awansurya.com:8998"}\"")
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Ditandatangani kunci debug supaya `assembleRelease` menghasilkan APK yang
            // benar-benar dapat dipasang. Untuk penyebaran nyata, ganti dengan kunci
            // rilis milik satuan — JANGAN menaruh keystore itu di repository.
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
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
}
