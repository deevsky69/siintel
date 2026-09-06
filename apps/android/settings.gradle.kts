// LAPOR PRESISI — kanal laporan masyarakat untuk Android (PHASE 17, TASK 170).
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
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "LaporPresisi"
include(":app")
include(":petugas")
