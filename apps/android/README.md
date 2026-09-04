# LAPOR PRESISI — aplikasi Android untuk masyarakat

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

## Membangun

Perkakas tidak ikut di repository. Yang dibutuhkan: JDK 17, Android SDK (platform 34,
build-tools 34.0.0), dan Gradle 8.7.

```bash
export JAVA_HOME=/path/ke/jdk-17
echo "sdk.dir=/path/ke/android-sdk" > local.properties

gradle assembleRelease
# keluaran: app/build/outputs/apk/release/app-release.apk
```

Alamat API dapat diganti tanpa menyunting kode:

```bash
gradle assembleRelease -PapiBase=https://siintel.awansurya.com:8998
```

## Tanda tangan

`assembleRelease` saat ini memakai **kunci debug** supaya APK-nya langsung dapat dipasang
untuk pengujian dan paparan. Untuk penyebaran nyata, ganti dengan kunci rilis milik satuan —
dan **jangan menaruh keystore itu di repository** (CLAUDE.md §28).

## Sertifikat HTTPS

Server demo masih memakai sertifikat swatandatangan. Android menolak sambungan HTTPS yang
sertifikatnya tidak tepercaya, sehingga aplikasi ini **belum dapat mengirim laporan ke
server demo** sampai sertifikat sungguhan terpasang — lihat `docs/10` §3.2b. Ini penolakan
yang benar dan tidak dilonggarkan di sini: mematikan pemeriksaan sertifikat pada aplikasi
yang dipasang warga membuka jalan penyadapan pada jaringan publik.
