package id.polri.jaksel.laporpresisi

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Sambungan ke kanal publik PREDIKSI PRESISI.
 *
 * Memakai `HttpURLConnection` bawaan, bukan pustaka HTTP pihak ketiga. Alasannya bukan
 * kesederhanaan melainkan **ukuran dan kepercayaan**: aplikasi ini dipasang warga, dan tiap
 * pustaka tambahan adalah kode yang ikut dipasang tanpa mereka ketahui. Dua permintaan
 * sederhana tidak sepadan dengan itu.
 *
 * Dua endpoint yang dipakai, keduanya **tanpa autentikasi**:
 *
 * ```text
 * GET  /api/v1/public/report-options   pilihan kategori dan kecamatan
 * POST /api/v1/public/citizen-reports  mengirim laporan
 * ```
 *
 * Tidak ada token, tidak ada akun, dan tidak ada satu pun field identitas yang dikirim —
 * lihat [ReportDraft]. Backend menolak field yang tidak dikenalnya, sehingga menambahkan
 * satu di sini akan gagal dengan pesan yang jelas, bukan diam-diam tersimpan.
 */
object PublicApi {

    private const val TIMEOUT_MS = 20_000

    data class Options(
        val categories: List<String>,
        val areas: List<String>,
        val coordinateBasis: String,
    )

    data class Ticket(val code: String, val message: String)

    /** Kegagalan yang sudah diterjemahkan menjadi kalimat yang pantas dibaca warga. */
    class ApiFailure(val readable: String) : Exception(readable)

    suspend fun options(baseUrl: String): Options = withContext(Dispatchers.IO) {
        val body = get("$baseUrl/api/v1/public/report-options")
        val json = JSONObject(body)
        Options(
            categories = json.getJSONArray("categories").toStringList(),
            areas = json.getJSONArray("kecamatan").toStringList(),
            coordinateBasis = json.text("coordinate_basis"),
        )
    }

    suspend fun submit(baseUrl: String, draft: ReportDraft): Ticket = withContext(Dispatchers.IO) {
        val payload = JSONObject().apply {
            put("category", draft.category)
            put("kecamatan", draft.area)
            put("description", draft.story)
            // Field opsional hanya dikirim bila benar-benar diisi: backend menolak field
            // bernilai kosong, dan galat itu akan membingungkan pelapor yang justru tidak
            // mengisi apa-apa.
            if (draft.place.isNotBlank()) put("location_text", draft.place)
        }
        val body = post("$baseUrl/api/v1/public/citizen-reports", payload.toString())
        val json = JSONObject(body)
        Ticket(code = json.getString("ticket"), message = json.text("message"))
    }

    private fun get(url: String): String = call(url, null)

    private fun post(url: String, json: String): String = call(url, json)

    private fun call(url: String, json: String?): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            requestMethod = if (json == null) "GET" else "POST"
            setRequestProperty("Accept", "application/json")
            if (json != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }

        try {
            if (json != null) {
                connection.outputStream.use { it.write(json.toByteArray(Charsets.UTF_8)) }
            }

            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()

            if (code in 200..299) return text

            // Pesan dari backend diteruskan apa adanya bila ada: ia yang tahu apa yang
            // ditolak, dan menggantinya dengan kalimat umum menghilangkan satu-satunya
            // petunjuk yang dipunyai pelapor untuk memperbaikinya.
            throw ApiFailure(readableError(text, code))
        } catch (failure: ApiFailure) {
            throw failure
        } catch (_: Exception) {
            throw ApiFailure(
                "Laporan tidak dapat dikirim karena sistem sedang tidak dapat dihubungi. " +
                    "Untuk keadaan mendesak, hubungi 110."
            )
        } finally {
            connection.disconnect()
        }
    }

    private fun readableError(body: String, code: Int): String = try {
        JSONObject(body).getJSONObject("error").getString("message")
    } catch (_: Exception) {
        when (code) {
            429 -> "Terlalu banyak laporan dikirim dari jaringan ini dalam satu jam terakhir."
            in 500..599 -> "Sistem sedang bermasalah. Coba lagi beberapa saat lagi."
            else -> "Laporan tidak dapat dikirim. Periksa kembali isian Anda, lalu coba lagi."
        }
    }

    /**
     * Nilai teks dari sebuah field, dengan `null` JSON dibaca sebagai kosong.
     *
     * **Jangan menggantinya dengan `optString`.** Keduanya berbeda pada kasus yang justru
     * paling mungkin terjadi: untuk `{"message": null}`, `optString` milik Android
     * mengembalikan teks `"null"` — empat huruf yang lalu tergambar di layar sebagai pesan
     * untuk pelapor. Implementasi `org.json` di JVM mengembalikan teks kosong untuk kasus
     * yang sama, sehingga unit test **tidak dapat menangkap perbedaan ini**; ia hanya
     * terlihat saat aplikasi berjalan di Android.
     */
    private fun JSONObject.text(name: String): String {
        val value = opt(name)
        return if (value == null || value === JSONObject.NULL) "" else value.toString()
    }

    private fun org.json.JSONArray.toStringList(): List<String> =
        (0 until length()).map { getString(it) }
}

/**
 * Isi satu laporan.
 *
 * **Tidak ada field identitas di sini, dan ketiadaannya disengaja.** Basis data memang tidak
 * memiliki tempat untuk nama, telepon, maupun alamat pelapor; menambahkannya di sini hanya
 * akan menampung data yang kemudian ditolak backend, sementara pelapor mengira datanya
 * tersimpan.
 */
data class ReportDraft(
    val category: String,
    val area: String,
    val place: String,
    val story: String,
)
