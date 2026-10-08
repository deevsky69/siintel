package id.polri.jaksel.laporpresisi

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.laporpresisi.petugas.PetugasActivity
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import kotlinx.coroutines.launch

/**
 * Layar muka: dua pintu, dan tidak lebih.
 *
 * ## Mengapa satu aplikasi, bukan dua
 *
 * Sampai 8 September 2026 ada dua APK terpisah — satu untuk warga, satu untuk petugas.
 * Pemisahan itu punya alasan: warga tidak perlu memasang kode berkewenangan di ponselnya.
 * Pemilik proyek meminta keduanya disatukan, dan permintaannya masuk akal untuk paparan:
 * satu tautan pemasangan, satu ikon, satu hal yang harus dijelaskan.
 *
 * Yang hilang dan yang tidak, dinyatakan terbuka:
 *
 * - **Tidak hilang:** kewenangan. Layar petugas tetap menuntut masuk, dan setiap
 *   permintaannya diperiksa server. Kode yang terpasang di ponsel tidak pernah menjadi
 *   kewenangan — yang menentukan adalah token, dan token hanya lahir dari kredensial.
 * - **Hilang:** jaminan bahwa ponsel warga tidak memuat layar masuk sama sekali. Sekarang
 *   ia memuatnya, dan yang menjaganya hanyalah bahwa layar itu tidak berguna tanpa akun.
 *
 * ## Mengapa layar ini ada sama sekali
 *
 * Membuka langsung ke formulir laporan akan menyembunyikan pintu petugas, dan membuka
 * langsung ke layar masuk akan menyuruh warga memasukkan kredensial yang tidak ia punya.
 * Dua tombol adalah harga terkecil yang dapat dibayar untuk melayani keduanya.
 *
 * Nomor darurat disebut di sini, bukan hanya di dalam formulir: orang yang salah membuka
 * aplikasi ini saat keadaan mendesak harus membaca "110" sebelum ia menekan apa pun.
 *
 * ## Imbauan yang sedang berlaku — "info sekitar" (spesifikasi §4)
 *
 * Ditambahkan 9 September 2026, setelah kanal imbauan dibangun. Ia diletakkan SEBELUM
 * tombol lapor dengan sengaja: warga yang membuka aplikasi karena melihat sesuatu perlu
 * tahu lebih dulu apakah hal itu sudah diketahui satuan.
 *
 * Ini satu-satunya isi kamtibmas yang ditampilkan tanpa akun, dan ia boleh ditampilkan
 * justru karena setiap barisnya sudah melewati keputusan publikasi oleh pejabat berwenang.
 * Peringatan dini yang belum diumumkan tidak pernah sampai ke sini, dan tidak ada satu
 * angka pun yang ikut — tanpa skor, tanpa grid, tanpa kode peringatan internal.
 *
 * Kegagalan jaringan tidak menghalangi apa pun: bagiannya sekadar tidak muncul. Layar muka
 * harus tetap menawarkan tombol lapor pada jaringan terburuk sekalipun.
 *
 * ## Compose (7 Oktober 2026)
 *
 * Layar pertama yang dipindahkan dari XML ke Jetpack Compose, dan menjadi pola bagi
 * layar lain: Activity memegang data dan jaringan dalam `mutableStateOf`, tampilan ada di
 * [HomeScreen] yang murni dan dapat dipratinjau. Tidak ada ViewModel: layar ini tidak
 * punya keadaan yang perlu selamat dari rotasi selain yang dimuat ulang pada `onResume`.
 */
class MainActivity : ComponentActivity() {

    private var state by mutableStateOf(HomeState(version = BuildConfig.VERSION_NAME))

