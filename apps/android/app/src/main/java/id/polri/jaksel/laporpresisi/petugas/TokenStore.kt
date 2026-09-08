package id.polri.jaksel.laporpresisi.petugas

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Penyimpanan token di ponsel.
 *
 * Memakai [EncryptedSharedPreferences], bukan preferensi biasa. Token adalah kredensial:
 * pada ponsel yang di-root, preferensi biasa dapat dibaca aplikasi lain, dan token yang
 * bocor memberi akses penuh atas nama petugas yang bersangkutan.
 *
 * Dua token disimpan, dengan umur yang jauh berbeda:
 *
 * - **access** — 15 menit, dibawa pada tiap permintaan;
 * - **refresh** — 7 hari, hanya dipakai untuk menukar access token yang kedaluwarsa.
 *
 * Refresh token jelas lebih berharga karena umurnya panjang. Ia disimpan karena tanpanya
 * petugas harus mengetik ulang kata sandinya tiap seperempat jam, dan aplikasi yang menuntut
 * itu tidak akan dipakai di lapangan. Pertukarannya disadari: satu kredensial berumur
 * seminggu di dalam penyimpanan terenkripsi, ditukar dengan kata sandi yang tidak perlu
 * diketik berulang di tempat terbuka.
 *
 * **Kata sandi tidak pernah disimpan.** Petugas yang kehilangan ponselnya kehilangan sesi,
 * bukan kata sandinya — dan [clear] menghapus keduanya sekaligus.
 */
class TokenStore(context: Context) : Tokens {

    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "sesi-presisi",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    override var accessToken: String?
        get() = prefs.getString(KEY_ACCESS, null)
        set(value) = write(KEY_ACCESS, value)

    override var refreshToken: String?
        get() = prefs.getString(KEY_REFRESH, null)
        set(value) = write(KEY_REFRESH, value)

    override fun clear() = prefs.edit().clear().apply()

    private fun write(key: String, value: String?) = prefs.edit().apply {
        if (value == null) remove(key) else putString(key, value)
    }.apply()

    private companion object {
        const val KEY_ACCESS = "access"
        const val KEY_REFRESH = "refresh"
    }
}
