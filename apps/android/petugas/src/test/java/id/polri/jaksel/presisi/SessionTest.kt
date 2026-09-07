package id.polri.jaksel.presisi

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Test aturan pembaruan sesi.
 *
 * Ini bagian yang menentukan apakah aplikasi petugas dapat dipakai. Access token berumur 15
 * menit; tanpa pembaruan otomatis, tiap kali aplikasi dibuka kembali petugas harus mengetik
 * ulang kata sandinya. Test di sini memastikan perilaku itu bukan sekadar niat.
 */
class SessionTest {

    private val meBody = """{"username":"demo.polsek","full_name":"Demo Polsek","role":"Polsek","permissions":[]}"""

    @Test
    fun `token kedaluwarsa ditukar diam-diam dan permintaan diulang sekali`() = runBlocking {
        FakeServer().use { server ->
            server.on(
                "/api/v1/auth/me",
                FakeServer.Reply(401, """{"error":{"message":"Token kedaluwarsa."}}"""),
                FakeServer.Reply(200, meBody),
            )
            server.on("/api/v1/auth/refresh", FakeServer.Reply(200, """{"access_token":"A2"}"""))
            val tokens = FakeTokens(accessToken = "A1", refreshToken = "R1")

            val profile = Session(server.base, tokens).run { Api.profile(server.base, it) }

            assertEquals("Demo Polsek", profile.name)
            // Token baru disimpan, sehingga permintaan berikutnya tidak perlu ditolak dulu.
            assertEquals("A2", tokens.accessToken)
            assertEquals("R1", tokens.refreshToken)

            val attempts = server.requestsTo("/api/v1/auth/me")
            assertEquals(2, attempts.size)
            assertEquals("Bearer A1", attempts[0].header("Authorization"))
            assertEquals("Bearer A2", attempts[1].header("Authorization"))
        }
    }

    @Test
    fun `token yang masih berlaku tidak memicu pembaruan sama sekali`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/me", FakeServer.Reply(200, meBody))
            server.on("/api/v1/auth/refresh", FakeServer.Reply(200, """{"access_token":"A2"}"""))
            val tokens = FakeTokens(accessToken = "A1", refreshToken = "R1")

            Session(server.base, tokens).run { Api.profile(server.base, it) }

            assertTrue(server.requestsTo("/api/v1/auth/refresh").isEmpty())
            assertEquals("A1", tokens.accessToken)
        }
    }

    @Test
    fun `refresh token yang sudah habis umurnya mengakhiri sesi, bukan mengulang selamanya`() =
        runBlocking {
            FakeServer().use { server ->
                server.on("/api/v1/auth/me", FakeServer.Reply(401, ""))
                server.on(
                    "/api/v1/auth/refresh",
                    FakeServer.Reply(401, """{"error":{"message":"Sesi tidak sah."}}"""),
                )
                val tokens = FakeTokens(accessToken = "A1", refreshToken = "R-lama")

                val failure = runCatching {
                    Session(server.base, tokens).run { Api.profile(server.base, it) }
                }.exceptionOrNull()

                assertTrue((failure as Api.Failure).unauthorized)
                assertEquals("Sesi tidak sah.", failure.readable)
                // Hanya satu percobaan awal; tidak ada percobaan ketiga.
                assertEquals(1, server.requestsTo("/api/v1/auth/me").size)
                assertEquals(1, server.requestsTo("/api/v1/auth/refresh").size)
            }
        }

    @Test
    fun `token baru yang tetap ditolak menyerah, tidak menggelung`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/me", FakeServer.Reply(401, ""))
            server.on("/api/v1/auth/refresh", FakeServer.Reply(200, """{"access_token":"A2"}"""))
            val tokens = FakeTokens(accessToken = "A1", refreshToken = "R1")

            val failure = runCatching {
                Session(server.base, tokens).run { Api.profile(server.base, it) }
            }.exceptionOrNull()

            assertTrue((failure as Api.Failure).unauthorized)
            assertEquals(2, server.requestsTo("/api/v1/auth/me").size)
            assertEquals(1, server.requestsTo("/api/v1/auth/refresh").size)
        }
    }

    @Test
    fun `gangguan jaringan tidak menjatuhkan sesi yang masih sah`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/me", FakeServer.Reply(503, ""))
            server.on("/api/v1/auth/refresh", FakeServer.Reply(200, """{"access_token":"A2"}"""))
            val tokens = FakeTokens(accessToken = "A1", refreshToken = "R1")

            val failure = runCatching {
                Session(server.base, tokens).run { Api.profile(server.base, it) }
            }.exceptionOrNull()

            assertEquals(false, (failure as Api.Failure).unauthorized)
            assertTrue(server.requestsTo("/api/v1/auth/refresh").isEmpty())
            assertEquals("A1", tokens.accessToken)
        }
    }

    @Test
    fun `sesi lama tanpa refresh token meminta masuk kembali, bukan menelan galatnya`() =
        runBlocking {
            FakeServer().use { server ->
                server.on("/api/v1/auth/me", FakeServer.Reply(401, ""))
                // Pemasangan sebelum pembaruan aplikasi hanya menyimpan access token.
                val tokens = FakeTokens(accessToken = "A1", refreshToken = null)

                val failure = runCatching {
                    Session(server.base, tokens).run { Api.profile(server.base, it) }
                }.exceptionOrNull()

                assertTrue((failure as Api.Failure).unauthorized)
                assertEquals(1, server.requestsTo("/api/v1/auth/me").size)
            }
        }

    @Test
    fun `tanpa token sama sekali, tidak ada permintaan yang dikirim`() = runBlocking {
        FakeServer().use { server ->
            server.on("/api/v1/auth/me", FakeServer.Reply(200, meBody))
            val tokens = FakeTokens()

            val failure = runCatching {
                Session(server.base, tokens).run { Api.profile(server.base, it) }
            }.exceptionOrNull()

            assertTrue((failure as Api.Failure).unauthorized)
            assertTrue(server.received.isEmpty())
        }
    }

    @Test
    fun `keluar menghapus kedua token`() {
        val tokens = FakeTokens(accessToken = "A1", refreshToken = "R1")

        tokens.clear()

        assertNull(tokens.accessToken)
        // Refresh token berumur tujuh hari. Meninggalkannya setelah keluar berarti sesi
        // yang dikira sudah berakhir sebenarnya masih dapat dihidupkan kembali.
        assertNull(tokens.refreshToken)
    }
}
