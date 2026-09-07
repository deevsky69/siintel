package id.polri.jaksel.presisi

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Test lapisan API petugas.
 *
 * Fokusnya pada hal-hal yang **hanya terlihat saat aplikasi berbicara dengan server**:
 * refresh token yang datang lewat header, bukan badan respons; `401` yang harus dibedakan
 * dari kegagalan lain; dan pesan galat yang harus sampai ke petugas dalam bahasa yang
 * dimengerti.
 */
class ApiTest {

    private val loginBody = """{"access_token":"A1","token_type":"bearer",""" +
        """"expires_at":"2026-09-07T10:00:00Z","must_change_password":false}"""

    @Test
    fun `login memungut refresh token dari header Set-Cookie`() = runBlocking {
        FakeServer().use { server ->
            server.on(
                "/api/v1/auth/login",
                FakeServer.Reply(
                    200,
                    loginBody,
                    mapOf("Set-Cookie" to "predpol_refresh=R1; Path=/api/v1/auth; HttpOnly; Max-Age=604800"),
                ),
            )

            val granted = Api.login(server.base, "demo.pimpinan", "rahasia")

            assertEquals("A1", granted.accessToken)
            assertEquals("R1", granted.refreshToken)
        }
    }

    @Test
    fun `login tanpa cookie menghasilkan refresh token kosong, bukan gagal`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/login", FakeServer.Reply(200, loginBody))

            val granted = Api.login(server.base, "demo.pimpinan", "rahasia")

