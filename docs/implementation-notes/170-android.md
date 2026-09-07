# 170 — Aplikasi Android

> **Status:** TECHNICAL DECISION
> **Fase:** PHASE 17 (TASK 170 dan TASK 171)
> **Terakhir diperbarui:** 7 September 2026

---

## 1. Dua aplikasi, bukan satu

| Modul Gradle | Nama | `applicationId` | Untuk siapa | Autentikasi |
|---|---|---|---|---|
| `app` | LAPOR PRESISI | `id.polri.jaksel.laporpresisi` | Masyarakat | Tidak ada |
| `petugas` | PRESISI Petugas | `id.polri.jaksel.presisi` | Personel | Ada |

Keduanya dipisah karena pemakainya berbeda secara mendasar. Menggabungkannya berarti
memasang kode berkewenangan di ponsel warga, dan meminta warga melewati layar masuk yang
tidak akan pernah mereka pakai. `applicationId` yang berbeda juga membuat keduanya dapat
terpasang berdampingan pada satu ponsel — berguna saat paparan.

Keduanya berbicara ke API yang sama lewat HTTPS. Tidak ada kode yang dibagi antara keduanya
dan tidak ada yang dibagi dengan web; yang dibagi hanyalah kontrak API.

---

## 2. Sesi petugas: dua token

Server menerbitkan dua token dengan umur yang jauh berbeda:

```text
access token   15 menit   dibawa pada tiap permintaan sebagai Authorization: Bearer
refresh token  7 hari     hanya untuk menukar access token yang kedaluwarsa
```

### 2.1 Mengapa refresh token harus dipakai

Aplikasi petugas dibuka beberapa kali sehari, sering kali berjam-jam setelah pemakaian
terakhir. Tanpa pembaruan otomatis, hampir **setiap kali** aplikasi dibuka petugas harus
mengetik ulang kata sandinya. Dalam praktiknya itu berarti aplikasinya tidak dipakai.

Versi pertama aplikasi ini membaca `refreshToken` dari server lalu membuangnya. Cacat itu
diperbaiki di sini.

### 2.2 Refresh token datang lewat header, bukan badan respons

`POST /auth/login` **tidak** mengembalikan refresh token pada badan JSON-nya. Server
menaruhnya pada cookie `httpOnly`:

```text
Set-Cookie: predpol_refresh=<jwt>; Path=/api/v1/auth; HttpOnly; Max-Age=604800
```

Bentuk itu benar untuk peramban — cookie `httpOnly` tidak terbaca JavaScript, sehingga
XSS tidak dapat mencurinya. Ponsel tidak punya peramban di jalur ini, jadi aplikasi:

1. membaca cookie tersebut dari header `Set-Cookie` saat masuk (`Api.refreshTokenFrom`);
2. menyimpannya di `EncryptedSharedPreferences` (`TokenStore.refreshToken`);
3. mengirimkannya kembali sebagai header `Cookie` saat memperbarui
   (`Api.refresh` → `Cookie: predpol_refresh=<jwt>`).

**Kontrak API tidak diubah.** Yang berubah hanya siapa yang menyimpan cookie-nya. Alternatif
yang ditolak adalah menambahkan `refresh_token` ke badan respons `/auth/login`: itu perubahan
kontrak yang material, dan ia akan menurunkan keamanan konsumen web dengan menaruh kredensial
tujuh hari di tempat yang terbaca JavaScript.

### 2.3 Aturan percobaan ulang

`Session.run` menjalankan permintaan, dan **hanya** bila ditolak `401`:

```text
401 -> ada refresh token?  tidak -> teruskan galatnya, pengguna masuk kembali
                            ya   -> POST /auth/refresh
                                    gagal -> teruskan galatnya
                                    berhasil -> simpan access token baru, ulangi SEKALI
```

Tiga batas yang disengaja:

- **Satu kali percobaan ulang.** Token yang baru diterbitkan tetapi tetap ditolak berarti
  persoalannya bukan kedaluwarsa. Mengulanginya menghasilkan gelung tak berujung.
- **Hanya `401`.** `503` dan kegagalan soket tidak menjatuhkan sesi; sinyal buruk di lapangan
  bukan alasan meminta kata sandi.
- **Refresh token tidak diputar.** Respons `/auth/refresh` tidak membawa `Set-Cookie`, jadi
  token yang sama dipakai sampai umur tujuh harinya habis.

### 2.4 Apa yang disimpan di ponsel

