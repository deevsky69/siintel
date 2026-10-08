# 170 — Aplikasi Android

> **Status:** TECHNICAL DECISION
> **Fase:** PHASE 17 (TASK 170–172)
> **Terakhir diperbarui:** 8 September 2026

---

## 1. Satu aplikasi, dua pintu

**PRESISI** — satu modul Gradle, `applicationId = id.polri.jaksel.laporpresisi`, versi 2.0.0.
Layar mukanya menawarkan dua pintu:

| Pintu | Layar | Autentikasi |
|---|---|---|
| Lapor kejadian | `LaporActivity` | Tidak ada |
| Masuk sebagai petugas | `petugas/PetugasActivity` | Ada |

### 1.1 Sebelumnya dua APK, dan mengapa disatukan

Sampai 8 September 2026 ada dua aplikasi terpisah — `LAPOR PRESISI` untuk warga dan
`PRESISI Petugas` untuk personel. Pemisahannya punya alasan: warga tidak perlu memasang
kode berkewenangan di ponselnya.

Pemilik proyek meminta keduanya disatukan, dan permintaannya masuk akal untuk paparan: satu
tautan pemasangan, satu ikon, satu hal yang harus dijelaskan.

**Yang tidak hilang: kewenangan.** Layar petugas tetap menuntut masuk, dan setiap
permintaannya diperiksa server. Kode yang terpasang di ponsel tidak pernah menjadi
kewenangan — yang menentukan adalah token, dan token hanya lahir dari kredensial.

**Yang hilang:** jaminan bahwa ponsel warga tidak memuat layar masuk sama sekali. Sekarang
ia memuatnya, dan yang menjaganya hanyalah bahwa layar itu tidak berguna tanpa akun.

**Yang ikut hilang:** pemasangan berdampingan. `applicationId` yang dipertahankan adalah
milik aplikasi warga, karena merekalah yang paling banyak sudah memasangnya. Pemasangan
lama `id.polri.jaksel.presisi` tidak akan diperbarui sendiri dan perlu dicopot.

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

33 unit test JVM, dijalankan dengan `gradle :app:testDebugUnitTest`.

| Berkas | Jumlah | Apa yang dijaga |
|---|---|---|
| `…/petugas/SessionTest.kt` | 8 | Aturan pembaruan sesi pada §2.3 |
| `…/petugas/ApiTest.kt` | 13 | `Set-Cookie` terbaca, `Cookie` terkirim, `401` dibedakan, verifikasi |
| `…/PublicApiTest.kt` | 12 | Tidak ada field identitas terkirim, lokasi hanya bila dibagikan, berkas benar-benar terkirim |

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
| Antrean Pimpinan | 20 rekomendasi menunggu keputusan |
| Antrean Polsek | 4 peringatan dini + 3 laporan warga — antrean yang berbeda, ditentukan server |
| Keluar lalu masuk sebagai peran lain | berhasil; kedua token terhapus |
| **Pembaruan sesi setelah token benar-benar mati** | **berhasil, pengguna tidak melihat apa pun** |

### 5.1 Pembaruan sesi diuji dengan kedaluwarsa yang sungguhan

Bukan dengan memperpendek umur token, melainkan dengan menunggu token yang terbit pukul
07:39:22 melewati 15 menitnya, lalu menekan "Muat ulang" pada 07:55:40. Log API mencatat:

```text
07:55:43,561  GET  /api/v1/auth/me        401
07:55:43,572  POST /api/v1/auth/refresh   200
07:55:43,584  GET  /api/v1/auth/me        200
07:55:43,595  GET  /api/v1/notifications  200
```

Seluruhnya 34 milidetik. Layar tetap menampilkan antrean; tidak ada layar masuk, tidak ada
pesan galat, tidak ada yang perlu dikerjakan petugas.

### 5.2 Menjalankan emulatornya

```sh
export ANDROID_HOME=$HOME/android-tools/sdk
# Mesin ini tidak punya libx11-xcb1 sistem; emulator menjatuhkan diri (SIGSEGV) tanpa itu.
# Salinannya ada di dalam SDK sendiri.
export LD_LIBRARY_PATH=$ANDROID_HOME/emulator/lib64/qt/lib:$ANDROID_HOME/emulator/lib64
$ANDROID_HOME/emulator/emulator -avd presisi34 -no-window -no-audio -no-boot-anim \
    -no-snapshot -writable-system -gpu off -port 5560

adb root && adb remount && adb reboot          # `remount` baru berlaku setelah boot ulang
adb root && adb remount
adb shell 'echo "10.0.2.2 siintel.awansurya.com" >> /etc/hosts'
adb shell wm size 1080x2340 && adb shell wm density 420
```

