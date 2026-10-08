package id.polri.jaksel.laporpresisi.petugas

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.activity.compose.BackHandler
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
 * ## Apa yang ditampilkan, dan mengapa
 *
 * Sampai 7 Oktober 2026 layar ini sengaja hanya satu: "apa yang menunggu saya". Pemilik
 * proyek kemudian meminta menu dan rincian, maka kini ada **menu bawah** yang tabnya
 * mengikuti permission dari `/auth/me` — Antrean dan Akun selalu; Peringatan, Laporan,
 * Rekomendasi hanya bila servernya memberi hak baca — dan **halaman rincian** per baris
 * dengan tindakan yang kewenangannya dipegang akun itu: terima/selesaikan peringatan,
 * verifikasi laporan, keputusan Pimpinan atas rekomendasi. Peta, analitik, dan evaluasi
 * tetap di web: menuntut layar lebar dan waktu membaca.
 *
 * Isi tiap tab datang dari endpoint yang sama dengan web (`/warnings`, `/citizen-reports`,
 * `/recommendations`); aplikasi ini tidak menghitung dan tidak memutuskan apa pun tentang
 * kewenangan — server yang menyaring wilayah dan menolak tindakan yang tidak sah.
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
 * mengembalikan pengguna ke layar masuk beserta alasannya. Gangguan jaringan **tidak**
 * menjatuhkan sesi. Kata sandi **tidak pernah disimpan**.
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
        onRefresh = ::reloadCurrent,
        onSignOut = { signOut(null) },
        onTab = ::openTab,
        onOpen = ::openDetail,
        onBack = { state = state.copy(detail = null) },
        onVerify = { code -> act(code, { Api.verifyReport(BuildConfig.API_BASE, it, code) }, R.string.verified_done) },
        onAcknowledge = { code -> act(code, { Api.acknowledgeWarning(BuildConfig.API_BASE, it, code) }, R.string.verified_done) },
        onResolve = { code -> act(code, { Api.resolveWarning(BuildConfig.API_BASE, it, code) }, R.string.verified_done) },
        onDecisionChoice = { state = state.copy(decisionChoice = it) },
        onDecisionReason = { state = state.copy(decisionReason = it) },
        onDecisionText = { state = state.copy(decisionText = it) },
        onDecide = ::decide,
        onPanicAcknowledge = { code -> act(code, { Api.acknowledgePanic(BuildConfig.API_BASE, it, code) }, R.string.verified_done) },
        onPanicCloseNote = { state = state.copy(panicCloseNote = it) },
        onPanicClose = { code ->
            act(code, { Api.closePanic(BuildConfig.API_BASE, it, code, state.panicCloseNote) }, R.string.verified_done)
            state = state.copy(panicCloseNote = "")
        },
    )

    /** Izin notifikasi (Android 13+) diminta sekali setelah antrean pertama termuat. */
    private val askNotifications =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    /** Kode darurat OPEN yang sudah dibunyikan, supaya tidak berbunyi lagi tiap polling. */
    private val announced = mutableSetOf<String>()
    private val poller = Handler(Looper.getMainLooper())
    private val pollTask = object : Runnable {
        override fun run() {
            if (tokens.accessToken != null && state.profile != null) loadQueues(quiet = true)
            poller.postDelayed(this, POLL_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokens = TokenStore(this)
        session = Session(BuildConfig.API_BASE, tokens)
        setContent {
            PresisiTheme {
                // Tombol kembali sistem menutup rincian dulu, lalu kembali ke tab Antrean,
                // baru keluar dari layar — seperti yang diharapkan dari aplikasi bermenu.
                BackHandler(enabled = state.detail != null || state.tab != Tab.ANTREAN) {
                    state = if (state.detail != null) state.copy(detail = null) else state.copy(tab = Tab.ANTREAN)
                }
                PetugasScreen(state, actions)
            }
        }
        if (tokens.accessToken == null) showLogin(null) else loadQueues()
    }

    /**
     * Selama layar terbuka antrean diperiksa tiap [POLL_MS]: inilah "pemberitahuan" bagi
     * petugas tanpa layanan dorong pihak ketiga. Permintaan darurat baru dibunyikan sebagai
     * notifikasi sistem. Ponsel yang aplikasinya tertutup TIDAK diberi tahu — dinyatakan di
     * docs/implementation-notes/170 §12.
     */
    override fun onResume() {
        super.onResume()
        poller.removeCallbacks(pollTask)
        poller.postDelayed(pollTask, POLL_MS)
    }

    override fun onPause() {
        poller.removeCallbacks(pollTask)
        super.onPause()
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

    /** Memuat ulang apa pun yang sedang dilihat: antrean, atau daftar tab aktif. */
    private fun reloadCurrent() {
        when (state.detail?.tab ?: state.tab) {
            Tab.DARURAT -> loadList(Tab.DARURAT, force = true)
            Tab.PERINGATAN -> loadList(Tab.PERINGATAN, force = true)
            Tab.LAPORAN -> loadList(Tab.LAPORAN, force = true)
            Tab.REKOMENDASI -> loadList(Tab.REKOMENDASI, force = true)
            else -> loadQueues()
        }
    }

    private fun openTab(tab: Tab) {
        state = state.copy(tab = tab, detail = null)
        loadList(tab)
    }

    private fun openDetail(ref: DetailRef) {
        state = state.copy(tab = ref.tab, detail = ref, decisionChoice = "APPROVED", decisionReason = "", decisionText = "")
        loadList(ref.tab)
    }

    private fun loadQueues(quiet: Boolean = false) {
        if (tokens.accessToken == null) return showLogin(null)
        if (!quiet) state = state.copy(busy = true)
        lifecycleScope.launch {
            try {
                val profile = session.run { Api.profile(BuildConfig.API_BASE, it) }
                val feed = session.run { Api.notifications(BuildConfig.API_BASE, it) }
                // Ringkasan situasi boleh gagal tanpa menjatuhkan beranda: angkanya pelengkap.
                val summary = runCatching { session.run { Api.summary(BuildConfig.API_BASE, it) } }.getOrNull()
                // Keterangan dikembalikan ke bunyi aslinya: pesan galat dari pemuatan yang
                // gagal sebelumnya tidak boleh tertinggal setelah pemuatan berikutnya berhasil.
                state = state.copy(profile = profile, feed = feed, summary = summary ?: state.summary, note = if (quiet) state.note else null, loginError = null)
                announcePanic(feed)
                // Daftar darurat ikut disegarkan saat polling supaya tab Darurat tidak basi.
                if (quiet && state.panics != null) loadList(Tab.DARURAT, force = true)
                if (!quiet) ensureNotificationPermission()
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

    private fun ensureNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    /** Membunyikan notifikasi sistem untuk tiap permintaan darurat OPEN yang belum pernah dibunyikan. */
    private fun announcePanic(feed: Api.Feed) {
        val group = feed.queues.firstOrNull { it.kind == "PANIC" } ?: return
        val fresh = group.items.filter { announced.add(it.code) }
        if (fresh.isEmpty()) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(PANIC_CHANNEL, getString(R.string.panic_notification_channel), NotificationManager.IMPORTANCE_HIGH),
            )
        }
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, PetugasActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        for (item in fresh) {
            val notification = NotificationCompat.Builder(this, PANIC_CHANNEL)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle(getString(R.string.panic_notification_title))
                .setContentText(getString(R.string.panic_notification_body, item.headline, item.detail))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setAutoCancel(true)
                .setContentIntent(open)
                .build()
            manager.notify(item.code.hashCode(), notification)
        }
    }

    /** Memuat daftar satu tab; sekali saja kecuali [force], supaya berpindah tab tidak lambat. */
    private fun loadList(tab: Tab, force: Boolean = false) {
        val loaded = when (tab) {
            Tab.DARURAT -> state.panics != null
            Tab.PERINGATAN -> state.warnings != null
            Tab.LAPORAN -> state.reports != null
            Tab.REKOMENDASI -> state.recommendations != null
            else -> return
        }
        if (loaded && !force) return
        state = state.copy(busy = true)
        lifecycleScope.launch {
            try {
                // Hasil ditunggu DULU, baru `state` disalin: `state.copy(x = suspend())`
                // mengambil `state` sebelum menunggu dan menimpa perubahan yang terjadi di
                // sela-selanya (ganti tab, antrean selesai dimuat) dengan keadaan basi.
                when (tab) {
                    Tab.DARURAT -> {
                        val rows = session.run { Api.panicEvents(BuildConfig.API_BASE, it) }
                        state = state.copy(panics = rows, note = null)
                    }
                    Tab.PERINGATAN -> {
                        val rows = session.run { Api.warnings(BuildConfig.API_BASE, it) }
                        state = state.copy(warnings = rows, note = null)
                    }
                    Tab.LAPORAN -> {
                        val rows = session.run { Api.reports(BuildConfig.API_BASE, it) }
                        state = state.copy(reports = rows, note = null)
                    }
                    Tab.REKOMENDASI -> {
                        val rows = session.run { Api.recommendations(BuildConfig.API_BASE, it) }
                        state = state.copy(recommendations = rows, note = null)
                    }
                    else -> Unit
                }
            } catch (failure: Api.Failure) {
                if (failure.unauthorized) signOut(getString(R.string.err_session)) else state = state.copy(note = failure.readable)
            } finally {
                state = state.copy(busy = false)
            }
        }
    }

    /**
     * Satu tindakan atas satu kode: tombolnya dimatikan selama berjalan, lalu antrean dan
     * daftar yang bersangkutan dimuat ulang supaya yang terlihat adalah keadaan sesungguhnya,
     * bukan tebakan aplikasi. Server yang memutuskan boleh atau tidak.
     */
    private fun act(code: String, request: suspend (String) -> Any, doneMessage: Int) {
        state = state.copy(acting = state.acting + code)
        lifecycleScope.launch {
            try {
                session.run(request)
                state = state.copy(note = getString(doneMessage, code))
                reloadAfterAction()
            } catch (failure: Api.Failure) {
                if (failure.unauthorized) signOut(getString(R.string.err_session)) else state = state.copy(note = failure.readable)
            } finally {
                state = state.copy(acting = state.acting - code)
            }
        }
    }

    private fun decide(code: String) {
        val choice = state.decisionChoice
        if (choice == "MODIFIED" && state.decisionText.isBlank()) {
            state = state.copy(note = getString(R.string.err_decision_text))
            return
        }
        act(
            code,
            { Api.decide(BuildConfig.API_BASE, it, code, choice, state.decisionReason, state.decisionText) },
            R.string.decision_done,
        )
    }

    private fun reloadAfterAction() {
        val tab = state.detail?.tab ?: state.tab
        if (tab != Tab.ANTREAN && tab != Tab.AKUN) loadList(tab, force = true)
        loadQueues()
    }

    private fun signOut(reason: String?) {
        tokens.clear()
        showLogin(reason)
    }

    private companion object {
        const val POLL_MS = 30_000L
        const val PANIC_CHANNEL = "darurat"
    }

    private fun showLogin(reason: String?) {
        state = PetugasState(version = state.version, username = state.username, loginError = reason)
    }
}
