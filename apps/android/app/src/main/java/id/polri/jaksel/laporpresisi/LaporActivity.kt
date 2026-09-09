package id.polri.jaksel.laporpresisi

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.net.Uri
import android.os.Bundle
import android.os.Looper
import android.provider.OpenableColumns
import android.view.View
import android.widget.ArrayAdapter
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.laporpresisi.databinding.ActivityLaporBinding
import kotlinx.coroutines.launch

/**
 * Kanal laporan masyarakat (PHASE 17, TASK 170).
 *
 * ## Satu layar, satu pekerjaan
 *
 * Layar ini dibuka orang yang sedang ingin melaporkan sesuatu, sering dalam keadaan tidak
 * tenang. Setiap langkah tambahan adalah satu langkah lagi antara niat melapor dan laporan
 * terkirim — jadi tidak ada menu, tidak ada daftar, tidak ada tab. Layar muka aplikasi
 * hanya menawarkan dua pintu, dan pintu ini membuka langsung ke formulirnya.
 *
 * ## Yang tidak ada di sini, dan mengapa
 *
 * | Tidak ada | Alasannya |
 * |---|---|
 * | Pendaftaran dan akun | Kanal ini tanpa identitas (`docs/14` §3) |
 * | Riwayat laporan | Menampilkannya menuntut penyimpanan penanda di ponsel |
 *
 * Peringatan darurat diletakkan **di atas** formulir, bukan di bawah tombol kirim: orang
 * yang sedang panik tidak membaca catatan kaki.
 */
class LaporActivity : AppCompatActivity() {

    private companion object {
        /** Berapa lama menunggu satu titik sebelum menyerah. */
        const val LOCATION_TIMEOUT_MS = 20_000L
    }

    private lateinit var views: ActivityLaporBinding
    private var options: PublicApi.Options? = null

    /** Titik yang dibagikan pelapor; `null` selama ia belum menekan tombolnya. */
    private var shared: Location? = null

    /** Lampiran yang sudah dititipkan ke server, beserta nama berkasnya untuk ditampilkan. */
    private val staged = mutableListOf<Pair<PublicApi.Staged, String>>()