Pemetaan `/etc/hosts` itu yang membuat jalur HTTPS dan penyematan CA **ikut teruji**;
tanpa itu pengujian hanya akan menyentuh HTTP polos yang justru dilarang aplikasi ini.

### 5.3 Cacat yang hanya terlihat di perangkat

Layar menampilkan nama petugas sebagai **`null`**.

Sebabnya: `full_name` bernilai NULL di basis data, dan `JSONObject.optString` **milik
Android** mengembalikan teks `"null"` untuk field bernilai `null` JSON — sementara
implementasi `org.json` di JVM mengembalikan teks kosong untuk masukan yang sama. Unit test
karenanya lulus sementara aplikasinya salah.

Diperbaiki dengan pembantu `text()` yang memeriksa `JSONObject.NULL` secara eksplisit, di
kedua aplikasi. Cacat ini adalah alasan langkah emulator tidak boleh dilewati: ada kelas
kesalahan yang **tidak dapat** ditangkap unit test JVM.

---

## 6. Lokasi, lampiran, dan verifikasi (8 September 2026)

### 6.1 Warga: berbagi lokasi dan melampirkan berkas

Izin lokasi diminta **saat tombolnya ditekan**, bukan saat layar dibuka. Dialog izin yang
muncul sebelum pelapor tahu untuk apa lokasinya dipakai hanya memberinya dua pilihan buruk.

Memakai `LocationManager` bawaan, bukan `play-services-location`: pustaka itu menuntut Google
Play Services yang tidak ada pada sebagian perangkat maupun emulator baku, dan aplikasi yang
dipasang warga sebaiknya membawa sesedikit mungkin yang tidak dapat mereka periksa.

**Titik terakhir yang diketahui tidak dipakai.** Ia bisa berumur berjam-jam dan menunjuk
tempat yang sudah lama ditinggalkan — titik yang salah lebih buruk daripada tidak ada titik,
karena ia tetap dicatat sebagai "lokasi kejadian".

Pemilih berkas memakai `OpenMultipleDocuments`, sehingga aplikasi **tidak pernah** meminta
izin membaca penyimpanan: yang diberikan pengguna adalah berkas yang ia pilih sendiri, bukan
hak membaca seluruh isi ponselnya. Badan `multipart/form-data` disusun sendiri di atas
`HttpURLConnection` dan dialirkan potong demi potong — video puluhan megabita yang dibaca
seluruhnya ke memori akan menjatuhkan aplikasi pada ponsel lama.

### 6.2 Petugas: memverifikasi dari ponsel

`POST /citizen-reports/{kode}/status` dengan `{"status": "VERIFIED"}` — **satu-satunya**
tindakan yang dapat dilakukan dari ponsel, dan pembatasannya disengaja. Verifikasi adalah
pernyataan bahwa laporan layak ditindaklanjuti, dan itu dapat diputuskan petugas yang baru
saja melihat tempatnya. Meneruskan, menugaskan, dan menutup laporan menuntut konteks yang
hanya ada di meja kerja; menyediakannya di layar sempit mengundang keputusan yang diambil
terlalu cepat.

### 6.3 Cacat yang hanya terlihat di perangkat

Tombol verifikasi tergambar sebagai **blok sian kosong** yang tetap dapat ditekan. Sebabnya
`MaterialButton` mewarnai dirinya lewat `backgroundTint` dari tema, dan tint itu menimpa
`android:background` yang ditulis di XML — teks beraksen di atas latar aksen menjadi tak
terlihat. Diperbaiki dengan gaya `OutlineButton` yang melepas tint (`backgroundTint = @null`).

Ini cacat kedua dalam dua sesi yang hanya muncul di perangkat, setelah `optString` pada §5.3.
Keduanya lolos kompilasi, lolos unit test, dan lolos build rilis.

---

## 7. Kelurahan pada laporan warga (5 Oktober 2026, versi 2.1.0)

Mengikuti web: setelah memilih kecamatan, pelapor dapat memilih **kelurahan** (pilihan,
bukan isian bebas; baris pertama "Tidak tahu / lewati"). Bila pelapor membagikan lokasi,
kecamatan dan kelurahan **terdekat** terisi otomatis dari titik pusat kelurahan pada
`report-options.areas` (`AreaNearest`, haversine, murni JVM dan teruji), dan catatannya
menyebut jarak serta bahwa itu usulan. Pengiriman menyertakan `kelurahan` hanya bila diisi;
server tetap menurunkan kelurahan terdekat sendiri dengan PostGIS bila kosong. Pada server
lama tanpa `areas`, pemilih kelurahan disembunyikan dan aplikasi bekerja seperti 2.0.0.

