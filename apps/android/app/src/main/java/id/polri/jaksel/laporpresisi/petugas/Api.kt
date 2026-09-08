package id.polri.jaksel.laporpresisi.petugas

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Sambungan ke API PREDIKSI PRESISI untuk petugas.
 *
 * Berbeda dari aplikasi warga, seluruh permintaan di sini **membawa token**. Tokennya
 * disimpan terenkripsi di ponsel ([TokenStore]) dan tidak pernah ditulis ke log.
 *
 * Endpoint yang dipakai:
 *
 * ```text
 * POST /api/v1/auth/login     menukar kredensial dengan token
 * POST /api/v1/auth/refresh   menukar refresh token dengan access token baru
 * GET  /api/v1/auth/me        identitas dan kewenangan efektif
 * GET  /api/v1/notifications  antrean pekerjaan menurut kewenangan itu
 * POST /api/v1/citizen-reports/{kode}/status   menriase satu laporan warga
 * ```
 *
 * ## Dua token, dan mengapa keduanya diperlukan
 *
 * Access token berumur **15 menit**; refresh token berumur **7 hari**. Tanpa yang kedua,
 * petugas harus mengetik ulang kata sandinya setiap seperempat jam — di lapangan itu berarti
 * aplikasinya tidak dipakai sama sekali.
 *
 * Refresh token **tidak dikirim pada badan respons**. Server menaruhnya pada cookie
 * `httpOnly` bernama [REFRESH_COOKIE] dengan `path=/api/v1/auth`, karena konsumen utamanya
 * adalah peramban, dan cookie `httpOnly` tidak terbaca JavaScript. Ponsel tidak punya
 * peramban di sini, jadi [login] membaca cookie itu dari header `Set-Cookie` dan
 * [refresh] mengirimkannya kembali sebagai header `Cookie`. Kontrak API tidak berubah:
 * yang berubah hanya siapa yang menyimpan cookie-nya.
 *
 * **Kewenangan tidak diperiksa di sini.** Aplikasi hanya menampilkan apa yang dikirim
 * server; server yang memutuskan apa yang boleh dilihat. Memeriksanya di ponsel akan
 * terlihat seperti pengaman padahal hanya kenyamanan — dan yang terlihat seperti pengaman
 * cenderung dipercaya (CLAUDE.md §15, §21).
 */
object Api {

    private const val TIMEOUT_MS = 20_000

    /** Nama cookie refresh milik server — lihat `auth.py:REFRESH_COOKIE`. */
    internal const val REFRESH_COOKIE = "predpol_refresh"

    class Failure(val readable: String, val unauthorized: Boolean = false) : Exception(readable)

    /**
     * Sepasang token hasil [login]. Dinamai begini, bukan `Session`, supaya tidak tertukar
     * dengan kelas [Session] yang memegang aturan pembaruannya.
     */
    data class Credentials(val accessToken: String, val refreshToken: String?)

    data class Profile(val name: String, val role: String, val permissions: List<String>)

    data class QueueItem(val code: String, val headline: String, val detail: String)

    data class Queue(
        val kind: String,
        val title: String,
        val action: String,
        val total: Int,
        val items: List<QueueItem>,
    )

    data class Feed(val role: String, val total: Int, val queues: List<Queue>)

    /** Badan respons beserta headernya — headernya diperlukan hanya untuk `Set-Cookie`. */
    internal class Reply(val body: String, val headers: Map<String, List<String>>)

    suspend fun login(base: String, username: String, password: String): Credentials =
        withContext(Dispatchers.IO) {
            val payload = JSONObject()
                .put("username", username)
                .put("password", password)
                .toString()
            val reply = call(base, "/api/v1/auth/login", "POST", payload, null, null)
            Credentials(
                accessToken = JSONObject(reply.body).getString("access_token"),
                refreshToken = refreshTokenFrom(reply.headers),
            )
        }

    /**
     * Menukar refresh token dengan access token baru.
     *
     * Refresh token **tidak diputar** oleh server: respons `/auth/refresh` tidak membawa
     * `Set-Cookie`, sehingga token yang sama dipakai sampai umurnya habis. Kegagalan dengan
     * `401` berarti masa tujuh hari itu sudah lewat dan petugas memang harus masuk kembali.
     */
    suspend fun refresh(base: String, refreshToken: String): String = withContext(Dispatchers.IO) {
        val reply = call(
            base,
            "/api/v1/auth/refresh",
            "POST",
            null,
            null,
            "$REFRESH_COOKIE=$refreshToken",
        )
        JSONObject(reply.body).getString("access_token")
    }

    suspend fun profile(base: String, token: String): Profile = withContext(Dispatchers.IO) {
        parseProfile(call(base, "/api/v1/auth/me", "GET", null, token, null).body)
    }

    /**
     * Menandai satu laporan warga sudah diverifikasi.
     *
     * Satu-satunya tindakan yang dapat dilakukan dari ponsel, dan pembatasannya disengaja.
     * Verifikasi adalah pernyataan bahwa laporan itu layak ditindaklanjuti — keputusan yang
     * dapat diambil petugas yang baru saja melihat tempatnya. Meneruskan, menugaskan, dan
     * menutup laporan menuntut konteks yang hanya ada di meja kerja, dan menyediakannya di
     * layar sempit mengundang keputusan yang diambil terlalu cepat.
     *
     * Server tetap yang memutuskan boleh atau tidak: kewenangan `citizen_report:write` dan
     * cakupan wilayah diperiksa di sana, dan setiap perpindahan status ditulis ke audit.
     */
    suspend fun verifyReport(base: String, token: String, code: String): String =
        withContext(Dispatchers.IO) {
            val payload = JSONObject().put("status", "VERIFIED").toString()
            val reply = call(base, "/api/v1/citizen-reports/$code/status", "POST", payload, token, null)
            JSONObject(reply.body).optString("status")
        }