    /**
     * Izin lokasi diminta **saat tombolnya ditekan**, bukan saat layar dibuka.
     *
     * Dialog izin yang muncul sebelum pelapor tahu untuk apa lokasinya dipakai hanya
     * memberinya dua pilihan buruk: menolak sesuatu yang mungkin berguna, atau mengizinkan
     * sesuatu yang tidak ia mengerti.
     */
    private val askLocation =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
            if (granted.values.any { it }) {
                readLocation()
            } else {
                views.locationNote.text = getString(R.string.err_location_denied)
            }
        }

    /**
     * Pemilih berkas memakai `OpenDocument`, bukan `GetContent`.
     *
     * Keduanya membuka pemilih berkas sistem — yang berarti aplikasi ini **tidak pernah**
     * meminta izin membaca penyimpanan. Yang diberikan pengguna adalah satu berkas yang ia
     * pilih sendiri, bukan hak membaca seluruh isi ponselnya.
     */
    private val pickFiles =
        registerForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { chosen ->
            if (chosen.isNotEmpty()) upload(chosen)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        views = ActivityLaporBinding.inflate(layoutInflater)
        setContentView(views.root)

        views.sendButton.setOnClickListener { submit() }
        views.againButton.setOnClickListener { resetForAnother() }
        views.locationButton.setOnClickListener { onLocationPressed() }
        views.attachButton.setOnClickListener {
            pickFiles.launch(
                arrayOf("image/jpeg", "image/png", "image/webp", "audio/*", "video/mp4", "video/webm")
            )
        }

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
                        latitude = shared?.latitude,
                        longitude = shared?.longitude,
                        // Ketelitian hanya disertakan bila peranti melaporkannya. Menebak
                        // angkanya berarti menyatakan ketelitian yang tidak pernah diukur.
                        accuracyMetres = shared?.takeIf { it.hasAccuracy() }?.accuracy?.toDouble(),
                        attachments = staged.map { it.first.handle },
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
        // Kode klaim disimpan terenkripsi di ponsel ini, dan TIDAK ditampilkan.
        //
        // Menampilkannya hanya akan mengundang pelapor menyalinnya ke tempat yang tidak
        // aman, padahal aplikasi sudah menyimpannya dan memakainya sendiri. Yang perlu ia
        // ingat cukup nomor tiketnya — itu yang disebutkan kepada petugas.
        if (ticket.claimToken.isNotBlank()) {
            TiketStore(this).simpan(TiketStore.Tiket(ticket.code, ticket.claimToken))
        }
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
        // Lokasi dan lampiran ikut dilepas. Laporan berikutnya adalah kejadian yang lain;
        // membawa serta titik dan foto laporan sebelumnya akan menempelkan bukti yang salah
        // pada peristiwa yang salah — kesalahan yang tidak terlihat sampai ada yang
        // memeriksanya.
        clearLocation()
        staged.clear()
        renderAttachments()
        views.sentGroup.visibility = View.GONE
        views.formGroup.visibility = View.VISIBLE
    }

    // ---------------------------------------------------------------------------------
    // Lokasi
    // ---------------------------------------------------------------------------------

    private fun onLocationPressed() {
        if (shared != null) {
            clearLocation()
            return
        }
        val granted = listOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        ).any { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }

        if (granted) readLocation() else askLocation.launch(
            arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION,
            )
        )
    }

    /**
     * Mengambil satu titik, sekali saja.
     *
     * Memakai `LocationManager` bawaan, bukan pustaka lokasi Google: pustaka itu menuntut
     * Play Services yang tidak ada pada sebagian perangkat, dan aplikasi yang dipasang
     * warga sebaiknya membawa sesedikit mungkin yang tidak dapat mereka periksa.
     *
     * Titik terakhir yang diketahui **tidak** dipakai. Ia bisa berumur berjam-jam dan
     * menunjuk tempat yang sudah lama ditinggalkan — dan titik yang salah lebih buruk
     * daripada tidak ada titik, karena ia tetap dicatat sebagai "lokasi kejadian".
     */
    private fun readLocation() {
        val manager = getSystemService(LOCATION_SERVICE) as? LocationManager
        val provider = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .firstOrNull { runCatching { manager?.isProviderEnabled(it) == true }.getOrDefault(false) }

        if (manager == null || provider == null) {
            views.locationNote.text = getString(R.string.err_location)
            return
        }

        views.locationButton.isEnabled = false
        views.locationButton.text = getString(R.string.sharing_location)

        val listener = object : android.location.LocationListener {
            override fun onLocationChanged(location: Location) {
                manager.removeUpdates(this)
                shared = location
                renderLocation()
            }

            // Tiga metode berikut kosong tetapi WAJIB ada di Android 24–29: tanpa
            // implementasinya, sistem melempar AbstractMethodError saat penyedia lokasi
            // berubah keadaan.
            @Deprecated("Diperlukan API 24–29")
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit

            override fun onProviderEnabled(provider: String) = Unit

            override fun onProviderDisabled(provider: String) {
                manager.removeUpdates(this)
                views.locationButton.isEnabled = true
                views.locationButton.text = getString(R.string.share_location)
                views.locationNote.text = getString(R.string.err_location)
            }
        }

        try {
            manager.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
        } catch (_: SecurityException) {
            views.locationButton.isEnabled = true
            views.locationButton.text = getString(R.string.share_location)
            views.locationNote.text = getString(R.string.err_location_denied)
            return
        }

        // Batas waktu supaya pelapor tidak menunggu tanpa kepastian di dalam ruangan, di
        // mana sinyal satelit sering tidak pernah datang sama sekali.
        views.locationButton.postDelayed({
            if (shared == null) {
                manager.removeUpdates(listener)
                views.locationButton.isEnabled = true
                views.locationButton.text = getString(R.string.share_location)
                views.locationNote.text = getString(R.string.err_location)
            }
        }, LOCATION_TIMEOUT_MS)
    }

    private fun renderLocation() {
        val location = shared
        views.locationButton.isEnabled = true

        if (location == null) {
            views.locationText.visibility = View.GONE
            views.locationButton.text = getString(R.string.share_location)
            views.locationNote.text = getString(R.string.location_note)
            return
        }

        views.locationText.visibility = View.VISIBLE
        views.locationText.text = String.format(
            java.util.Locale.US,
            "%.5f, %.5f (±%.0f m)",
            location.latitude,
            location.longitude,
            if (location.hasAccuracy()) location.accuracy else 0f,
        )
        views.locationButton.text = getString(R.string.clear_location)
        views.locationNote.text = getString(R.string.location_note)
    }

    private fun clearLocation() {
        shared = null
        renderLocation()
    }

    // ---------------------------------------------------------------------------------
    // Lampiran
    // ---------------------------------------------------------------------------------

    private fun upload(chosen: List<Uri>) {
        val limits = options ?: return
        views.attachButton.isEnabled = false
        views.attachButton.text = getString(R.string.uploading)

        lifecycleScope.launch {
            for (uri in chosen) {
                if (staged.size >= limits.maxAttachments) break

                val name = displayName(uri)
                val size = fileSize(uri)
                // Diperiksa di ponsel lebih dulu supaya berkas besar tidak dikirim sia-sia
                // lewat jaringan seluler. Server tetap memeriksanya sendiri — ini
                // kenyamanan, bukan pengaman.
                if (size != null && limits.maxAttachmentBytes > 0 && size > limits.maxAttachmentBytes) {
                    showError("$name melebihi batas ${limits.maxAttachmentBytes / (1024 * 1024)} MB.")
                    continue
                }

                try {
                    val stream = contentResolver.openInputStream(uri) ?: continue
                    val media = contentResolver.getType(uri) ?: "application/octet-stream"
                    val result = stream.use {
                        PublicApi.stage(BuildConfig.API_BASE, it, name, media)
                    }
                    staged += result to name
                } catch (failure: PublicApi.ApiFailure) {
                    showError("$name: ${failure.readable}")
                }
            }

            renderAttachments()
            views.attachButton.isEnabled = staged.size < limits.maxAttachments
            views.attachButton.text = getString(
                if (staged.size >= limits.maxAttachments) R.string.attachments_full
                else R.string.pick_file
            )
        }
    }

    private fun renderAttachments() {
        if (staged.isEmpty()) {
            views.attachmentList.visibility = View.GONE
            views.attachButton.isEnabled = true
            views.attachButton.text = getString(R.string.pick_file)
            return
        }
        views.attachmentList.visibility = View.VISIBLE
        views.attachmentList.text = staged.joinToString("\n") { (file, name) ->
            "• $name — ${maxOf(1L, file.byteSize / 1024)} KB"
        }
    }

    /** Nama berkas menurut penyedianya; jatuh ke nama umum bila tidak ada. */
    private fun displayName(uri: Uri): String {
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (column >= 0 && cursor.moveToFirst()) return cursor.getString(column)
        }
        return uri.lastPathSegment ?: "berkas"
    }

    private fun fileSize(uri: Uri): Long? {
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val column = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (column >= 0 && cursor.moveToFirst() && !cursor.isNull(column)) {
                return cursor.getLong(column)
            }
        }
        return null
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