Unit test: 42 (empat suite), semuanya lulus. APK rilis: `~/siintel-rilis/presisi-2.1.0.apk`
(masih kunci debug; lihat §5). Belum diperiksa di perangkat nyata.

## 8. Jetpack Compose (7 Oktober 2026, versi 2.2.0)

Keputusan pemilik proyek (opsi B): seluruh tampilan dipindahkan dari XML/ViewBinding ke
Jetpack Compose supaya mudah dipoles di Android Studio. Polanya sama di tiga layar:

| Layar | Tampilan murni (+ `@Preview`) | Pemegang keadaan |
|---|---|---|
| Muka | `HomeScreen` / `HomeState` | `MainActivity` |
| Lapor | `LaporScreen` / `LaporState` / `LaporActions` | `LaporActivity` (izin, lokasi, berkas, tiket) |
| Petugas | `PetugasScreen` / `PetugasState` / `PetugasActions` | `PetugasActivity` (token, sesi) |

- `ui/Theme.kt`: palet yang sama dengan web, selalu gelap. `ui/Components.kt`: Panel,
  CriticalPanel, PrimaryButton, SecondaryButton, SectionLabel, Hint, InputField, Picker
  (pengganti Spinner), ErrorBox, ScreenHeader — satu tempat untuk mengubah rupa.
- Activity memegang `mutableStateOf(State)`; tidak ada ViewModel karena tidak ada keadaan
  yang perlu selamat dari rotasi selain yang dimuat ulang.
- Logika jaringan (`PublicApi`, `petugas/Api`, `Session`, `TokenStore`, `TiketStore`,
  `AreaNearest`) **tidak disentuh**; unit testnya tetap 42 dan lulus.
- Dibuang: enam layout XML, dua drawable, gaya `FieldLabel`/`OutlineButton`, pustaka
  AppCompat/Material/ConstraintLayout. Tema jendela kini turunan `android:Theme.Material`.
  APK rilis 6,7 MB (2.1.0: 5,6 MB; dengan Compose + pustaka lama sempat 9,7 MB).
- Kotlin 1.9.23 ↔ Compose Compiler 1.5.11, BOM 2024.06.00. Naik ke Kotlin 2.x berarti
  mengganti `composeOptions` dengan plugin `org.jetbrains.kotlin.plugin.compose`.

Belum diperiksa di perangkat nyata; pratinjau Compose di Android Studio adalah langkah
pemeriksaan pertama, ponsel lewat USB langkah kedua.

## 9. Lambang, ikon, dan lokasi yang tangguh (7 Oktober 2026, versi 2.3.0)

Masukan pemilik proyek setelah mencoba 2.2.0 di ponsel: "desain terlalu kaku" dan tombol
bagikan lokasi "tidak muncul apa-apa".

- **Lambang** `res/drawable/ic_logo.xml` (perisai + sasaran, buatan sendiri, bukan lambang
  kedinasan) dipakai di layar muka (besar), kepala layar lapor/petugas (ringkas), dan ikon
  peluncur. Komponen `BrandHeader`/`BrandMark`.
- **Ikon** Material (paket inti yang sudah ikut material3, tanpa dependensi baru) pada
  tombol dan label bagian: lapor, masuk, cek status, 110, imbauan, lokasi, lampiran,
  kirim, tiket, profil, muat ulang, keluar, verifikasi. Sudut kartu 14 dp, tombol 12 dp.
- **Lokasi**: versi lama meminta ke satu penyedia (GPS dahulu) dan di dalam ruangan
  menunggu 20 detik tanpa tanda. Kini titik terakhir yang diketahui (< 2 menit) dipakai
  seketika; bila tidak ada, semua penyedia yang menyala (GPS, jaringan, fused di Android
  12+) diminta sekaligus; ada indikator berputar selama menunggu; layanan lokasi yang mati
  dan izin yang ditolak permanen dilaporkan apa adanya, yang terakhir dengan tombol
  "Buka pengaturan aplikasi".

Unit test 42 lulus, `assembleRelease` lulus. Belum diperiksa ulang di perangkat.

### 9.1 Layar petugas per peran dan kerangka responsif (7 Oktober 2026, masih 2.3.0)

