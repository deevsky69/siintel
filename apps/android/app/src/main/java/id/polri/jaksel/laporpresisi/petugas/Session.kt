package id.polri.jaksel.laporpresisi.petugas

/**
 * Apa yang dibutuhkan [Session] dari penyimpanan token.
 *
 * Antarmuka ini ada supaya aturan pembaruan sesi dapat diuji tanpa Android: implementasi
 * sesungguhnya ([TokenStore]) memerlukan `Context` dan keystore perangkat, yang tidak
 * tersedia pada unit test JVM. Aturan yang tidak dapat diuji cenderung tidak diuji.
 */
interface Tokens {
    var accessToken: String?
    var refreshToken: String?
    fun clear()
}

/**
 * Sesi petugas: menjalankan permintaan ber-token dan memperbarui token yang kedaluwarsa.
 *
 * Access token berumur 15 menit, sedangkan aplikasi ini dibuka petugas beberapa kali sehari.
 * Hampir setiap kali dibuka, token yang tersimpan sudah mati. Menyerahkan itu kepada
 * pengguna berarti meminta kata sandi diketik ulang di tempat terbuka, berkali-kali sehari —
 * yang dalam praktiknya berarti aplikasinya tidak dipakai.
 *
 * Karena itu penolakan `401` **tidak langsung** dianggap sebagai akhir sesi. Ia ditukar
 * sekali dengan refresh token, dan hanya bila penukaran itu pun ditolak barulah pengguna
 * diminta masuk kembali.
 */
class Session(private val base: String, private val tokens: Tokens) {

    /**
     * Menjalankan [request] dengan access token yang tersimpan; bila server menolaknya
     * dengan `401`, menukar refresh token dengan access token baru lalu mencobanya
     * **sekali lagi**.
     *
     * Percobaan ulang dibatasi satu kali dengan sengaja. Token yang baru saja diterbitkan
     * server tetapi tetap ditolak berarti persoalannya bukan kedaluwarsa — mengulanginya
     * hanya menghasilkan gelung yang tidak pernah berhenti sementara pengguna menatap
     * pemutar yang berputar terus.
     *
     * Kegagalan yang bukan `401` diteruskan apa adanya. Sinyal yang buruk bukan alasan untuk
     * menjatuhkan sesi yang masih sah.
     */
    suspend fun <T> run(request: suspend (String) -> T): T {
        val token = tokens.accessToken ?: throw Api.Failure(EXPIRED, unauthorized = true)

        return try {
            request(token)
        } catch (failure: Api.Failure) {
            if (!failure.unauthorized) throw failure
            // Sesi dari versi lama aplikasi tidak menyimpan refresh token. Galat aslinya
            // diteruskan supaya pengguna diminta masuk kembali, bukan ditelan diam-diam.
            val refresh = tokens.refreshToken ?: throw failure
            val renewed = Api.refresh(base, refresh)
            tokens.accessToken = renewed
            request(renewed)
        }
    }

    companion object {
        /** Ditimpa layar dengan kalimat dari `strings.xml` sebelum sampai ke pengguna. */
        const val EXPIRED = "Sesi berakhir."
    }
}
