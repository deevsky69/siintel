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
        // 2.0.0: dua APK menjadi satu. 2.1.0: kelurahan pada laporan. 2.2.0: seluruh
        // tampilan dipindahkan ke Jetpack Compose (7 Oktober 2026).
        versionCode = 4
        versionName = "2.2.0"

        // Alamat API dibaca dari sini, bukan ditanam di kode: alamat produksi kelak
        // berbeda, dan pengujian lokal memakai alamat lain lagi
        // (`gradle assembleRelease -PapiBase=https://…`).
        //
        // BAWAANNYA PERNAH `:8998`, dan itu menjadi cacat yang membuat APK hasil bangun
        // TIDAK DAPAT TERSAMBUNG SAMA SEKALI: port itu bergantung pada penerusan port di
        // router, dan penerusan itu sudah tidak aktif. Demo kini dilayani pada 443 lewat
        // nama domainnya. Alamat bawaan yang mati adalah kegagalan paling mahal pada
        // sebuah APK — ia baru ketahuan setelah dipasang di ponsel orang.
        buildConfigField("String", "API_BASE", "\"${project.findProperty("apiBase") ?: "https://siintel.awansurya.com"}\"")
    }

    buildFeatures {
        buildConfig = true
        compose = true
    }

    // Kotlin 1.9.23 ↔ Compose Compiler 1.5.11 (pasangan resmi; pada Kotlin 2.x pasangan ini
    // diganti plugin `org.jetbrains.kotlin.plugin.compose`).
    composeOptions { kotlinCompilerExtensionVersion = "1.5.11" }

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
    // Jetpack Compose — keputusan pemilik proyek 7 Oktober 2026: tampilan dipindahkan dari
    // XML ke Compose, layar demi layar, dimulai dari layar muka. BOM menyamakan versi
    // seluruh artefak Compose.
    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.0")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.core:core-ktx:1.13.1")
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
