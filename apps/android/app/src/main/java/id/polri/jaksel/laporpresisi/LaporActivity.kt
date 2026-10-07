package id.polri.jaksel.laporpresisi

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
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
 *
 * ## Compose (7 Oktober 2026)
 *
 * Tampilan ada di [LaporScreen]; Activity ini memegang [LaporState] dan segala yang
 * menyentuh Android — izin, `LocationManager`, pemilih berkas, `ContentResolver`,
 * `TiketStore` — lalu menyalurkannya sebagai perubahan keadaan.
 */
class LaporActivity : ComponentActivity() {

    private companion object {
        /** Berapa lama menunggu satu titik sebelum menyerah. */
        const val LOCATION_TIMEOUT_MS = 20_000L
    }

    private var state by mutableStateOf(LaporState())

    /** Titik yang dibagikan pelapor; `null` selama ia belum menekan tombolnya. */
    private var shared: Location? = null

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
                state = state.copy(locationNote = getString(R.string.err_location_denied))
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

    private val actions = LaporActions(
        onCategory = { state = state.copy(category = it, error = null) },
        onKecamatan = {
            // Kelurahan ikut dikosongkan: kelurahan milik kecamatan sebelumnya tidak sah
            // untuk kecamatan yang baru.
            state = state.copy(kecamatan = it, kelurahan = "", kelurahanSuggestion = null, error = null)
        },
        onKelurahan = { state = state.copy(kelurahan = it, kelurahanSuggestion = null) },
        onPlace = { state = state.copy(place = it) },
        onStory = { state = state.copy(story = it, error = null) },
        onLocation = ::onLocationPressed,
        onPickFiles = {
            pickFiles.launch(
                arrayOf("image/jpeg", "image/png", "image/webp", "audio/*", "video/mp4", "video/webm"),
            )
        },
        onSend = ::submit,
        onAgain = ::resetForAnother,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { PresisiTheme { LaporScreen(state, actions) } }
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
        state = state.copy(busy = true)
        lifecycleScope.launch {
            try {
                state = state.copy(options = PublicApi.options(BuildConfig.API_BASE), optionsFailed = false)
            } catch (_: PublicApi.ApiFailure) {
                state = state.copy(optionsFailed = true)
            } finally {
                state = state.copy(busy = false)
            }
        }
    }

    private fun submit() {
        // Pengiriman mustahil sebelum pilihan termuat: tanpa daftar kategori dan kecamatan
        // dari server, tidak ada nilai sah yang bisa dikirim.
        if (state.options == null) return
        val story = state.story.trim()
        if (state.category.isBlank() || state.kecamatan.isBlank() || story.isBlank()) {
            state = state.copy(error = getString(R.string.err_incomplete))
            return
        }
        // Ambang yang sama dijaga backend (`min_length=10`). Diperiksa juga di sini bukan
        // sebagai pengaman melainkan agar pelapor tahu sebelum menunggu perjalanan jaringan.
        if (story.length < 10) {
            state = state.copy(error = getString(R.string.err_short))
            return
        }

        state = state.copy(error = null, sending = true, busy = true)
        lifecycleScope.launch {
            try {
                val ticket = PublicApi.submit(
                    BuildConfig.API_BASE,
                    ReportDraft(
                        category = state.category,
                        area = state.kecamatan,
                        place = state.place.trim(),
                        story = story,
                        latitude = shared?.latitude,
                        longitude = shared?.longitude,
                        // Ketelitian hanya disertakan bila peranti melaporkannya. Menebak
                        // angkanya berarti menyatakan ketelitian yang tidak pernah diukur.
                        accuracyMetres = shared?.takeIf { it.hasAccuracy() }?.accuracy?.toDouble(),
                        attachments = state.attachments.map { it.staged.handle },
                        kelurahan = state.kelurahan,
                    ),
                )
                showTicket(ticket)
            } catch (failure: PublicApi.ApiFailure) {
                state = state.copy(error = failure.readable)
            } finally {
                state = state.copy(sending = false, busy = false)
            }
        }
    }

    private fun showTicket(ticket: PublicApi.Ticket) {
        // Kode klaim disimpan terenkripsi di ponsel ini, dan TIDAK ditampilkan.
        //
        // Menampilkannya hanya akan mengundang pelapor menyalinnya ke tempat yang tidak
        // aman, padahal aplikasi sudah menyimpannya dan memakainya sendiri. Yang perlu ia
        // ingat cukup nomor tiketnya — itu yang disebutkan kepada petugas.
        if (ticket.claimToken.isNotBlank()) {
            TiketStore(this).simpan(TiketStore.Tiket(ticket.code, ticket.claimToken))
        }
        state = state.copy(ticket = ticket.code, error = null)
    }

    /**
     * Menyiapkan formulir untuk laporan berikutnya.
     *
     * Isian dikosongkan seluruhnya. Membiarkan keterangan sebelumnya tertinggal akan
     * membuat laporan kedua tidak sengaja mengulang isi laporan pertama — dan pada kanal
     * tanpa identitas, laporan berulang tidak dapat dibedakan dari laporan sungguhan.
     * Lokasi dan lampiran ikut dilepas: laporan berikutnya adalah kejadian yang lain, dan
     * membawa serta titik dan foto laporan sebelumnya menempelkan bukti yang salah pada
     * peristiwa yang salah.
     */
    private fun resetForAnother() {
        shared = null
        state = LaporState(options = state.options)
    }

