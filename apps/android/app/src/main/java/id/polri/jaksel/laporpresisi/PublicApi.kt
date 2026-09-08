package id.polri.jaksel.laporpresisi

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStream
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
 * Tiga endpoint yang dipakai, seluruhnya **tanpa autentikasi**:
 *
 * ```text
 * GET  /api/v1/public/report-options   pilihan kategori dan kecamatan
 * POST /api/v1/public/attachments      menitipkan satu berkas, menerima handle
 * POST /api/v1/public/citizen-reports  mengirim laporan, menyebut handle-nya
 * ```
 *
 * Tidak ada token, tidak ada akun, dan tidak ada satu pun field identitas yang dikirim —
 * lihat [ReportDraft]. Backend menolak field yang tidak dikenalnya, sehingga menambahkan
 * satu di sini akan gagal dengan pesan yang jelas, bukan diam-diam tersimpan.
 *
 * Lampiran dititipkan **sebelum** laporan dikirim dan diwakili handle acak. Berkasnya tidak
 * pernah dikirim dua kali, dan pelapor tahu berkasnya diterima sebelum ia menulis
 * keterangan — bukan setelah menunggu unggahan panjang yang lalu ditolak.
 */
object PublicApi {

    private const val TIMEOUT_MS = 20_000

    /** Unggahan diberi waktu lebih panjang: berkas video pada jaringan seluler lambat. */
    private const val UPLOAD_TIMEOUT_MS = 120_000

    data class Options(
        val categories: List<String>,
        val areas: List<String>,
        val coordinateBasis: String,
        val attachmentBasis: String,
        val maxAttachments: Int,
        val maxAttachmentBytes: Long,
    )

    /** Satu berkas yang sudah dititipkan dan siap disebut saat mengirim laporan. */
    data class Staged(val handle: String, val kind: String, val byteSize: Long)

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
            attachmentBasis = json.text("attachment_basis"),
            maxAttachments = json.optInt("max_attachments", 0),
            maxAttachmentBytes = json.optLong("max_attachment_bytes", 0),
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
            // Koordinat hanya dikirim bila pelapor benar-benar menekan tombol bagikan
            // lokasi. Mengirim nol saat ia tidak menekannya akan menyimpan titik di lepas
            // pantai Afrika dan menandainya sebagai tempat kejadian menurut pelapor.
            if (draft.latitude != null && draft.longitude != null) {
                put("latitude", draft.latitude)
                put("longitude", draft.longitude)
                if (draft.accuracyMetres != null) put("accuracy_m", draft.accuracyMetres)
            }
            if (draft.attachments.isNotEmpty()) {
                put("attachments", JSONArray(draft.attachments))
            }
        }
        val body = post("$baseUrl/api/v1/public/citizen-reports", payload.toString())
        val json = JSONObject(body)
        Ticket(code = json.getString("ticket"), message = json.text("message"))
    }

    /**
     * Menitipkan satu berkas dan menerima handle-nya.
     *
     * Badan permintaan disusun sendiri sebagai `multipart/form-data`. Itu beberapa baris
     * lebih panjang daripada memakai pustaka HTTP, tetapi pustaka itu akan ikut terpasang
     * di ponsel warga hanya untuk satu permintaan — dan aplikasi yang dipasang orang yang
     * tidak dapat memeriksanya sebaiknya membawa sesedikit mungkin.
     *
     * Berkas dialirkan dari [InputStream], tidak pernah dibaca seluruhnya ke memori: video
     * puluhan megabita pada ponsel lama akan menjatuhkan aplikasinya.
     */
    suspend fun stage(
        baseUrl: String,
        stream: InputStream,
        fileName: String,
        mediaType: String,
    ): Staged = withContext(Dispatchers.IO) {
        val boundary = "----presisi${System.nanoTime()}"
        val connection =
            (URL("$baseUrl/api/v1/public/attachments").openConnection() as HttpURLConnection).apply {
                connectTimeout = TIMEOUT_MS
                readTimeout = UPLOAD_TIMEOUT_MS
                requestMethod = "POST"
                doOutput = true
                // Aliran dipotong-potong supaya berkas besar tidak ditumpuk di memori
                // sebelum dikirim.
                setChunkedStreamingMode(64 * 1024)
                setRequestProperty("Accept", "application/json")
                setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            }

        try {
            connection.outputStream.use { out ->
                out.write(
                    (
                        "--$boundary\r\n" +
                            "Content-Disposition: form-data; name=\"berkas\"; " +
                            "filename=\"$fileName\"\r\n" +
                            "Content-Type: $mediaType\r\n\r\n"
                        ).toByteArray(Charsets.UTF_8)
                )
                stream.copyTo(out, 64 * 1024)
                out.write("\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8))
            }

            val code = connection.responseCode
            val stream2 = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream2?.bufferedReader()?.use(BufferedReader::readText).orEmpty()
            if (code !in 200..299) throw ApiFailure(readableError(text, code))

            val json = JSONObject(text)
            Staged(
                handle = json.getString("handle"),
                kind = json.text("kind"),
                byteSize = json.optLong("byte_size"),
            )
        } catch (failure: ApiFailure) {
            throw failure
        } catch (_: Exception) {
            throw ApiFailure("Berkas tidak dapat dikirim. Periksa sambungan Anda.")
        } finally {
            connection.disconnect()
        }
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
    /**
     * Titik yang dibagikan pelapor, atau `null` bila ia tidak membagikannya.
     *
     * Keduanya harus berpasangan. Salah satu saja bukan lokasi, dan backend menolaknya —
     * dengan benar, karena menyimpannya berarti mengarang separuhnya.
     */
    val latitude: Double? = null,
    val longitude: Double? = null,
    val accuracyMetres: Double? = null,
    /** Handle lampiran yang sudah dititipkan lewat [PublicApi.stage]. */
    val attachments: List<String> = emptyList(),
)