    suspend fun notifications(base: String, token: String): Feed = withContext(Dispatchers.IO) {
        parseFeed(call(base, "/api/v1/notifications", "GET", null, token, null).body)
    }

    internal fun parseProfile(body: String): Profile {
        val json = JSONObject(body)
        return Profile(
            name = json.text("full_name").ifBlank { json.getString("username") },
            role = json.text("role"),
            permissions = json.optJSONArray("permissions").toStringList(),
        )
    }

    internal fun parseFeed(body: String): Feed {
        val json = JSONObject(body)
        val groups = json.getJSONArray("groups")
        return Feed(
            role = json.text("role"),
            total = json.optInt("total"),
            queues = (0 until groups.length()).map { index ->
                val group = groups.getJSONObject(index)
                val items = group.getJSONArray("items")
                Queue(
                    kind = group.getString("kind"),
                    title = group.getString("title"),
                    action = group.text("action"),
                    total = group.optInt("total"),
                    items = (0 until items.length()).map {
                        val item = items.getJSONObject(it)
                        QueueItem(item.text("code"), item.text("headline"), item.text("detail"))
                    },
                )
            },
        )
    }

    /**
     * Memungut refresh token dari header `Set-Cookie`.
     *
     * Nama header dibandingkan tanpa peduli huruf besar-kecil karena HTTP memang begitu, dan
     * atribut cookie (`Path`, `HttpOnly`, `Max-Age`) dibuang: yang dipakai hanya nilainya.
     * Tanda kutip di sekeliling nilai dilucuti, lalu nilai kosong diperlakukan sebagai tidak
     * ada: `predpol_refresh=""; Max-Age=0` adalah cara server **menghapus** cookie-nya
     * (itulah yang dikirim `/auth/logout`), bukan token yang sah.
     */
    internal fun refreshTokenFrom(headers: Map<String, List<String>>): String? {
        val lines = headers.entries.flatMap { entry ->
            // `headerFields` milik JDK menyimpan baris status HTTP dengan kunci null.
            val name: String? = entry.key
            if (name != null && name.equals("Set-Cookie", ignoreCase = true)) entry.value else emptyList()
        }
        return lines.firstNotNullOfOrNull { line ->
            val pair = line.substringBefore(';').trim()
            val name = pair.substringBefore('=').trim()
            val value = pair.substringAfter('=', "").trim().trim('"')
            if (name == REFRESH_COOKIE && value.isNotEmpty()) value else null
        }
    }

    private fun call(
        base: String,
        path: String,
        method: String,
        body: String?,
        token: String?,
        cookie: String?,
    ): Reply {
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            requestMethod = method
            setRequestProperty("Accept", "application/json")
            if (token != null) setRequestProperty("Authorization", "Bearer $token")
            if (cookie != null) setRequestProperty("Cookie", cookie)
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }

        try {
            if (body != null) {
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()

            if (code in 200..299) return Reply(text, connection.headerFields.orEmpty())

            // 401 dibedakan dari galat lain: ia berarti sesi berakhir dan pengguna harus
            // masuk kembali, bukan bahwa ada sesuatu yang rusak.
            throw Failure(readable(text, code), unauthorized = code == 401)
        } catch (failure: Failure) {
            throw failure
        } catch (_: Exception) {
            throw Failure("Tidak dapat menghubungi server. Periksa sambungan internet Anda.")
        } finally {
            connection.disconnect()
        }
    }

    internal fun readable(body: String, code: Int): String = try {
        JSONObject(body).getJSONObject("error").getString("message")
    } catch (_: Exception) {
        when (code) {
            401 -> "Nama pengguna atau kata sandi salah."
            403 -> "Akun Anda tidak memiliki kewenangan untuk ini."
            in 500..599 -> "Server sedang bermasalah. Coba lagi beberapa saat lagi."
            else -> "Permintaan gagal ($code)."
        }
    }

    /**
     * Nilai teks dari sebuah field, dengan `null` JSON dibaca sebagai kosong.
     *
     * **Jangan menggantinya dengan `optString`.** Keduanya berbeda justru pada kasus yang
     * paling sering terjadi di sini: untuk `{"full_name": null}`, `optString` milik Android
     * mengembalikan teks `"null"` — empat huruf yang lalu tergambar di layar sebagai nama
     * petugas. Implementasi `org.json` di JVM mengembalikan teks kosong untuk kasus yang
     * sama, sehingga unit test **tidak dapat menangkap perbedaan ini**; ia hanya terlihat
     * saat aplikasi berjalan di Android.
     */
    private fun JSONObject.text(name: String): String {
        val value = opt(name)
        return if (value == null || value === JSONObject.NULL) "" else value.toString()
    }

    private fun JSONArray?.toStringList(): List<String> =
        if (this == null) emptyList() else (0 until length()).map { getString(it) }
}