            assertEquals("A1", granted.accessToken)
            assertNull(granted.refreshToken)
        }
    }

    @Test
    fun `login mengirim kredensial pada badan permintaan, bukan pada URL`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/login", FakeServer.Reply(200, loginBody))

            Api.login(server.base, "demo.pimpinan", "rahasia")

            val request = server.requestsTo("/api/v1/auth/login").single()
            assertEquals("POST", request.method)
            assertEquals("/api/v1/auth/login", request.path)
            assertTrue(request.body.contains(""""password":"rahasia""""))
        }
    }

    @Test
    fun `refresh mengirim token sebagai header Cookie sesuai yang dibaca server`() = runBlocking {
        FakeServer().use { server ->
            server.on(
                "/api/v1/auth/refresh",
                FakeServer.Reply(200, """{"access_token":"A2","expires_at":"2026-09-07T10:15:00Z"}"""),
            )

            val renewed = Api.refresh(server.base, "R1")

            assertEquals("A2", renewed)
            val request = server.requestsTo("/api/v1/auth/refresh").single()
            assertEquals("POST", request.method)
            assertEquals("predpol_refresh=R1", request.header("Cookie"))
            // Refresh tidak membawa Authorization: access token yang lama justru sudah mati.
            assertNull(request.header("Authorization"))
        }
    }

    @Test
    fun `permintaan ber-token membawa Authorization Bearer`() = runBlocking {
        FakeServer().use { server ->
            server.on(
                "/api/v1/auth/me",
                FakeServer.Reply(200, """{"username":"demo.pimpinan","full_name":"","role":"Pimpinan","permissions":[]}"""),
            )

            Api.profile(server.base, "A1")

            assertEquals("Bearer A1", server.requestsTo("/api/v1/auth/me").single().header("Authorization"))
        }
    }

    @Test
    fun `401 ditandai sebagai sesi berakhir, galat lain tidak`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/me", FakeServer.Reply(401, """{"error":{"message":"Token kedaluwarsa."}}"""))
            server.on("/api/v1/notifications", FakeServer.Reply(503, ""))

            val expired = runCatching { Api.profile(server.base, "A1") }.exceptionOrNull()
            val broken = runCatching { Api.notifications(server.base, "A1") }.exceptionOrNull()

            assertTrue((expired as Api.Failure).unauthorized)
            assertEquals("Token kedaluwarsa.", expired.readable)
            assertFalse((broken as Api.Failure).unauthorized)
            assertEquals("Server sedang bermasalah. Coba lagi beberapa saat lagi.", broken.readable)
        }
    }

    @Test
    fun `server yang tidak dapat dihubungi tidak dianggap sesi berakhir`() = runBlocking {
        // Port yang tertutup: kegagalannya di lapisan soket, bukan HTTP.
        val failure = runCatching { Api.profile("http://127.0.0.1:1", "A1") }.exceptionOrNull()

        assertFalse((failure as Api.Failure).unauthorized)
        assertTrue(failure.readable.contains("sambungan internet"))
    }

    @Test
    fun `profil memakai nama lengkap, dan jatuh ke nama pengguna bila kosong`() {
        val bernama = Api.parseProfile(
            """{"username":"demo.pimpinan","full_name":"Kombes Pol Demo","role":"Pimpinan","permissions":["prediction:read"]}""",
        )
        val namaNull = Api.parseProfile(
            """{"username":"demo.polsek","full_name":null,"role":"Polsek","permissions":[]}""",
        )
        val tanpaField = Api.parseProfile("""{"username":"demo.fungsi","role":"Fungsi"}""")

        assertEquals("Kombes Pol Demo", bernama.name)
        assertEquals(listOf("prediction:read"), bernama.permissions)
        // `full_name` memang NULL di basis data untuk akun demo. Nilai itu tidak boleh
        // sampai ke layar sebagai teks "null" — lihat `Api.text`.
        assertEquals("demo.polsek", namaNull.name)
        assertEquals(emptyList<String>(), namaNull.permissions)
        assertEquals("demo.fungsi", tanpaField.name)
    }

    @Test
    fun `antrean diurai beserta isinya`() {
        val feed = Api.parseFeed(
            """
            {"role":"Pimpinan","total":3,"groups":[
              {"kind":"RECOMMENDATION","title":"Rekomendasi menunggu keputusan","action":"Putuskan",
               "total":2,"items":[
                 {"headline":"Patroli Tebet","detail":"Prioritas tinggi"},
                 {"headline":"Operasi Kebayoran","detail":"Prioritas sedang"}]},
              {"kind":"EARLY_WARNING","title":"Peringatan dini","action":"Tinjau","total":1,"items":[]}
            ]}
            """.trimIndent(),
        )

        assertEquals("Pimpinan", feed.role)
        assertEquals(3, feed.total)
        assertEquals(2, feed.queues.size)
        assertEquals("Patroli Tebet", feed.queues[0].items[0].headline)
        // Antrean berjumlah satu tetapi tanpa rincian tetap terbaca sebagai antrean, bukan
        // dibuang — angkanya yang penting bagi pembaca.
        assertEquals(1, feed.queues[1].total)
        assertTrue(feed.queues[1].items.isEmpty())
    }

    @Test
    fun `cookie lain di header yang sama tidak tertukar dengan refresh token`() {
        val diambil = Api.refreshTokenFrom(
            mapOf(
                "set-cookie" to listOf(
                    "sesi_lain=XX; Path=/",
                    "predpol_refresh=R9; Path=/api/v1/auth; HttpOnly",
                ),
            ),
        )
        val dihapus = Api.refreshTokenFrom(
            mapOf("Set-Cookie" to listOf("""predpol_refresh=""; Max-Age=0; Path=/api/v1/auth""")),
        )
        val takAda = Api.refreshTokenFrom(mapOf("Content-Type" to listOf("application/json")))

        assertEquals("R9", diambil)
        // Cookie bernilai kosong adalah cara server menghapusnya, bukan token yang sah.
        assertNull(dihapus)
        assertNull(takAda)
    }

    @Test
    fun `status HTTP tanpa badan galat tetap menghasilkan kalimat yang terbaca`() {
        assertEquals("Nama pengguna atau kata sandi salah.", Api.readable("", 401))
        assertEquals("Akun Anda tidak memiliki kewenangan untuk ini.", Api.readable("", 403))
        assertEquals("Permintaan gagal (418).", Api.readable("bukan json", 418))
    }
}
