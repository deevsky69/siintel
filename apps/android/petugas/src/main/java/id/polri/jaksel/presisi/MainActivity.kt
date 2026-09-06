package id.polri.jaksel.presisi

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.presisi.databinding.ActivityMainBinding
import id.polri.jaksel.presisi.databinding.ItemQueueBinding
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
 * masih berlaku. Token yang ditolak server (`401`) menjatuhkan sesi dan mengembalikan
 * pengguna ke layar masuk beserta alasannya — bukan layar kosong yang tampak rusak.
 *
 * Kata sandi **tidak pernah disimpan**. Petugas yang kehilangan ponselnya kehilangan sesi,
 * bukan kata sandinya.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var views: ActivityMainBinding
    private lateinit var tokens: TokenStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        views = ActivityMainBinding.inflate(layoutInflater)
        setContentView(views.root)
        tokens = TokenStore(this)

        views.versionText.text = getString(
            R.string.version_label,
        ) + " ${BuildConfig.VERSION_NAME} · Android ${android.os.Build.VERSION.RELEASE}"

        views.loginButton.setOnClickListener { signIn() }
        views.refreshButton.setOnClickListener { loadQueues() }
        views.logoutButton.setOnClickListener { signOut(null) }

        val existing = tokens.accessToken
        if (existing == null) showLogin(null) else loadQueues()
    }

    private fun signIn() {
        val username = views.usernameInput.text.toString().trim()
        val password = views.passwordInput.text.toString()

        if (username.isBlank() || password.isBlank()) {
            showLoginError(getString(R.string.err_credentials))
            return
        }

        busy(true)
        views.loginButton.isEnabled = false
        views.loginButton.text = getString(R.string.signing_in)

        lifecycleScope.launch {
            try {
                val session = Api.login(BuildConfig.API_BASE, username, password)
                tokens.accessToken = session.accessToken
                // Kata sandi dihapus dari layar begitu ditukar dengan token: membiarkannya
                // tertinggal di kolom berarti ia terbaca siapa pun yang meminjam ponselnya.
                views.passwordInput.text?.clear()
                loadQueues()
            } catch (failure: Api.Failure) {
                showLoginError(failure.readable)
            } finally {
                busy(false)
                views.loginButton.isEnabled = true
                views.loginButton.text = getString(R.string.sign_in)
            }
        }
    }

    private fun loadQueues() {
        val token = tokens.accessToken ?: return showLogin(null)

        busy(true)
        lifecycleScope.launch {
            try {
                val profile = Api.profile(BuildConfig.API_BASE, token)
                val feed = Api.notifications(BuildConfig.API_BASE, token)
                render(profile, feed)
            } catch (failure: Api.Failure) {
                if (failure.unauthorized) {
                    signOut(getString(R.string.err_session))
                } else {
                    // Kegagalan jaringan tidak menjatuhkan sesi: token masih sah, dan
                    // memaksa masuk ulang setiap kali sinyal buruk membuat aplikasi ini
                    // tidak dapat dipakai di lapangan.
                    showLoginErrorOnHome(failure.readable)
                }
            } finally {
                busy(false)
            }
        }
    }

    private fun render(profile: Api.Profile, feed: Api.Feed) {
        views.loginGroup.visibility = View.GONE
        views.homeGroup.visibility = View.VISIBLE

        views.whoText.text = profile.name
        views.roleText.text = profile.role
        views.totalText.text = feed.total.toString()
        views.totalText.setTextColor(
            ContextCompat.getColor(this, if (feed.total > 0) R.color.critical else R.color.ink_faint),
        )

        views.queueList.removeAllViews()
        if (feed.queues.isEmpty()) {
            val empty = LayoutInflater.from(this)
                .inflate(R.layout.item_queue, views.queueList, false)
            ItemQueueBinding.bind(empty).apply {
                queueTitle.text = getString(R.string.queue_empty)
                queueCount.visibility = View.GONE
                queueAction.visibility = View.GONE
                queueItems.visibility = View.GONE
            }
            views.queueList.addView(empty)
            return
        }

        for (queue in feed.queues) {
            val row = LayoutInflater.from(this).inflate(R.layout.item_queue, views.queueList, false)
            ItemQueueBinding.bind(row).apply {
                queueTitle.text = queue.title
                queueCount.text = queue.total.toString()
                queueCount.setTextColor(
                    ContextCompat.getColor(
                        this@MainActivity,
                        if (queue.total > 0) R.color.critical else R.color.ink_faint,
                    ),
                )
                queueAction.text = queue.action
                queueItems.text = if (queue.items.isEmpty()) {
                    // Antrean kosong tetap digambar: "nol peringatan menunggu" adalah kabar
                    // baik, dan menghilangkan barisnya membuat pembaca tidak dapat
                    // membedakan "tidak ada" dari "tidak diperiksa".
                    "Tidak ada yang menunggu."
                } else {
                    queue.items.joinToString("\n") { "• ${it.headline} — ${it.detail}" }
                }
            }
            views.queueList.addView(row)
        }
    }

    private fun signOut(reason: String?) {
        tokens.clear()
        showLogin(reason)
    }

    private fun showLogin(reason: String?) {
        views.homeGroup.visibility = View.GONE
        views.loginGroup.visibility = View.VISIBLE
        if (reason == null) hideLoginError() else showLoginError(reason)
    }

    private fun showLoginError(message: String) {
        views.loginError.text = message
        views.loginError.visibility = View.VISIBLE
    }

    private fun showLoginErrorOnHome(message: String) {
        views.queueNote.text = message
    }

    private fun hideLoginError() {
        views.loginError.visibility = View.GONE
    }

    private fun busy(active: Boolean) {
        views.spinner.visibility = if (active) View.VISIBLE else View.GONE
    }
}
