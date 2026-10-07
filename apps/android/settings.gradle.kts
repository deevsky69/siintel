// PRESISI — satu aplikasi Android untuk warga dan petugas (PHASE 17, TASK 170–172).
//
// Terpisah dari build web/API dengan sengaja: ia berbicara ke API yang sama lewat HTTP,
// tidak berbagi kode, dan tidak boleh ikut menggagalkan CI keduanya bila SDK Android tidak
// terpasang di mesin yang menjalankannya.
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    // Mengunduh JDK yang diminta `gradle/gradle-daemon-jvm.properties` bila mesin ini tidak
    // memilikinya (7 Oktober 2026). Tanpa ini, mesin yang hanya punya Java 25 bawaan
    // Android Studio gagal sync karena Gradle 8.x tidak berjalan di atas Java 25.
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "Presisi"

// Satu modul. Sampai 8 September 2026 ada dua — `app` untuk warga dan `petugas` untuk
// personel — dan keduanya disatukan atas permintaan pemilik proyek: satu tautan
// pemasangan, satu ikon, satu hal yang harus dijelaskan saat paparan.
include(":app")
