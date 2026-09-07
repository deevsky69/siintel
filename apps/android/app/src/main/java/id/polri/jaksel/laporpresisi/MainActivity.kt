package id.polri.jaksel.laporpresisi

import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.laporpresisi.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

/**
 * LAPOR PRESISI — satu layar, satu pekerjaan (PHASE 17, TASK 170).
 *
 * ## Mengapa hanya satu layar
 *
 * Aplikasi ini dipasang orang yang sedang ingin melaporkan sesuatu, sering dalam keadaan
 * tidak tenang. Setiap layar tambahan — beranda, menu, daftar riwayat — adalah satu langkah
 * lagi antara niat melapor dan laporan terkirim. Karena itu tidak ada beranda: aplikasi
 * dibuka langsung pada formulirnya.
 *
 * ## Yang tidak ada di sini, dan mengapa
 *
 * | Tidak ada | Alasannya |
 * |---|---|
 * | Pendaftaran dan akun | Kanal ini tanpa identitas (`docs/14` §3) |
 * | Izin lokasi | Lokasi sebatas kecamatan yang dipilih sendiri; izin GPS meminta kepercayaan untuk sesuatu yang tidak dipakai |
 * | Kamera dan lampiran | Menyimpan berkas warga menyentuh retensi dan klasifikasi data — keputusan kebijakan yang belum diambil |
 * | Riwayat laporan | Menampilkannya menuntut penyimpanan penanda di ponsel; nomor tiket sudah cukup, dan ia tidak mengikat ke siapa pun |
 *
 * Peringatan darurat diletakkan **di atas** formulir, bukan di bawah tombol kirim: orang
 * yang sedang panik tidak membaca catatan kaki.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var views: ActivityMainBinding
    private var options: PublicApi.Options? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        views = ActivityMainBinding.inflate(layoutInflater)
        setContentView(views.root)

        views.sendButton.setOnClickListener { submit() }
        views.againButton.setOnClickListener { resetForAnother() }

        loadOptions()
    }

    /**
     * Pilihan isian diambil dari server, tidak ditanam di aplikasi.
     *
     * Daftar kategori dan kecamatan hidup di `config/taxonomy/mappings.yaml` dan master
     * lokasi. Menyalinnya ke dalam APK berarti setiap perubahan menuntut pemasangan ulang
     * di setiap ponsel — dan sampai itu terjadi, warga mengirim kategori yang sudah tidak
     * dikenal server.
     */
    private fun loadOptions() {
        setBusy(true)
        lifecycleScope.launch {
            try {
                val loaded = PublicApi.options(BuildConfig.API_BASE)
                options = loaded
                fill(views.categorySpinner, loaded.categories)
                fill(views.areaSpinner, loaded.areas)
                views.formGroup.visibility = View.VISIBLE
            } catch (failure: PublicApi.ApiFailure) {
                views.formGroup.visibility = View.GONE
                showError(getString(R.string.err_options))
            } finally {
                setBusy(false)
            }
        }
    }

    private fun submit() {
        // Pengiriman mustahil sebelum pilihan termuat: tanpa daftar kategori dan kecamatan
        // dari server, tidak ada nilai sah yang bisa dikirim.
        if (options == null) return
        val category = views.categorySpinner.selectedItem?.toString().orEmpty()
        val area = views.areaSpinner.selectedItem?.toString().orEmpty()
        val story = views.storyInput.text.toString().trim()

        if (category.isBlank() || area.isBlank() || story.isBlank()) {
            showError(getString(R.string.err_incomplete))
            return
        }
        // Ambang yang sama dijaga backend (`min_length=10`). Diperiksa juga di sini bukan
        // sebagai pengaman melainkan agar pelapor tahu sebelum menunggu perjalanan jaringan.
        if (story.length < 10) {
            showError(getString(R.string.err_short))
            return
        }

        hideError()
        setBusy(true)
        views.sendButton.isEnabled = false
        views.sendButton.text = getString(R.string.sending)

        lifecycleScope.launch {
            try {
                val ticket = PublicApi.submit(
                    BuildConfig.API_BASE,
                    ReportDraft(
                        category = category,
                        area = area,
                        place = views.placeInput.text.toString().trim(),
                        story = story,
                    ),
                )
                showTicket(ticket)
            } catch (failure: PublicApi.ApiFailure) {
                showError(failure.readable)
            } finally {
                setBusy(false)
                views.sendButton.isEnabled = true
                views.sendButton.text = getString(R.string.send)
            }
        }
    }

    private fun showTicket(ticket: PublicApi.Ticket) {
        views.ticketText.text = ticket.code
        views.formGroup.visibility = View.GONE
        views.sentGroup.visibility = View.VISIBLE
        hideError()
    }

    /**
     * Menyiapkan formulir untuk laporan berikutnya.
     *
     * Isian dikosongkan seluruhnya. Membiarkan keterangan sebelumnya tertinggal akan
     * membuat laporan kedua tidak sengaja mengulang isi laporan pertama — dan pada kanal
     * tanpa identitas, laporan berulang tidak dapat dibedakan dari laporan sungguhan.
     */
    private fun resetForAnother() {
        views.storyInput.text?.clear()
        views.placeInput.text?.clear()
        views.sentGroup.visibility = View.GONE
        views.formGroup.visibility = View.VISIBLE
    }

    private fun fill(spinner: android.widget.Spinner, values: List<String>) {
        spinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            values,
        )
    }

    private fun setBusy(busy: Boolean) {
        views.spinner.visibility = if (busy) View.VISIBLE else View.GONE
    }

    private fun showError(message: String) {
        views.errorText.text = message
        views.errorText.visibility = View.VISIBLE
    }

    private fun hideError() {
        views.errorText.visibility = View.GONE
    }
}