    /** Izin lokasi diminta saat tombol darurat dikonfirmasi; ditolak pun permintaan tetap dikirim. */
    private val askLocation =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
            if (granted.values.any { it }) locateThenSend() else sendPanic(null)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            PresisiTheme {
                HomeScreen(
                    state = state,
                    onReport = { startActivity(Intent(this, LaporActivity::class.java)) },
                    onOfficer = { startActivity(Intent(this, PetugasActivity::class.java)) },
                    onCheckStatus = ::periksaStatus,
                    onPanicPress = { state = state.copy(panic = PanicState.Confirming) },
                    onPanicCancel = { state = state.copy(panic = PanicState.Idle) },
                    onPanicNote = { state = state.copy(panicNote = it) },
                    onPanicConfirm = ::confirmPanic,
                )
            }
        }
    }

    /**
     * Memuat imbauan setiap kali layar muka kembali tampak, bukan sekali saat dibuat.
     *
     * Warga yang baru selesai mengirim laporan kembali ke layar ini; imbauan yang terbit
     * di sela itu harus ikut terlihat tanpa perlu menutup aplikasi.
     */
    override fun onResume() {
        super.onResume()
        muatImbauan()
        tampilkanTombolStatus()
    }

    /**
     * Tombol cek status hanya muncul bila ponsel ini pernah mengirim laporan.
     *
     * Kode klaim tersimpan di ponsel, bukan di server — jadi ponsel yang belum pernah
     * melapor memang tidak punya apa pun untuk diperiksa. Tombol yang pasti menjawab
     * "tidak ada" membuat orang mengira aplikasinya rusak.
     */
    private fun tampilkanTombolStatus() {
        val ada = TiketStore(this).semua().isNotEmpty()
        state = state.copy(hasTicket = ada, statusResult = if (ada) state.statusResult else null)
    }

    /**
     * Memeriksa status laporan terakhir yang dikirim dari ponsel ini.
     *
     * Tiket yang sudah tidak dikenal server — misalnya karena basis data demo di-seed
     * ulang — DIHAPUS dari ponsel. Menyimpannya terus membuat tombol ini selamanya
     * menjawab gagal, dan pelapor tidak punya cara tahu bahwa penyebabnya bukan jaringan.
     */
    private fun periksaStatus() {
        val store = TiketStore(this)
        val tiket = store.semua().firstOrNull() ?: return
        state = state.copy(statusResult = getString(R.string.home_status_checking))

        lifecycleScope.launch {
            val status = PublicApi.statusLaporan(BuildConfig.API_BASE, tiket.code, tiket.claimToken)
            state = state.copy(
                statusResult = if (status == null) {
                    getString(R.string.home_status_none)
                } else {
                    "${status.code} · ${status.statusLabel}\n${status.basis}"
                },
            )
        }
    }

    private fun muatImbauan() {
        lifecycleScope.launch {
            // Disembunyikan seluruhnya bila kosong — termasuk ketika kosongnya karena
            // jaringan gagal. Judul tanpa isi terbaca seperti aplikasi yang rusak.
            state = state.copy(alerts = PublicApi.imbauan(BuildConfig.API_BASE).take(MAX_ALERTS))
        }
    }

    // ---------------------------------------------------------------------------------
    // Tombol darurat (8 Oktober 2026)
    // ---------------------------------------------------------------------------------

    private fun confirmPanic() {
        state = state.copy(panic = PanicState.Sending)
        val permissions = arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        val granted = permissions.any { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }
        if (granted) locateThenSend() else askLocation.launch(permissions)
    }

    /**
     * Mencari titik secepat mungkin: titik terakhir yang diketahui dipakai bila ada (umur
     * berapa pun — pada keadaan darurat titik lima menit lalu lebih berharga daripada tidak
     * ada), bila tidak ada menunggu penyedia paling lama [PANIC_LOCATION_WAIT_MS], lalu kirim
     * apa pun hasilnya. Permintaan TIDAK PERNAH tertahan oleh lokasi.
     */
    private fun locateThenSend() {
        val manager = getSystemService(LOCATION_SERVICE) as? LocationManager
        if (manager == null) return sendPanic(null)
        val providers = buildList {
            add(LocationManager.GPS_PROVIDER)
            add(LocationManager.NETWORK_PROVIDER)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) add(LocationManager.FUSED_PROVIDER)
        }.filter { runCatching { manager.isProviderEnabled(it) }.getOrDefault(false) }
        try {
            val recent = providers.mapNotNull { manager.getLastKnownLocation(it) }.maxByOrNull { it.time }
            if (recent != null) return sendPanic(recent)
            if (providers.isEmpty()) return sendPanic(null)
            var sent = false
            val listener = object : android.location.LocationListener {
                override fun onLocationChanged(location: Location) {
                    manager.removeUpdates(this)
                    if (!sent) {
                        sent = true
                        sendPanic(location)
                    }
                }

                @Deprecated("Diperlukan API 24–29")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
                override fun onProviderEnabled(provider: String) = Unit
                override fun onProviderDisabled(provider: String) = Unit
            }
            for (provider in providers) manager.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
            Handler(Looper.getMainLooper()).postDelayed({
                if (!sent) {
                    sent = true
                    manager.removeUpdates(listener)
                    sendPanic(null)
                }
            }, PANIC_LOCATION_WAIT_MS)
        } catch (_: SecurityException) {
            sendPanic(null)
        }
    }

    private fun sendPanic(location: Location?) {
        lifecycleScope.launch {
            try {
                val receipt = PublicApi.panic(
                    BuildConfig.API_BASE,
                    location?.latitude,
                    location?.longitude,
                    location?.takeIf { it.hasAccuracy() }?.accuracy?.toDouble(),
                    state.panicNote,
                )
                val area = listOf(receipt.kelurahan, receipt.kecamatan)
                    .filter { it.isNotBlank() }
                    .joinToString(", ")
                    .ifBlank { null }
                state = state.copy(panic = PanicState.Sent(receipt.code, area), panicNote = "")
            } catch (failure: PublicApi.ApiFailure) {
                state = state.copy(panic = PanicState.Failed(failure.readable))
            }
        }
    }

    private companion object {
        /** Layar muka bukan arsip: yang berguna dibaca adalah yang paling dekat berlaku. */
        const val MAX_ALERTS = 3

        /** Berapa lama menunggu titik baru sebelum permintaan darurat dikirim tanpa titik. */
        const val PANIC_LOCATION_WAIT_MS = 8_000L
    }
}
