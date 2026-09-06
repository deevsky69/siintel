package id.polri.jaksel.presisi

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
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
 * GET  /api/v1/auth/me        identitas dan kewenangan efektif
 * GET  /api/v1/notifications  antrean pekerjaan menurut kewenangan itu
 * ```
 *
 * **Kewenangan tidak diperiksa di sini.** Aplikasi hanya menampilkan apa yang dikirim
 * server; server yang memutuskan apa yang boleh dilihat. Memeriksanya di ponsel akan
 * terlihat seperti pengaman padahal hanya kenyamanan — dan yang terlihat seperti pengaman
 * cenderung dipercaya (CLAUDE.md §15, §21).
 */
object Api {

    private const val TIMEOUT_MS = 20_000

    class Failure(val readable: String, val unauthorized: Boolean = false) : Exception(readable)

    data class Session(val accessToken: String, val refreshToken: String?)

    data class Profile(val name: String, val role: String, val permissions: List<String>)

    data class QueueItem(val headline: String, val detail: String)

    data class Queue(
        val kind: String,
        val title: String,
        val action: String,
        val total: Int,
        val items: List<QueueItem>,
    )

    data class Feed(val role: String, val total: Int, val queues: List<Queue>)

    suspend fun login(base: String, username: String, password: String): Session =
        withContext(Dispatchers.IO) {
            val payload = JSONObject()
                .put("username", username)
                .put("password", password)
                .toString()
            val json = JSONObject(call(base, "/api/v1/auth/login", "POST", payload, null))
            Session(
                accessToken = json.getString("access_token"),
                refreshToken = json.optString("refresh_token").ifBlank { null },
            )
        }

    suspend fun profile(base: String, token: String): Profile = withContext(Dispatchers.IO) {
        val json = JSONObject(call(base, "/api/v1/auth/me", "GET", null, token))
        Profile(
            name = json.optString("full_name").ifBlank { json.getString("username") },
            role = json.optString("role"),
            permissions = json.optJSONArray("permissions").toStringList(),
        )
    }

    suspend fun notifications(base: String, token: String): Feed = withContext(Dispatchers.IO) {
        val json = JSONObject(call(base, "/api/v1/notifications", "GET", null, token))
        val groups = json.getJSONArray("groups")
        Feed(
            role = json.optString("role"),
            total = json.optInt("total"),
            queues = (0 until groups.length()).map { index ->
                val group = groups.getJSONObject(index)
                val items = group.getJSONArray("items")
                Queue(
                    kind = group.getString("kind"),
                    title = group.getString("title"),
                    action = group.optString("action"),
                    total = group.optInt("total"),
                    items = (0 until items.length()).map {
                        val item = items.getJSONObject(it)
                        QueueItem(item.optString("headline"), item.optString("detail"))
                    },
                )
            },
        )
    }

    private fun call(base: String, path: String, method: String, body: String?, token: String?): String {
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            requestMethod = method
            setRequestProperty("Accept", "application/json")
            if (token != null) setRequestProperty("Authorization", "Bearer $token")
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

            if (code in 200..299) return text

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

    private fun readable(body: String, code: Int): String = try {
        JSONObject(body).getJSONObject("error").getString("message")
    } catch (_: Exception) {
        when (code) {
            401 -> "Nama pengguna atau kata sandi salah."
            403 -> "Akun Anda tidak memiliki kewenangan untuk ini."
            in 500..599 -> "Server sedang bermasalah. Coba lagi beberapa saat lagi."
            else -> "Permintaan gagal ($code)."
        }
    }

    private fun org.json.JSONArray?.toStringList(): List<String> =
        if (this == null) emptyList() else (0 until length()).map { getString(it) }
}