Permintaan pemilik proyek: tampilan untuk Pimpinan, Polsek, Fungsi, dan Administrator
yang responsif dan sederhana. Satu layar tetap dipakai keempatnya — isi antreannya
ditentukan server menurut kewenangan — tetapi rupanya kini mengikuti peran:

- Kartu "siapa saya": ikon peran (Pimpinan bintang, Polsek lokasi, Fungsi perkakas,
  Administrator pengaturan), nama peran beraksen, satu kalimat tugas yang bunyinya dari
  docs/12, dan pil jumlah total yang menunggu.
- Baris **ringkasan** kepingan per jenis antrean (peringatan, laporan, keputusan,
  rencana, prediksi, operasi) dengan ikon; menggulir mendatar di layar sempit.
- Kartu antrean berikon jenis dan pil angka; antrean nol tidak diulang sebagai kartu;
  bila semuanya nol tampil "tidak ada yang menunggu" bertanda centang hijau.
- `ScreenScaffold` bersama ketiga layar: gulir, tepi, indikator sibuk, dan **lebar isi
  maksimum 560 dp** sehingga di tablet isi tetap di tengah dan terbaca.

## 10. Menu bawah dan rincian (7 Oktober 2026, versi 2.4.0)

Masukan pemilik proyek: "kenapa tidak ada menu" dan "tidak bisa melihat list detailnya".
Batas lama (satu layar antrean) dilepas atas permintaan itu; batas barunya: yang masuk ke
ponsel adalah **daftar dan tindakan lapangan**, bukan peta/analitik/evaluasi.

| Tab | Syarat tampil (permission dari `/auth/me`) | Sumber | Tindakan di rincian |
|---|---|---|---|
| Antrean | selalu | `/notifications` | baris WARNING/CITIZEN_REPORT/DECISION membuka rincian |
| Peringatan | `warning:read` | `/warnings?page_size=100` | Terima (`warning:acknowledge`), Selesaikan (`warning:resolve`) |
| Laporan | `citizen_report:read` | `/citizen-reports?page_size=100` | Verifikasi (`citizen_report:write`) |
| Rekomendasi | `recommendation:read` | `/recommendations?page_size=100` | Keputusan Pimpinan APPROVED/MODIFIED/REJECTED (`commander_decision:approve`) |
| Akun | selalu | profil | daftar kewenangan, keluar |

- Tab yang tampil hanya mengikuti permission; server tetap menolak tindakan yang tidak
  sah — tombol di ponsel bukan kewenangan.
- Tombol kembali sistem: tutup rincian → ke Antrean → keluar layar (`BackHandler`).
- Daftar dimuat sekali per sesi dan dimuat ulang setelah tiap tindakan atau tombol muat
  ulang; "seratus teratas" dinyatakan di layar bila kode tidak ditemukan.
- Tidak ada pustaka navigasi: keadaan `tab` + `detail` pada `PetugasState`.

Unit test 45 (3 baru: pengurai daftar, badan keputusan, jalur terima/selesaikan). Belum
diperiksa di perangkat.

## 11. Tab Rekomendasi memakai field baru (8 Oktober 2026, versi 2.5.0)

Mengikuti `GET /recommendations` yang kini membawa `threat_type`, `time_window`,
`risk_score`, `kecamatan`, `kelurahan`. Daftar: skor di kiri, satu baris apa · di mana ·
kapan, lalu fungsi · prioritas · potongan usulan; urutannya yang menunggu dahulu, prioritas
tinggi, skor terbesar. Rincian: empat kotak kunci (Apa, Di mana, Kapan, Risiko) sebelum
kalimat usulan; kode prediksi/peringatan/waktu dibuat menjadi satu baris kecil di bawah.
Server lama tanpa field itu: tajuk jatuh ke "Untuk {fungsi}", skor tidak digambar (null,
bukan 0) — diuji di `ApiTest`. Unit test 45, `assembleRelease` lulus.

## 12. Tombol darurat dan tampilan ringkas per peran (8 Oktober 2026, versi 2.6.0)

**Warga.** Tombol merah besar di layar muka, dua langkah (tekan → dialog konfirmasi
dengan keterangan opsional). Lokasi dicari secepat mungkin: titik terakhir yang diketahui
dipakai apa pun umurnya, bila tidak ada menunggu penyedia paling lama 8 detik, lalu
permintaan dikirim apa pun hasilnya — permintaan tidak pernah tertahan oleh lokasi atau
izin. Setelah terkirim: kode dan kelurahan yang dikirim, dan pengingat 110.

