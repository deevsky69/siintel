package id.polri.jaksel.laporpresisi

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import org.json.JSONArray
import org.json.JSONObject

/**
 * Tiket laporan beserta kode klaimnya, tersimpan di ponsel pelapor.
 *
 * ## Mengapa terenkripsi
 *
 * Kode klaim adalah kredensial: ia satu-satunya bukti bahwa sebuah laporan milik pemegang
 * ponsel ini. Menyimpannya sebagai preferensi biasa berarti aplikasi lain pada perangkat
 * yang sudah di-root — atau cadangan yang tersalin ke tempat lain — dapat membacanya, dan
 * dengan itu membaca status laporan orang tersebut.
 *
 * Skemanya sama persis dengan penyimpanan sesi petugas: kalau kredensial petugas pantas
 * dienkripsi, kredensial warga pantas juga.
 *
 * ## Mengapa di ponsel, bukan di server
 *
 * Karena server sengaja tidak menyimpan identitas pelapor sama sekali. Tidak ada akun,
 * tidak ada nomor telepon, tidak ada apa pun yang dapat dipakai mengembalikan kode yang
 * hilang. Itu harga yang dibayar untuk kanal yang benar-benar tanpa identitas — dan
 * layar menyatakannya kepada pelapor, bukan menyembunyikannya.
 */
class TiketStore(context: Context) {

    /** Satu laporan yang pernah dikirim dari ponsel ini. */
    data class Tiket(val code: String, val claimToken: String)

    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "tiket-presisi",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    /** Seluruh tiket, terbaru lebih dahulu. */
    fun semua(): List<Tiket> {
        val raw = prefs.getString(KEY, null) ?: return emptyList()
        return runCatching {
            val rows = JSONArray(raw)
            (0 until rows.length()).map { index ->
                val row = rows.getJSONObject(index)
                Tiket(row.getString("code"), row.getString("token"))
            }
        }.getOrDefault(emptyList())
    }

    /**
     * Menyimpan satu tiket baru di paling depan.
     *
     * Hanya [MAX] terakhir yang disimpan. Bukan penghematan ruang: daftar yang tumbuh
     * selamanya menyimpan kredensial laporan bertahun lalu yang sudah tidak berguna, dan
     * kredensial yang tidak lagi berguna sebaiknya tidak lagi ada.
     */
    fun simpan(tiket: Tiket) {
        val disimpan = (listOf(tiket) + semua().filterNot { it.code == tiket.code }).take(MAX)
        val rows = JSONArray()
        for (row in disimpan) {
            rows.put(JSONObject().put("code", row.code).put("token", row.claimToken))
        }
        prefs.edit().putString(KEY, rows.toString()).apply()
    }

    fun hapus(code: String) {
        val rows = JSONArray()
        for (row in semua().filterNot { it.code == code }) {
            rows.put(JSONObject().put("code", row.code).put("token", row.claimToken))
        }
        prefs.edit().putString(KEY, rows.toString()).apply()
    }

    private companion object {
        const val KEY = "tiket"
        const val MAX = 20
    }
}