Keduanya di `EncryptedSharedPreferences`, dan **kata sandi tidak pernah disimpan**. Refresh
token jelas lebih berharga karena umurnya panjang; pertukarannya disadari — satu kredensial
tujuh hari di penyimpanan terenkripsi, ditukar dengan kata sandi yang tidak perlu diketik
berulang kali di tempat terbuka. `Keluar` menghapus keduanya sekaligus.

---

## 3. Kepercayaan sertifikat

`res/xml/network_security_config.xml` menambahkan **satu** jangkar kepercayaan untuk **satu**
domain. Itu bukan mematikan pemeriksaan sertifikat — justru lebih ketat daripada bawaan
Android, yang menerima ratusan CA publik. `cleartextTrafficPermitted="false"` tetap berlaku.

CA publik tetap dipercaya untuk domain yang sama, supaya aplikasi terus bekerja pada hari
sertifikat Let's Encrypt dipasang tanpa menunggu APK baru.

---

## 4. Test

26 unit test JVM, dijalankan dengan `gradle :petugas:testDebugUnitTest :app:testDebugUnitTest`.

| Berkas | Jumlah | Apa yang dijaga |
|---|---|---|
| `petugas/…/SessionTest.kt` | 8 | Aturan pembaruan sesi pada §2.3 |
| `petugas/…/ApiTest.kt` | 11 | `Set-Cookie` terbaca, `Cookie` terkirim, `401` dibedakan |
| `app/…/PublicApiTest.kt` | 7 | Tidak ada field identitas terkirim, galat terbaca warga |

Test berbicara ke **server HTTP sungguhan** (`FakeServer`, dibangun di atas `ServerSocket`)
dan bukan ke tiruan `Api`. Alasannya: yang paling mungkin salah justru ada di lapisan HTTP —
header yang tidak terbaca, header yang tidak terkirim, status yang tidak dibedakan. Memalsukan
lapisan itu berarti menguji tiruannya.

`com.sun.net.httpserver` tidak dipakai karena unit test Android dikompilasi terhadap
`android.jar`, dan kelas `com.sun.*` tidak ada di sana.

### 4.1 Mutation test pada penjaga sesi

Empat perusakan sengaja dijalankan pada 7 September 2026; keempatnya **ditangkap**:

| Perusakan | Hasil |
|---|---|
| Percobaan ulang setelah refresh dihapus | test gagal |
| `Set-Cookie` diabaikan | test gagal |
| `unauthorized = code == 401` → `false` | test gagal |
| Header `Cookie` tidak dikirim saat refresh | test gagal |

---

## 5. Verifikasi di emulator

Dijalankan pada 7 September 2026 dengan AVD `system-images;android-34;default;x86_64`,
tanpa jendela, `-gpu off`. Domain `siintel.awansurya.com` dipetakan ke `10.0.2.2` melalui
`/etc/hosts` tamu, sehingga jalur **HTTPS dan penyematan CA yang sesungguhnya ikut teruji**.

| Yang diuji | Hasil |
|---|---|
| LAPOR PRESISI memuat pilihan dari server | 6 kategori, 10 kecamatan |
| Mengirim laporan | tiket `RPT-0154`, tersimpan `RECEIVED` di basis data |
| `location_text` kosong tidak dikirim | terbukti — kolomnya kosong di basis data |
| PRESISI Petugas masuk sebagai Pimpinan | berhasil lewat HTTPS + CA satuan |
| Antrean menurut peran | 20 rekomendasi menunggu keputusan |

### 5.1 Cacat yang hanya terlihat di perangkat

Layar menampilkan nama petugas sebagai **`null`**.

Sebabnya: `full_name` bernilai NULL di basis data, dan `JSONObject.optString` **milik
Android** mengembalikan teks `"null"` untuk field bernilai `null` JSON — sementara
implementasi `org.json` di JVM mengembalikan teks kosong untuk masukan yang sama. Unit test
karenanya lulus sementara aplikasinya salah.

Diperbaiki dengan pembantu `text()` yang memeriksa `JSONObject.NULL` secara eksplisit, di
kedua aplikasi. Cacat ini adalah alasan langkah emulator tidak boleh dilewati: ada kelas
kesalahan yang **tidak dapat** ditangkap unit test JVM.

---

## 6. Yang belum dikerjakan

- Aplikasi petugas hanya **membaca** antrean; ia belum dapat menyetujui, menolak, atau
  mentriase. Itu memerlukan keputusan pemilik proyek tentang tindakan mana yang pantas
  dilakukan dari ponsel.
- Belum ada notifikasi dorong; antrean hanya diperbarui saat aplikasi dibuka atau
  "Muat ulang" ditekan.
- Belum ada test instrumentasi (`androidTest`) yang berjalan di perangkat.