    // ---------------------------------------------------------------------------------
    // Lokasi
    // ---------------------------------------------------------------------------------

    private fun onLocationPressed() {
        if (shared != null) {
            clearLocation()
            return
        }
        val permissions = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        val granted = permissions.any {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
        if (granted) readLocation() else askLocation.launch(permissions)
    }

    /**
     * Mengambil satu titik, sekali saja.
     *
     * Memakai `LocationManager` bawaan, bukan pustaka lokasi Google: pustaka itu menuntut
     * Google Play Services — yang tidak ada pada sebagian perangkat, tidak ada pada
     * emulator baku, dan menambah ketergantungan pada satu perusahaan untuk aplikasi
     * yang dipasang warga.
     */
    private fun readLocation() {
        val manager = getSystemService(LOCATION_SERVICE) as? LocationManager
        val provider = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .firstOrNull { runCatching { manager?.isProviderEnabled(it) == true }.getOrDefault(false) }
        if (manager == null || provider == null) {
            state = state.copy(locationNote = getString(R.string.err_location))
            return
        }
        state = state.copy(locationBusy = true, locationNote = null)

        val listener = object : android.location.LocationListener {
            override fun onLocationChanged(location: Location) {
                manager.removeUpdates(this)
                shared = location
                state = state.copy(
                    location = SharedPoint(
                        location.latitude,
                        location.longitude,
                        if (location.hasAccuracy()) location.accuracy.toDouble() else null,
                    ),
                    locationBusy = false,
                    locationNote = null,
                )
                suggestAreaFrom(location)
            }

            // Tiga metode berikut kosong tetapi WAJIB ada di Android 24–29: tanpa
            // implementasinya, sistem melempar AbstractMethodError saat penyedia lokasi
            // berubah keadaan.
            @Deprecated("Diperlukan API 24–29")
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
            override fun onProviderEnabled(provider: String) = Unit
            override fun onProviderDisabled(provider: String) {
                manager.removeUpdates(this)
                state = state.copy(locationBusy = false, locationNote = getString(R.string.err_location))
            }
        }
        try {
            manager.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
        } catch (_: SecurityException) {
            state = state.copy(locationBusy = false, locationNote = getString(R.string.err_location_denied))
            return
        }
        // Batas waktu supaya pelapor tidak menunggu tanpa kepastian di dalam ruangan, di
        // mana sinyal satelit sering tidak pernah datang sama sekali.
        Handler(Looper.getMainLooper()).postDelayed({
            if (shared == null && state.locationBusy) {
                manager.removeUpdates(listener)
                state = state.copy(locationBusy = false, locationNote = getString(R.string.err_location))
            }
        }, LOCATION_TIMEOUT_MS)
    }

    private fun clearLocation() {
        shared = null
        state = state.copy(location = null, locationBusy = false, locationNote = null, kelurahanSuggestion = null)
    }

    /**
     * Lokasi yang dibagikan mengusulkan kecamatan dan kelurahan terdekat. Pelapor tetap
     * dapat mengubah keduanya; catatan di bawah pemilih menyebut bahwa ini usulan.
     */
    private fun suggestAreaFrom(location: Location) {
        val areas = state.options?.detailedAreas.orEmpty()
        val nearest = AreaNearest.nearest(areas, location.latitude, location.longitude) ?: return
        state = state.copy(
            kecamatan = nearest.kecamatan,
            kelurahan = nearest.kelurahan,
            kelurahanSuggestion = getString(
                R.string.kelurahan_suggested,
                nearest.kelurahan,
                nearest.distanceM.toInt(),
            ),
        )
    }

    // ---------------------------------------------------------------------------------
    // Lampiran
    // ---------------------------------------------------------------------------------

    private fun upload(chosen: List<Uri>) {
        val limits = state.options ?: return
        state = state.copy(uploading = true)

        lifecycleScope.launch {
            for (uri in chosen) {
                if (state.attachments.size >= limits.maxAttachments) break

                val name = displayName(uri)
                val size = fileSize(uri)
                // Diperiksa di ponsel lebih dulu supaya berkas besar tidak dikirim sia-sia
                // lewat jaringan seluler. Server tetap memeriksanya sendiri — ini
                // kenyamanan, bukan pengaman.
                if (size != null && limits.maxAttachmentBytes > 0 && size > limits.maxAttachmentBytes) {
                    state = state.copy(error = "$name melebihi batas ${limits.maxAttachmentBytes / (1024 * 1024)} MB.")
                    continue
                }

                try {
                    val stream = contentResolver.openInputStream(uri) ?: continue
                    val media = contentResolver.getType(uri) ?: "application/octet-stream"
                    val result = stream.use { PublicApi.stage(BuildConfig.API_BASE, it, name, media) }
                    state = state.copy(attachments = state.attachments + StagedFile(result, name))
                } catch (failure: PublicApi.ApiFailure) {
                    state = state.copy(error = "$name: ${failure.readable}")
                }
            }
            state = state.copy(uploading = false)
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
}
