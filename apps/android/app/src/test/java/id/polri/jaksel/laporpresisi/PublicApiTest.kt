package id.polri.jaksel.laporpresisi

import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Test kanal laporan warga.
 *
 * Dua hal yang diuji paling keras, karena keduanya adalah janji yang dibuat aplikasi ini
 * kepada pemakainya:
 *
 * 1. **Tidak ada satu pun field identitas yang terkirim.** Itu bukan sekadar niat baik —
 *    basis datanya memang tidak punya tempat untuk itu, dan pelapor diberi tahu demikian.
 * 2. **Kegagalan sampai sebagai kalimat yang dimengerti**, bukan kode status. Warga yang
 *    laporannya gagal tidak punya cara lain untuk tahu apa yang harus diperbaiki.
 */
class PublicApiTest {

    private val optionsBody = """
        {"categories":["Pencurian","Narkoba"],
         "kecamatan":["Tebet","Kebayoran Baru"],
         "coordinate_basis":"Titik tengah kecamatan"}
    """.trimIndent()

    private val ticketBody = """{"ticket":"CR-2026-0001","message":"Laporan Anda diterima."}"""

    @Test
    fun `pilihan kategori dan kecamatan diambil dari server, bukan ditanam di aplikasi`() =
        runBlocking {
            FakeServer().use { server ->
                server.on("/api/v1/public/report-options", FakeServer.Reply(200, optionsBody))

                val options = PublicApi.options(server.base)

                assertEquals(listOf("Pencurian", "Narkoba"), options.categories)
                assertEquals(listOf("Tebet", "Kebayoran Baru"), options.areas)
                assertEquals("Titik tengah kecamatan", options.coordinateBasis)
                assertEquals("GET", server.requestsTo("/api/v1/public/report-options").single().method)
            }
        }

    @Test
    fun `laporan dikirim tanpa satu pun field identitas`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/public/citizen-reports", FakeServer.Reply(201, ticketBody))

            PublicApi.submit(
                server.base,
                ReportDraft(
                    category = "Pencurian",
                    area = "Tebet",
                    place = "Depan minimarket Jalan Tebet Raya",
                    story = "Sepeda motor hilang saat ditinggal sebentar.",
                ),
            )

            val sent = JSONObject(server.requestsTo("/api/v1/public/citizen-reports").single().body)
            assertEquals(
                setOf("category", "kecamatan", "description", "location_text"),
                sent.keys().asSequence().toSet(),
            )
            for (identitas in listOf("nama", "name", "phone", "telepon", "nik", "email", "address", "alamat")) {
                assertFalse(identitas, sent.has(identitas))
            }
        }
    }

    @Test
    fun `tempat kejadian yang tidak diisi tidak dikirim sebagai teks kosong`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/public/citizen-reports", FakeServer.Reply(201, ticketBody))

            PublicApi.submit(
                server.base,
                ReportDraft("Narkoba", "Tebet", "   ", "Ada aktivitas mencurigakan tiap malam."),
            )

            val sent = JSONObject(server.requestsTo("/api/v1/public/citizen-reports").single().body)
            // Backend menolak field opsional yang bernilai kosong. Mengirimkannya akan
            // menghasilkan galat yang membingungkan justru bagi pelapor yang tidak mengisinya.
            assertFalse(sent.has("location_text"))
        }
    }

    @Test
    fun `nomor tiket dikembalikan supaya pelapor punya pegangan`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/public/citizen-reports", FakeServer.Reply(201, ticketBody))

            val ticket = PublicApi.submit(
                server.base,
                ReportDraft("Pencurian", "Tebet", "", "Sepeda motor hilang di depan rumah."),
            )

            assertEquals("CR-2026-0001", ticket.code)
            assertEquals("Laporan Anda diterima.", ticket.message)
        }
    }

    @Test
    fun `pesan penolakan dari server diteruskan apa adanya`() = runBlocking {
        FakeServer().use { server ->
            server.on(
                "/api/v1/public/citizen-reports",
                FakeServer.Reply(400, """{"error":{"code":"VALIDATION_ERROR","message":"Kecamatan tidak dikenal."}}"""),
            )

            val failure = runCatching {
                PublicApi.submit(server.base, ReportDraft("Pencurian", "Bandung", "", "Isi laporan yang cukup panjang."))
            }.exceptionOrNull()

            // Server yang tahu apa yang ditolak; menggantinya dengan kalimat umum
            // menghilangkan satu-satunya petunjuk untuk memperbaikinya.
            assertEquals("Kecamatan tidak dikenal.", (failure as PublicApi.ApiFailure).readable)
        }
    }

    @Test
    fun `batas pengiriman per jam dijelaskan, bukan ditampilkan sebagai kode 429`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/public/citizen-reports", FakeServer.Reply(429, "bukan json"))

            val failure = runCatching {
                PublicApi.submit(server.base, ReportDraft("Pencurian", "Tebet", "", "Isi laporan yang cukup panjang."))
            }.exceptionOrNull()

            assertTrue((failure as PublicApi.ApiFailure).readable.contains("Terlalu banyak laporan"))
        }
    }

    @Test
    fun `server yang tidak dapat dihubungi mengarahkan pelapor ke 110`() = runBlocking {
        val failure = runCatching {
            // Port tertutup: kegagalannya di lapisan soket, bukan HTTP.
            PublicApi.submit("http://127.0.0.1:1", ReportDraft("Pencurian", "Tebet", "", "Isi laporan yang cukup panjang."))
        }.exceptionOrNull()

        // Keadaan mendesak tidak boleh berhenti pada aplikasi yang sedang tidak berfungsi.
        assertTrue((failure as PublicApi.ApiFailure).readable.contains("110"))
    }
}
