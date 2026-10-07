# Aplikasi Android PREDIKSI PRESISI

Dua aplikasi, satu proyek Gradle:

| Modul | Aplikasi | Untuk | applicationId |
|---|---|---|---|
| `app` | **LAPOR PRESISI** | Masyarakat — kirim laporan tanpa akun | `id.polri.jaksel.laporpresisi` |
| `petugas` | **PRESISI Petugas** | Personel — masuk, lalu antrean pekerjaannya | `id.polri.jaksel.presisi` |

`applicationId` sengaja berbeda supaya keduanya dapat terpasang berdampingan di satu
ponsel — berguna saat paparan.

---

## LAPOR PRESISI — untuk masyarakat

Kanal laporan warga (PHASE 17, TASK 170). Berbicara ke API yang sama dengan aplikasi web,
lewat dua endpoint publik yang **tidak menuntut autentikasi**:

```text
GET  /api/v1/public/report-options   pilihan kategori dan kecamatan
POST /api/v1/public/citizen-reports  mengirim laporan
```

## Mengapa aplikasi warga, bukan aplikasi petugas

`docs/08` PHASE 17 menyebut LAPOR PRESISI sebagai aplikasi **masyarakat**, dan kanal
publiknya sudah ada dan teruji. Aplikasi untuk petugas adalah aplikasi kedua yang berbeda
— ia menuntut login, penyimpanan token, dan penegakan cakupan wilayah di sisi ponsel.

## Yang sengaja tidak ada

| Tidak ada | Alasannya |
|---|---|
| Pendaftaran dan akun | Kanal ini tanpa identitas (`docs/14` §3) |
| Izin lokasi | Lokasi sebatas kecamatan yang dipilih sendiri. Meminta izin GPS berarti meminta kepercayaan untuk sesuatu yang tidak dipakai |
| Kamera dan lampiran | Menyimpan berkas warga menyentuh retensi dan klasifikasi data — keputusan kebijakan yang belum diambil (U-14) |
| Riwayat laporan di ponsel | Menampilkannya menuntut penyimpanan penanda; nomor tiket sudah cukup, dan ia tidak mengikat ke siapa pun |
| Pustaka HTTP pihak ketiga | Aplikasi ini dipasang warga; tiap pustaka tambahan adalah kode yang ikut terpasang tanpa mereka ketahui |

Manifest hanya meminta `INTERNET`. Itu dapat diperiksa sendiri:

```bash
aapt2 dump badging app-release.apk | grep uses-permission
```

---

## PRESISI Petugas — untuk personel

Masuk dengan akun yang sama seperti aplikasi web, lalu menampilkan **antrean pekerjaan
menurut kewenangan peran** — isi yang sama dengan lonceng di pojok kanan atas layar web.

```text
POST /api/v1/auth/login     menukar kredensial dengan token
GET  /api/v1/auth/me        identitas dan kewenangan efektif
GET  /api/v1/notifications  antrean pekerjaan menurut kewenangan itu
```

### Mengapa hanya antrean, bukan seluruh layar web

Yang dibawa ke ponsel adalah satu-satunya hal yang benar-benar berguna di luar meja kerja:
**apa yang menunggu saya kerjakan sekarang.** Peta, analitik, dan penilaian risiko menuntut
layar lebar dan waktu membaca; memaksakannya ke ponsel menghasilkan tiruan yang lebih buruk
daripada aslinya.

### Sesi

Token disimpan **terenkripsi** (`EncryptedSharedPreferences`), bukan preferensi biasa: pada
ponsel yang di-root, preferensi biasa terbaca aplikasi lain, dan token yang bocor memberi
akses penuh atas nama petugas yang bersangkutan.

**Kata sandi tidak pernah disimpan.** Petugas yang kehilangan ponselnya kehilangan sesi,
bukan kata sandinya. Token yang ditolak server (`401`) menjatuhkan sesi dan mengembalikan
pengguna ke layar masuk beserta alasannya; kegagalan jaringan **tidak** — memaksa masuk
ulang setiap kali sinyal buruk membuat aplikasi tidak dapat dipakai di lapangan.

Aplikasi ini pun **hanya meminta `INTERNET`**. Tidak ada izin lokasi meski ia aplikasi
kepolisian: posisi satuan belum disimpan sistem mana pun, dan izin yang tidak dipakai hanya
memperbesar apa yang harus dipercaya saat memasangnya.

---

## Sertifikat: mengapa CA disematkan

Server demo memakai sertifikat yang ditandatangani **CA milik satuan**, bukan CA publik.
Android menolak sambungan HTTPS semacam itu — dan penolakannya benar.

`res/xml/network_security_config.xml` menambahkan **satu** jangkar kepercayaan untuk **satu**
domain. Bedanya dengan mematikan pemeriksaan sertifikat menentukan:

```text
mematikan pemeriksaan  ->  menerima sertifikat APA PUN, termasuk milik penyadap
menyematkan jangkar    ->  menerima HANYA sertifikat dari CA yang tertulis di sana
```

Yang kedua justru **lebih ketat** daripada kepercayaan bawaan Android, yang menerima ratusan
CA publik di seluruh dunia. Aplikasi ini menerima satu — ditambah CA sistem, supaya ia terus
bekerja pada hari sertifikat Let's Encrypt dipasang tanpa menunggu APK baru.

HTTP polos tetap ditolak (`cleartextTrafficPermitted="false"`). Sertifikat swatandatangan
mengamankan sambungannya; ia tidak membuat HTTP polos aman.

