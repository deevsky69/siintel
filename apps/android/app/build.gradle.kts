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
        // Naik ke 2.0.0 karena aplikasinya berubah bentuk, bukan bertambah fitur: dua APK
        // menjadi satu, dan layar mukanya kini bukan formulir laporan.
        versionCode = 2
        versionName = "2.0.0"

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

    testOptions {
        unitTests {
            // Panggilan ke kerangka Android yang tidak diuji mengembalikan nilai bawaan
            // alih-alih melemparkan galat. Yang diuji di sini adalah lapisan HTTP dan
            // penguraian JSON — keduanya Kotlin murni.
            isReturnDefaultValues = true
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
    // Penyimpanan token petugas. Dipakai daripada SharedPreferences biasa karena token
    // adalah kredensial: pada ponsel yang di-root, preferensi biasa terbaca aplikasi lain.
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    // Tidak ada pustaka lokasi pihak ketiga. `play-services-location` lebih nyaman, tetapi
    // ia menuntut Google Play Services — yang tidak ada pada sebagian perangkat, tidak ada
    // pada emulator baku, dan menambah ketergantungan pada satu perusahaan untuk aplikasi
    // yang dipasang warga. `LocationManager` bawaan sudah cukup untuk satu kali pengambilan.

    testImplementation("junit:junit:4.13.2")
    // org.json sungguhan untuk unit test JVM. Tanpa ini, `android.jar` tiruan milik Gradle
    // mengembalikan nilai bawaan dari tiap panggilan JSON, dan test parsing akan lulus tanpa
    // benar-benar mengurai apa pun.
    testImplementation("org.json:json:20240303")
}
