package id.polri.jaksel.laporpresisi

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import id.polri.jaksel.laporpresisi.databinding.ActivityHomeBinding
import id.polri.jaksel.laporpresisi.petugas.PetugasActivity

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
    }
}
