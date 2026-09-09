package id.polri.jaksel.laporpresisi

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import id.polri.jaksel.laporpresisi.databinding.ActivityHomeBinding
import id.polri.jaksel.laporpresisi.databinding.ItemAlertBinding
import id.polri.jaksel.laporpresisi.petugas.PetugasActivity
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
 */
class MainActivity : AppCompatActivity() {

    private lateinit var views: ActivityHomeBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        views = ActivityHomeBinding.inflate(layoutInflater)
        setContentView(views.root)

        views.versionText.text =
            getString(R.string.version_label) + " ${BuildConfig.VERSION_NAME}"

        views.reportButton.setOnClickListener {
            startActivity(Intent(this, LaporActivity::class.java))
        }
        views.officerButton.setOnClickListener {
            startActivity(Intent(this, PetugasActivity::class.java))
        }

        views.statusButton.setOnClickListener { periksaStatus() }

        muatImbauan()
        tampilkanTombolStatus()
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
        views.statusButton.visibility = if (ada) View.VISIBLE else View.GONE
        if (!ada) views.statusResult.visibility = View.GONE
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

        views.statusResult.visibility = View.VISIBLE
        views.statusResult.text = getString(R.string.home_status_checking)

        lifecycleScope.launch {
            val status = PublicApi.statusLaporan(BuildConfig.API_BASE, tiket.code, tiket.claimToken)
            views.statusResult.text = if (status == null) {
                getString(R.string.home_status_none)
            } else {
                "${status.code} · ${status.statusLabel}\n${status.basis}"
            }
        }
    }

    private fun muatImbauan() {
        lifecycleScope.launch {
            val imbauan = PublicApi.imbauan(BuildConfig.API_BASE)
            views.alertList.removeAllViews()

            // Disembunyikan seluruhnya bila kosong — termasuk ketika kosongnya karena
            // jaringan gagal. Judul tanpa isi terbaca seperti aplikasi yang rusak.
            views.alertSection.visibility = if (imbauan.isEmpty()) View.GONE else View.VISIBLE

            for (row in imbauan.take(MAX_ALERTS)) {
                val card = ItemAlertBinding.inflate(layoutInflater, views.alertList, true)
                val jam = row.timeWindow?.let { " · $it WIB" } ?: ""
                card.alertHeadline.text = "${row.threatType} · ${row.areaText}$jam"
                card.alertMessage.text = row.message
            }
        }
    }

    private companion object {
        /** Layar muka bukan arsip: yang berguna dibaca adalah yang paling dekat berlaku. */
        const val MAX_ALERTS = 3
    }
}
