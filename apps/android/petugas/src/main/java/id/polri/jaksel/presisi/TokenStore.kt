package id.polri.jaksel.presisi

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Penyimpanan token di ponsel.
 *
 * Memakai [EncryptedSharedPreferences], bukan preferensi biasa. Token akses adalah
 * kredensial: pada ponsel yang di-root, preferensi biasa dapat dibaca aplikasi lain, dan
 * token yang bocor memberi akses penuh atas nama petugas yang bersangkutan.
 *
 * **Kata sandi tidak pernah disimpan** — hanya token, dan token berumur pendek. Petugas
 * yang kehilangan ponselnya kehilangan sesi, bukan kata sandinya.
 */
class TokenStore(context: Context) {

    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "sesi-presisi",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var accessToken: String?
        get() = prefs.getString(KEY_ACCESS, null)
        set(value) = prefs.edit().apply {
            if (value == null) remove(KEY_ACCESS) else putString(KEY_ACCESS, value)
        }.apply()

    fun clear() = prefs.edit().clear().apply()

    private companion object {
        const val KEY_ACCESS = "access"
    }
}