**Petugas.** Tab **Darurat** (`panic:read`) dengan Terima/Tutup (`panic:acknowledge`) dan
tombol membuka titik di aplikasi peta ponsel (`geo:` intent). Selama layar terbuka antrean
diperiksa tiap 30 detik; permintaan OPEN yang baru dibunyikan sebagai notifikasi sistem
(saluran "darurat", penting tinggi; izin `POST_NOTIFICATIONS` diminta di Android 13+).
**Batasnya dinyatakan:** ponsel yang aplikasinya tertutup tidak diberi tahu — itu menuntut
layanan dorong pihak ketiga (Firebase), yang sejak awal dihindari (tanpa Play Services) dan
menjadi keputusan tersendiri.

**Tampilan ringkas** (`PetugasState.compact`, semua peran selain Administrator): baris
kepingan ringkasan disembunyikan, kode prediksi/peringatan/waktu dibuat pada rincian
disembunyikan, daftar kewenangan di Akun disembunyikan; Pimpinan tidak mendapat tab
Peringatan (cukup Darurat dan Rekomendasi). Server tetap mengirim data yang sama — ini
penyaringan tampilan, bukan kewenangan.

Unit test 47, `assembleRelease` lulus. Belum diperiksa di perangkat.

## 13. Penyusunan ulang per peran setelah penelitian aplikasi sejenis (8 Oktober 2026, versi 2.7.0)

Masukan pemilik proyek: layar muka terlalu padat (tiga tombol bertumpuk), label menu bawah
terpenggal ("Rekomend/asi"), tampilan kaku "seperti buatan AI", dan permintaan agar isi per
peran diteliti dari aplikasi sejenis — bukan sekadar menaruh data.

### Yang diteliti dan apa yang diambil

| Rujukan | Yang diambil |
|---|---|
| Aplikasi komando: Motorola PSCore / PremierOne Mobile, Adashi LiveView | Komandan membuka dengan *gambaran situasi* (common operating picture) dan hal yang menunggu keputusannya; peringatan darurat (duress) selalu paling atas |
| Aplikasi petugas lapangan: Tyler ShieldForce, Spillman CAD Touch | Antrean "panggilan" berurut kemendesakan, berwarna menurut status, tindakan satu ketuk (terima/tindak), peta untuk menuju lokasi |
| Aplikasi darurat warga: 112 India (UX4G), SOS Grab, JAKI/JakLapor | Satu tombol darurat besar dan sederhana; laporan non-darurat terpisah; imbauan sekitar; sedikit pilihan |
| Polri Super App Presisi | Panggilan darurat dan laporan online berdampingan sebagai layanan warga |

### Hasilnya

- **Warga**: lambang kecil + satu kalimat; **TOMBOL DARURAT** besar; satu tombol **Lapor**;
  cek status sebagai baris teks; imbauan dilipat menjadi satu baris berjumlah; masuk
  petugas sebagai tautan kecil di bawah. Tidak ada lagi tiga tombol bertumpuk.
- **Petugas, beranda per peran** (`HomeBoard`): sapaan menurut jam; baris *Situasi* dari
  `/dashboard/summary` (Pimpinan & Administrator: indeks keamanan, kejadian 24 jam,
  peringatan aktif; Polsek: kejadian dan peringatan wilayahnya; Fungsi: tanpa angka);
  lalu **kartu tugas** berurut kemendesakan dari `/notifications` — darurat paling atas,
  angka besar, satu contoh isi, ketuk membuka daftar atau langsung rinciannya bila hanya satu.
- **Menu bawah**: label satu baris tanpa pemenggalan; "Rekomendasi" menjadi **Usulan**,
  dan bagi Pimpinan **Keputusan**; Pimpinan tanpa tab Peringatan.
- **Rupa**: sudut lebih membulat (18 dp), permukaan terisi dengan garis samar alih-alih
  kotak bergaris tegas, label huruf biasa (bukan kapital berjarak), angka besar sebagai
  pembawa makna.

Isi tiap peran tetap ditentukan server lewat permission; layar hanya menata. Unit test 47,
`assembleRelease` lulus. Belum diperiksa di perangkat.

## 14. Yang belum dikerjakan

- Belum ada notifikasi dorong; antrean hanya diperbarui saat aplikasi dibuka atau
  "Muat ulang" ditekan.
- Belum ada test instrumentasi (`androidTest`) yang berjalan di perangkat.
- Petugas belum dapat **melihat lampiran** laporan dari ponsel — hanya mengetahui bahwa
  laporan itu ada. Menampilkan foto warga di layar yang dibawa berkeliling adalah keputusan
  yang pantas diambil pemilik proyek, bukan diambil diam-diam karena secara teknis mudah.