> **Kapan penyematan dihapus.** Begitu sertifikat Let's Encrypt terbit (`docs/10` §3.2),
> hapus `res/xml/network_security_config.xml` dan `res/raw/siintel_ca.pem` pada kedua modul
> beserta rujukannya di manifest. Menyematkan CA sendiri adalah jalan pintas yang dibayar
> dengan satu kewajiban: APK harus dibangun ulang bila CA-nya berganti.

CA-nya dibuat oleh `scripts/pasang-sertifikat-sendiri.sh`. **`ca.key` jangan pernah
dibagikan** — dengan berkas itu siapa pun dapat menyamar sebagai server ini di hadapan kedua
aplikasi.

---

## Tampilan: Jetpack Compose

Sejak 7 Oktober 2026 (2.2.0) seluruh layar digambar Compose. Tiap layar punya pasangan
`XxxScreen` (tampilan murni, dengan `@Preview` yang dapat dilihat di Android Studio tanpa
perangkat) dan `XxxActivity` (pemegang keadaan dan segala yang menyentuh Android). Komponen
dan palet ada di `ui/`. Mengubah rupa aplikasi biasanya cukup di `ui/Components.kt` dan
`ui/Theme.kt`.

## Membangun

Perkakas tidak ikut di repository. Yang dibutuhkan: JDK 17, Android SDK (platform 34,
build-tools 34.0.0), dan Gradle 8.7.

```bash
export JAVA_HOME=/path/ke/jdk-17
echo "sdk.dir=/path/ke/android-sdk" > local.properties

./gradlew assembleRelease
# keluaran: app/build/outputs/apk/release/app-release.apk
```

Gradle **wrapper** (`gradlew`, `gradlew.bat`, 8.14.3) ikut di repository sejak 6 Oktober
2026, supaya proyek dapat dibuka langsung di Android Studio pada mesin lain (termasuk
Windows) tanpa memasang Gradle sendiri. Studio menulis `local.properties`-nya sendiri
(berkas itu tidak di-commit).

**JDK dikunci di repo**, bukan di pengaturan Studio tiap mesin: `gradle/gradle-daemon-jvm.properties`
meminta Java 17, dan plugin foojay di `settings.gradle.kts` mengunduhnya bila mesin tidak
memilikinya (7 Oktober 2026). Latar belakangnya: Android Studio 2026.2 membawa Java 25, dan
Gradle 8.x tidak berjalan di atasnya; tanpa kunci ini tiap mesin baru gagal sync dengan
"Incompatible Gradle JVM version". Bila Studio menawarkan "migrate to Daemon toolchain",
jawab tidak — sudah dilakukan.

### Mengedit di Android Studio pada komputer lain

Jembatannya **Git**, bukan berbagi berkas lewat jaringan — Gradle di atas SSHFS/Samba
lambat dan rapuh.

```text
Windows (Android Studio)             Server (Claude Code lewat SSH)
git clone … siintel                  /home/kim/siintel
Open → folder apps/android           edit logika/API/test, bangun APK
ubah tampilan, uji di ponsel         git pull ← git push
git commit + git push                lanjut dari commit terbaru
```

Commit kecil dan sering; sebelum meminta Claude melanjutkan, pastikan perubahan sudah
di-push. `PublicApi.kt`, `petugas/Api.kt`, dan logika pengiriman mengikuti kontrak backend —
perubahan di sana sebaiknya dikoordinasikan lewat server.

Alamat API bawaannya `https://siintel.awansurya.com`, dan dapat diganti tanpa menyunting
kode:

```bash
gradle assembleRelease -PapiBase=https://alamat-lain
```

> Bawaannya pernah menyebut port `8998`, dan itu membuat APK hasil bangun **tidak dapat
> tersambung sama sekali**: port itu bergantung pada penerusan port di router yang sudah
> tidak aktif. Alamat bawaan yang mati adalah kegagalan paling mahal pada sebuah APK — ia
> baru ketahuan setelah terpasang di ponsel orang. Diperbaiki 9 September 2026.

## Tanda tangan

`assembleRelease` saat ini memakai **kunci debug** supaya APK-nya langsung dapat dipasang
untuk pengujian dan paparan. Diperiksa 9 September 2026 dan memang demikian:

```text
Signer #1 certificate DN: C=US, O=Android, CN=Android Debug
```

**Ini menutup jalan penyebaran nyata, dan alasannya bukan formalitas.** Kunci debug adalah
kunci yang SAMA pada setiap mesin pengembang di dunia, dengan kata sandi yang diketahui
umum (`android`). Siapa pun dapat membangun "pembaruan" yang diterima Android sebagai
aplikasi yang sama, dan Google Play menolak APK bertanda tangan debug.

Untuk paparan pada perangkat yang dikendalikan sendiri, ini memadai. Untuk dibagikan kepada
personel atau masyarakat, ganti dengan kunci rilis milik satuan — dan **jangan menaruh
keystore itu di repository** (CLAUDE.md §28).

## Alamat API

Backend dibuka ke publik lewat **awalan path**, bukan subdomain:

```text
https://siintel.awansurya.com/api/v1/...
```

Subdomain (`api.<domain>`) lebih rapi tetapi menuntut satu A record baru di panel DomaiNesia
— panel yang sedang terbukti tidak dapat diandalkan. Awalan path tidak menuntut DNS sama
sekali, dan `/api/v1/*` bebas dari bentrokan: rute BFF aplikasi web hanya `/api/auth/login`
dan `/api/auth/logout`, tanpa `/v1`.
