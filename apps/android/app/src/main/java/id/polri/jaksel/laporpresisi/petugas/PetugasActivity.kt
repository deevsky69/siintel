package id.polri.jaksel.laporpresisi.petugas

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.laporpresisi.BuildConfig
import id.polri.jaksel.laporpresisi.R
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import kotlinx.coroutines.launch

/**
 * PRESISI Petugas — masuk, lalu antrean pekerjaan menurut kewenangan (PHASE 17, TASK 171).
 *
 * ## Apa yang ditampilkan, dan mengapa hanya itu
 *
 * Aplikasi ini **tidak menyalin seluruh layar web ke ponsel**. Yang dibawa ke ponsel adalah
 * satu-satunya hal yang benar-benar berguna di luar meja kerja: **apa yang menunggu saya
 * kerjakan sekarang.** Peta, analitik, dan penilaian risiko menuntut layar lebar dan waktu
 * membaca; memaksakannya ke ponsel menghasilkan tiruan yang lebih buruk dari aslinya.
 *
 * Isinya berbeda menurut peran, dan perbedaannya **ditentukan server**: `GET /notifications`
 * mengikat tiap antrean ke permission tindakan. Pimpinan melihat rekomendasi yang menunggu
 * keputusannya; petugas Polsek melihat peringatan dan laporan warga. Aplikasi ini hanya
 * menggambar apa yang dikirim — ia tidak memutuskan apa pun tentang kewenangan.
 *
 * ## Sesi
 *
 * Token disimpan terenkripsi ([TokenStore]) dan aplikasi membuka langsung ke antrean bila
 * masih berlaku. Access token hanya berumur 15 menit, jadi hampir setiap kali aplikasi
 * dibuka kembali token itu sudah kedaluwarsa; [Session] menukarnya dengan yang baru
 * memakai refresh token tanpa melibatkan pengguna. Petugas baru diminta masuk kembali
 * setelah tujuh hari, atau ketika akunnya dinonaktifkan.
 *
 * Penolakan yang tidak dapat dipulihkan (`401` yang bertahan) menjatuhkan sesi dan
 * mengembalikan pengguna ke layar masuk beserta alasannya — bukan layar kosong yang tampak
 * rusak. Gangguan jaringan **tidak** menjatuhkan sesi.
 *
 * Kata sandi **tidak pernah disimpan**. Petugas yang kehilangan ponselnya kehilangan sesi,
 * bukan kata sandinya.
 *
 * ## Compose (7 Oktober 2026)
 *
 * Tampilan ada di [PetugasScreen]; Activity ini memegang [PetugasState], token, dan sesi.
 */
class PetugasActivity : ComponentActivity() {

    private var state by mutableStateOf(
        PetugasState(version = "${BuildConfig.VERSION_NAME} · Android ${android.os.Build.VERSION.RELEASE}"),
    )
    private lateinit var tokens: TokenStore
    private lateinit var session: Session

    private val actions = PetugasActions(
        onUsername = { state = state.copy(username = it, loginError = null) },
        onPassword = { state = state.copy(password = it, loginError = null) },
        onSignIn = ::signIn,
        onRefresh = ::loadQueues,
        onSignOut = { signOut(null) },
        onVerify = ::verify,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokens = TokenStore(this)
        session = Session(BuildConfig.API_BASE, tokens)
        setContent { PresisiTheme { PetugasScreen(state, actions) } }
        if (tokens.accessToken == null) showLogin(null) else loadQueues()
    }

    private fun signIn() {
        val username = state.username.trim()
        val password = state.password
        if (username.isBlank() || password.isBlank()) {
            state = state.copy(loginError = getString(R.string.err_credentials))
            return
        }
        state = state.copy(signingIn = true, busy = true, loginError = null)
        lifecycleScope.launch {
            try {
                val granted = Api.login(BuildConfig.API_BASE, username, password)
                tokens.accessToken = granted.accessToken
                tokens.refreshToken = granted.refreshToken
                // Kata sandi dihapus dari keadaan begitu ditukar dengan token: membiarkannya
                // tertinggal berarti ia terbaca siapa pun yang meminjam ponselnya.
                state = state.copy(password = "")
                loadQueues()
            } catch (failure: Api.Failure) {
                state = state.copy(loginError = failure.readable)
            } finally {
                state = state.copy(signingIn = false, busy = false)
            }
        }
    }

    private fun loadQueues() {
        if (tokens.accessToken == null) return showLogin(null)
        state = state.copy(busy = true)
        lifecycleScope.launch {
            try {
                val profile = session.run { Api.profile(BuildConfig.API_BASE, it) }
                val feed = session.run { Api.notifications(BuildConfig.API_BASE, it) }
                // Keterangan dikembalikan ke bunyi aslinya: pesan galat dari pemuatan yang
                // gagal sebelumnya tidak boleh tertinggal setelah pemuatan berikutnya berhasil.
                state = state.copy(profile = profile, feed = feed, note = null, loginError = null)
            } catch (failure: Api.Failure) {
                if (failure.unauthorized) {
                    signOut(getString(R.string.err_session))
                } else {
                    // Kegagalan jaringan tidak menjatuhkan sesi: token masih sah, dan
                    // memaksa masuk ulang setiap kali sinyal buruk membuat aplikasi ini
                    // tidak dapat dipakai di lapangan.
                    state = state.copy(note = failure.readable)
                }
            } finally {
                state = state.copy(busy = false)
            }
        }
    }

    /**
     * Memverifikasi satu laporan warga dari ponsel.
     *
     * Tombolnya dimatikan selama berjalan dan tidak dinyalakan kembali bila berhasil:
     * laporan yang sudah berpindah status tidak lagi ada di antrean, dan menekannya kedua
     * kali akan dijawab `409` oleh server. Antrean dimuat ulang sesudahnya supaya yang
     * terlihat di layar adalah keadaan sesungguhnya, bukan tebakan aplikasi.
     */
    private fun verify(code: String) {
        state = state.copy(verifying = state.verifying + code)
        lifecycleScope.launch {
            try {
                session.run { Api.verifyReport(BuildConfig.API_BASE, it, code) }
                state = state.copy(note = getString(R.string.verified_done, code))
                loadQueues()
            } catch (failure: Api.Failure) {
                if (failure.unauthorized) {
                    signOut(getString(R.string.err_session))
                } else {
                    state = state.copy(note = failure.readable)
                }
            } finally {
                state = state.copy(verifying = state.verifying - code)
            }
        }
    }

    private fun signOut(reason: String?) {
        tokens.clear()
        showLogin(reason)
    }

    private fun showLogin(reason: String?) {
        state = state.copy(profile = null, feed = null, password = "", loginError = reason, verifying = emptySet())
    }
}
