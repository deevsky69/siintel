# MODUL TATA CARA PENGGUNAAN — PREDIKSI PRESISI

Sistem Deteksi Dini Kerawanan Kamtibmas berbasis *Predictive Policing*
Polres Metro Jakarta Selatan

> **Versi halaman.** Modul ini juga disajikan di dalam aplikasi pada `/modul.html`
> (tautan **Modul** di bilah atas), dengan tata letak siap cetak. Berkasnya ada di
> `apps/web/public/modul.html`; dokumen inilah acuannya bila keduanya berbeda.
>
> **Status prototipe.** Seluruh angka pada aplikasi ini berasal dari **data sintetis**.
> Bobot dan ambang yang berlaku **ditetapkan pemilik proyek 9 September 2026**, sehingga
> keduanya berlaku sebagai ketentuan — tetapi ketetapan itu menyangkut ANGKANYA, bukan
> klaim bahwa hasilnya sudah terbukti tepat. Ketepatan hanya dapat dinyatakan lewat
> evaluasi. Modul ini menjelaskan cara kerja sistem, bukan menyatakan bahwa angkanya sudah
> dapat dipakai sebagai dasar tindakan nyata atas data sungguhan.

---

## 1. UNTUK SIAPA MODUL INI

| Pembaca | Bagian yang paling relevan |
|---|---|
| **Pimpinan** | §2 · §3 · §6 Brief · §14 Keputusan · §16 Evaluasi |
| **Administrator** | §3 · §7 Input · §11 Penilaian risiko · §12 Prediksi · §13 Peringatan · §15 Operasi · §19 Akun |
| **Petugas Fungsi** | §3 · §14 Rekomendasi · §15 Operasi |
| **Petugas Polsek** | §3 · §5 Dashboard · §8 Peta · §13 Peringatan · §17 Laporan masyarakat |
| **Analis / peninjau** | §9 Pattern DNA · §10 Analytics · §16 Evaluasi |
| **Penguji Taskap** | §2 Gagasan pokok · §3 Pemisahan kewenangan · §16 Evaluasi · §20 Audit · §21 Batasan |

---

## 2. GAGASAN POKOK: SISTEM INI TIDAK MEMUTUSKAN

Yang membedakan PREDIKSI PRESISI dari sekadar dasbor statistik adalah **rantai
tertutup** berikut, dan yang membedakannya dari sistem otomatis adalah mata rantai
keempat:

```
DATA  →  ANALISIS  →  PREDIKSI  →  PERINGATAN DINI  →  REKOMENDASI
                                                            ↓
                                            KEPUTUSAN PEJABAT BERWENANG
                                                            ↓
                                          TINDAKAN OPERASIONAL  →  HASIL NYATA
                                                            ↓
                                                       EVALUASI
                                                            ↓
                                              PERBAIKAN MODEL
```

**Sistem mengusulkan; manusia memutuskan.** Rekomendasi yang muncul di layar adalah
**opsi**, bukan perintah. Tidak ada satu pun tindakan operasional yang dapat lahir
tanpa melewati keputusan pejabat berwenang — dan itu bukan sekadar kesepakatan
prosedur, melainkan dijaga oleh basis data itu sendiri: sebuah *trigger* PostgreSQL
menolak setiap tindakan yang tidak berasal dari keputusan berstatus **DISETUJUI** atau
**DIMODIFIKASI**. Mematikan aplikasi tidak melonggarkan aturan itu.

---

## 3. EMPAT PERAN DAN FUNGSINYA

Pemisahan peran di sini bukan sekadar pengelompokan menu. Ia menjalankan **pemisahan
kewenangan**: tidak ada satu akun pun yang dapat mengusulkan, menyetujui, dan
melaksanakan sekaligus.

### 3.1 Ringkasan

| Peran | Tugas pokok dalam sistem | Cakupan data | Kewenangan khas yang tidak dimiliki peran lain |
|---|---|---|---|
| **Pimpinan** | Menilai dan memutuskan rekomendasi; memerintahkan evaluasi | Seluruh Polres | **Satu-satunya** yang menyetujui rekomendasi, dan **satu-satunya** yang menjalankan evaluasi |
| **Administrator** | Menyiapkan data, menjalankan analisis, mengendalikan kegiatan harian, dan mengelola akun | Seluruh Polres | Memasukkan data, menjalankan penilaian risiko dan prediksi, menerima dan menyelesaikan peringatan, mencatat pelaksanaan operasi, mengelola pengguna dan peran |
| **Fungsi** | Menindaklanjuti sesuai fungsi masing-masing | **Hanya fungsinya sendiri** | Menulis laporan intelijen dan kegiatan fungsinya |
| **Polsek** | Bertindak di wilayah hukumnya | **Hanya polseknya sendiri** | Menerima peringatan di wilayahnya; mencatat laporan masyarakat |

> **Empat peran, bukan enam.** Command Center dan Analyst dilebur ke Administrator pada
> 1 September 2026 atas keputusan pemilik proyek. Akun `demo.commandcenter` dan
> `demo.analyst` masih dapat masuk, tetapi keduanya kini berperan Administrator; untuk
> peragaan gunakan `demo.admin`.

### 3.2 Penjelasan tiap peran

#### Pimpinan

Peran ini menjawab pertanyaan terpenting bagi pertanggungjawaban sistem: **siapa yang
memutuskan.** Pimpinan melihat seluruh wilayah, seluruh prediksi, seluruh peringatan,
dan seluruh rekomendasi — lalu memutuskan mana yang dijalankan.

Tiga keputusan yang tersedia berdiri **sejajar**, bukan satu tombol setuju dengan tolak
tersembunyi di menu:

| Keputusan | Artinya |
|---|---|
| **Disetujui** | Rekomendasi dijalankan apa adanya |
| **Dimodifikasi** | Rekomendasi dijalankan setelah disesuaikan. Usulan asli sistem **tidak ditimpa** — keduanya tersimpan berdampingan |
| **Ditolak** | Rekomendasi tidak dijalankan |

Setiap keputusan tercatat beserta nama pejabat, waktu, dan pertimbangannya.
**Rekomendasi yang sudah diputus tidak dapat diputus ulang**, karena memutus dua kali
akan mengaburkan siapa yang memutuskan apa.

> Pimpinan **sengaja tidak** dapat menerima atau menyelesaikan peringatan harian, dan
> tidak memasukkan data. Itu pekerjaan Administrator. Sebaliknya, Administrator tidak
> dapat memutuskan maupun menjalankan evaluasi. Keduanya saling membatasi.

#### Administrator

Peran operasional terbesar. Ia memasukkan data kejadian dan laporan intelijen,
menjalankan penilaian risiko dan prediksi, memantau serta menutup peringatan, mencatat
pelaksanaan tindakan operasional, dan mengelola akun serta peran.

Peran ini memegang 40 dari 43 kewenangan. Dua yang **sengaja** berada di luar
jangkauannya, dan keduanya milik Pimpinan:

| Kewenangan | Mengapa dipisahkan |
|---|---|
| Menyetujui rekomendasi | Yang mengusulkan tidak boleh menjadi yang memutuskan. Inilah inti rantai human-in-the-loop |
| **Menjalankan evaluasi** | Yang menghasilkan angka tidak boleh menjadi yang menilai ketepatannya. Tanpa pemisahan ini, *precision* dan *recall* dinilai oleh pihak yang berkepentingan atas hasilnya |

Pemisahan kedua itu hanya berbiaya satu kewenangan, tetapi ia yang membuat angka validasi
sistem ini dapat dipertahankan ketika ditanya siapa yang memverifikasinya.

#### Fungsi (Samapta, Binmas, Intelkam, Reskrim, Lantas)

Peran ini dibatasi **menurut fungsi**, bukan wilayah. Seorang petugas Samapta melihat
rekomendasi, kegiatan, dan laporan yang ditujukan kepada Samapta — bukan milik Reskrim.

Peta, prediksi, dan peringatan tetap terlihat seluruh wilayah, karena kesadaran situasi
tidak dibatasi fungsi. Yang dibatasi adalah data pekerjaannya sendiri.

#### Polsek

Dibatasi **menurut wilayah hukum**. Seorang petugas Polsek Tebet melihat kejadian,
risiko, prediksi, dan rekomendasi di Tebet saja.

Pembatasan ini nyata dan dapat diperiksa: pada peta, delapan kecamatan lain tetap
tergambar tetapi bertanda **"tidak ada data"** — bukan disembunyikan. Sistem
menyatakan batas kewenangan secara terbuka alih-alih berpura-pura wilayah lain tidak
ada.

Polsek dapat **menerima** peringatan di wilayahnya, tetapi **tidak dapat
menyatakannya selesai** — penutupan peringatan tetap kewenangan Administrator.

### 3.3 Prinsip yang mendasari pembagian ini

| Prinsip | Wujudnya di sistem |
|---|---|
| Pemisahan kewenangan | Yang menyiapkan dan melaksanakan (Administrator, Fungsi, Polsek) ≠ yang **memutuskan** (Pimpinan) ≠ yang **menilai ketepatan** (Pimpinan) |
| Kebutuhan untuk tahu | Polsek dibatasi wilayah, Fungsi dibatasi fungsi |
| Ditegakkan di server | Menyembunyikan tombol **bukan** pengamanan. Setiap permintaan diperiksa ulang di sisi server; akun yang memaksa tetap ditolak, dan penolakannya tercatat di audit |
| Kebocoran tidak dibiarkan lewat pesan galat | Data di luar wilayah dijawab **"tidak ditemukan"**, bukan "terlarang" — sebab "terlarang" justru membocorkan bahwa datanya ada di wilayah lain |

---

## 4. MASUK KE APLIKASI

1. Buka alamat aplikasi pada peramban.
2. Masukkan **username** dan **password**.
3. Sistem akan membuka Dashboard sesuai peran Anda.

Yang perlu diketahui:

- **Seluruh percobaan masuk dicatat**, termasuk yang gagal.
- Password tidak pernah tersimpan di dalam kode maupun berkas contoh; hanya
  ditetapkan langsung di server.
- Sesi berumur pendek dan diperpanjang otomatis selama Anda aktif.
- Menu yang tampil mengikuti peran Anda, tetapi **yang menentukan adalah server** —
  membuka alamat halaman secara langsung tidak melewati pembatasan.
- Tombol **Keluar** di kanan atas mengakhiri sesi dan mengembalikan Anda ke halaman masuk.
- **Lonceng** di kanan atas memuat antrean pekerjaan yang menunggu Anda — lihat di bawah.
- Halaman masuk memuat jalan kembali ke **Lapor Kejadian** dan **Halaman Muka**, untuk warga
  yang salah menekan tombol.

### Lonceng — pekerjaan yang menunggu Anda

Lonceng di pojok kanan atas **bukan kabar tentang apa yang terjadi**, melainkan daftar
pekerjaan yang menunggu Anda kerjakan. Bedanya menentukan, dan itu pula sebabnya isinya
berbeda menurut peran:

| Peran | Yang muncul di loncengnya |
|---|---|
| **Pimpinan** | Rekomendasi yang menunggu keputusannya |
| **Polsek** | Peringatan belum diterima · laporan warga belum diverifikasi |
| **Administrator** | Peringatan · laporan warga · prediksi draf · keputusan yang belum ditindaklanjuti |
| **Fungsi** | Kosong, dan itu benar — kewenangannya mencatat kejadian dan patroli, bukan menyetujui atau menriase |

Tiap baris terikat pada **kewenangan tindakan**, bukan kewenangan baca. Seorang Pimpinan
dapat membaca laporan masyarakat tetapi tidak dapat memverifikasinya — jadi laporan yang
belum diverifikasi **tidak** muncul di loncengnya. Memberitahunya hanya menambah kecemasan
tanpa jalan keluar, dan lencana yang selalu merah berhenti dilihat orang.

> **Tidak ada penanda "sudah dibaca".** Angkanya dihitung ulang dari keadaan sebenarnya
> setiap kali halaman dimuat, sehingga ia **hanya turun ketika pekerjaannya selesai**. Itu
> disengaja: pada antrean tugas, penanda terbaca berubah menjadi cara melupakan tugas.

Antrean yang kosong tetap ditampilkan berikut angka nolnya. "Nol peringatan menunggu" adalah
kabar baik yang pantas terbaca — dan menghilangkan barisnya membuat Anda tidak dapat
membedakan "tidak ada" dari "tidak diperiksa".

### Susunan menu

Menu tersusun dalam **lima kelompok**, masing-masing membuka submenu. Hanya kelompok tempat
halaman yang sedang Anda buka yang terbuka sendiri; kelompok lain cukup satu klik.

| Kelompok | Submenu | Menjawab |
|---|---|---|
| **Pemantauan** | Beranda · Informasi Terbaru · Peta · Peringatan Dini | Apa yang sedang terjadi |
| **Laporan** | Laporan Masyarakat · Laporan Petugas · Panic Button · Input Data | Apa yang masuk |
| **Analisis** | Analitik · Wilayah Rawan · Pola Gangguan · Prediksi · Penilaian Risiko · Evaluasi | Apa artinya |
| **Operasi** | Operasi & Penugasan · Rekomendasi & Keputusan · Dokumen Intelijen · Brief Pimpinan | Apa yang dikerjakan |
| **Sistem** | Manajemen Pengguna · Audit Log · Pengaturan Sistem | Siapa melakukan apa |

Susunan ini ditetapkan pemilik proyek pada 2 September 2026, menggantikan deret enam belas
ikon setara yang sebelumnya memaksa mata membaca seluruhnya untuk menemukan satu.

**Menu yang tidak dapat Anda pakai sama sekali tidak ditampilkan**, dan kelompok yang tidak
menyisakan satu pun submenu ikut hilang. Seorang Pimpinan misalnya tidak memegang satu pun
izin tulis, sehingga **Input Data** dan **Manajemen Pengguna** tidak muncul — sebelumnya
keduanya tampil dan hanya menyambut dengan kalimat "Akun Anda tidak memiliki kewenangan".

**Rekomendasi & Keputusan** membawa lencana berisi jumlah yang menunggu keputusan Anda.
Lencana itu pindah ke judul kelompok **Operasi** saat submenunya tertutup, sehingga tetap
terlihat tanpa membuka apa pun — dan hanya muncul bagi yang berwenang memutuskan, karena
angka yang tidak dapat Anda selesaikan hanya menjadi kecemasan tanpa jalan keluar.

> **Menyembunyikan menu bukan pengamanan.** Server tetap memeriksa setiap permintaan.
> Menyalin alamat halaman yang tersembunyi dan membukanya langsung tetap ditolak, dan
> percobaannya tercatat di jejak audit.

### Empat layar yang baru

| Submenu | Isinya |
|---|---|
| **Informasi Terbaru** | Tiga kanal berdampingan — kejadian, laporan masyarakat, laporan intelijen. Sengaja **tidak dilebur** jadi satu aliran: keandalan ketiganya berbeda, dan aliran tunggal membuat perbedaan itu hilang |
| **Laporan Petugas** | Kejadian yang dicatat petugas, dengan **pencarian, rentang tanggal, dan penyaring**. Statusnya dapat diubah langsung dari daftar |
| **Wilayah Rawan** | Peringkat kecamatan; **tiap baris dapat diklik** untuk melihat ancaman, jam rawan, riwayat, peringatan aktif, dan kejadian terbarunya |
| **Pengaturan Sistem** | Bobot, ambang, dan kelas risiko yang sedang berlaku — **hanya membaca** |

**Pengaturan Sistem sengaja tidak dapat menyunting.** Setiap baris skor risiko menyimpan
versi bobot yang menghasilkannya, dan versi yang masih dirujuk baris mana pun tidak boleh
berubah isinya: menurunkannya akan membuat skor lama tampak terbit di bawah aturan yang
tidak pernah berlaku saat itu. Cara yang benar mengubah bobot adalah **menambah versi
baru**, lewat berkas konfigurasi lalu pembangunan ulang.

Pada layar **Wilayah Rawan**, dua kolom terakhir bukan pengukuran yang sama dengan kolom
skor: jumlah laporan tidak ditimbang sama sekali. Wilayah dengan banyak laporan tetapi skor
rendah biasanya bukan wilayah yang memburuk, melainkan wilayah yang **warganya rajin
melapor** — dan sebaliknya, wilayah sepi laporan bisa saja justru wilayah yang warganya
enggan melapor.

### Panic Button — baca ini sebelum mengandalkannya

> **Kanal darurat sekali-tekan belum tersambung.** Ia menuntut dua hal: aplikasi di tangan
> warga yang dapat mengirim lokasi seketika, dan — yang lebih menentukan — **komitmen
> respons**: siapa yang menerima, dalam berapa lama, dan apa yang terjadi bila tidak ada
> yang menjawab.
>
> Yang kedua bukan pekerjaan teknis. Tombol darurat yang menjanjikan bantuan tanpa ada yang
> berkewajiban datang **lebih berbahaya daripada tidak ada tombol sama sekali** — ia membuat
> orang berhenti mencari pertolongan lain.
>
> Layar **Panic Button** karena itu tidak berpura-pura menjadi kanal itu. Ia menampilkan hal
> terdekat yang benar-benar ada: laporan masyarakat berurgensi tinggi yang belum tertangani,
> dan menyatakan perbedaannya di bagian paling atas layar. Untuk keadaan darurat, jalur yang
> berlaku tetap **110**.

---

## 5. DASHBOARD — LAYAR PERTAMA

Beranda menjawab **apa yang menonjol hari ini**, bukan menyajikan seluruh yang diketahui
sistem. Susunannya:

```text
Sorotan     4 kartu — satu angka, satu baris
Peta        isi utama, rincian terbuka saat wilayah diklik
Menonjol    3 kartu — apa yang BERGERAK, bukan apa yang ada
Selebihnya  terlipat
```

Seluruh isinya dibatasi kewenangan Anda. Petugas Polsek melihat susunan yang sama berisi
wilayahnya sendiri.

### Empat kartu sorotan

| Kartu | Angkanya | Bacanya |
|---|---|---|
| **Laporan Masuk** | Total 24 jam terakhir | Rinciannya tiga jenis: kejadian, intelijen, warga |
| **Status Wilayah** | Berapa dari berapa kecamatan pada status terbanyak | Pemetaan statusnya **belum disetujui** |
| **Perlu Perhatian** | Butir yang masih menunggu manusia | Terpisah: peringatan belum diterima, dan keputusan yang menunggu Anda |
| **Wilayah Prioritas** | Skor sel tertinggi wilayah teratas | Rata-rata wilayahnya disebut di bawahnya |

Tiap kartu hanya memuat **satu angka besar dan satu baris keterangan**. Rinciannya tidak
dihapus — ia pindah ke layar yang memang tugasnya menjelaskan, dan setiap kartu menautkan
ke sana.

### Peta — arahkan kursor, lalu klik

Peta adalah isi utama beranda. Keduanya memikul beban yang berbeda:

| | Isinya | Untuk |
|---|---|---|
| **Arahkan kursor** | Skor risiko, kelas, ancaman utama, jam rawan | Memutuskan **apakah perlu diklik** |
| **Klik** | Ancaman berperingkat, jam rawan, peringatan aktif, riwayat, jumlah sel | Rincian wilayah itu |

Pembagian ini mengikuti cara aplikasi pemantauan lain menyusunnya — Grafana, ArcGIS
Dashboards, Datadog: ringkasan hover **tidak pernah lebih dari lima baris**, dan tidak
pernah memuat sesuatu yang harus diklik. Tooltip mengikuti kursor dan hilang begitu kursor
bergeser ke arahnya; tautan di dalamnya mustahil diraih.

Klik **tidak meninggalkan beranda**. Rinciannya muncul di panel sebelah kanan, dan alamat
halaman ikut berubah menjadi `?wilayah=…` — sehingga tampilan itu dapat dibagikan sebagai
tautan saat paparan, dan tombol mundur peramban bekerja seperti yang diharapkan.

Dari panel itu tersedia dua jalan lanjut: **Rincian lengkap** (seluruh data wilayah) dan
**Buka di peta** (peta lengkap dengan ketiga layer).

> Sebelum ada wilayah yang diklik, panel kanan **sengaja dibiarkan kosong** beserta ajakan
> mengklik — bukan diisi wilayah pilihan sistem. Rincian yang muncul sendiri tanpa diminta
> membuat pembaca mengira ia sedang melihat wilayah yang paling penting, padahal ia hanya
> melihat wilayah yang kebetulan terpilih lebih dulu.

### Tiga kartu "menonjol"

Blok ini menyorot apa yang **berubah**, bukan apa yang terbesar:

| Kartu | Isinya |
|---|---|
| **Naik Paling Tajam** | Jenis gangguan dengan kenaikan terbesar dibanding pekan lalu |
| **Wilayah Terbanyak Lapor** | Volume laporan 30 hari — **bukan** peringkat kerawanan |
| **Tindakan Disarankan** | Satu usulan teratas, diturunkan aturan, bukan keluaran model |

Bedanya menentukan. Daftar "sepuluh teratas" selalu terisi dan karenanya tidak pernah
memberi tahu sesuatu yang baru; yang berguna dibaca setiap pagi adalah apa yang bergerak
sejak kemarin. Bila memang tidak ada yang bergerak, kartunya **mengaku kosong** alih-alih
mengisi dirinya dengan angka terbesar yang kebetulan ada.

### Rincian dan panel analitik — terlipat

Di bawah terdapat bagian **terlipat**; klik untuk membukanya. Isinya tabel sepuluh wilayah,
isu sepekan lengkap, seluruh rekomendasi kebijakan, indeks keamanan, outlook prediktif,
tren bulanan, status patroli, dan peringatan teratas.

Semuanya tetap ada dan masing-masing punya layarnya sendiri di menu. Yang berubah hanya:
ia tidak lagi ikut dibaca pada pandangan pertama.

Sejak 8 September 2026 tiap butir **Rekomendasi Kebijakan** dapat diklik dan membuka layar
yang memuat angka asalnya: butir jam patroli membuka rincian kecamatan yang skornya
dikutip, butir operasi khusus membuka Crime Analytics yang sudah tersaring ke jenis
gangguan itu, dan butir verifikasi membuka daftar laporan masyarakat berstatus `RECEIVED`.
Saran yang dasarnya tidak dapat diperiksa sama saja dengan saran tanpa dasar.

> **Kebiasaan yang benar:** setiap angka turunan pada aplikasi ini membawa keterangan asal.
> Bacalah keterangan itu sebelum mengutip angkanya. Angka tanpa konteks adalah cara
> tercepat sebuah prototipe disalahpahami sebagai data resmi.

---

## 6. EXECUTIVE BRIEF — RINGKASAN UNTUK PIMPINAN

Menu **Brief**. Satu halaman yang dapat dibaca lima menit sebelum apel, dan **siap cetak**
(Ctrl+P).

Isinya enam bagian: situasi 24 jam terakhir, ancaman menonjol beserta jam rawannya,
rekomendasi yang menunggu keputusan, keputusan yang belum ditindaklanjuti, dan ketepatan
model sejauh ini.

> **Kalimatnya disusun template, bukan model bahasa.** Halaman ini menyatakannya sendiri.
> Setiap angka di dalam kalimat diulang sebagai angka pada daftar di bawahnya, sehingga
> bila ada yang keliru, kekeliruannya terlihat — bukan tersembunyi di dalam prosa.

Tiap bagian mengikuti kewenangan Anda sendiri. Bagian yang tidak berhak Anda baca tampil
kosong beserta alasannya, bukan diisi angka. Ringkasan tidak boleh menjadi pintu belakang
bagi data yang pintu depannya terkunci.

---

## 7. MEMASUKKAN DATA

Menu **Data Entry**. Tiga formulir: **kejadian**, **laporan intelijen**, dan **triase
laporan masyarakat**.

### Kejadian

Isi jenis, tanggal, jam, lokasi, kategori TKP, modus, dan objek sasaran. Yang perlu
diketahui:

- **Jenis kejadian hanya boleh dari daftar resmi.** Nilai di luar itu ditolak beserta
  daftar yang sah — bukan disimpan apa adanya. Dua ejaan untuk satu hal akan memecah
  seluruh analisis pola.
- **Tanggal di masa depan ditolak**, diukur terhadap waktu acuan sistem.
- **Identitas korban, pelaku, dan saksi tidak diterima.** Bila dikirim, sistem
  mengabaikannya dan tidak pernah menyimpannya — termasuk tidak ke catatan audit.
- Petugas yang dibatasi wilayah hanya dapat menulis di wilayahnya. Lokasi di luar itu
  dijawab "tidak ditemukan", bukan "terlarang".

### Mengubah status — dua alur, satu aturan

Ada **dua alur status** pada sistem ini, dan keduanya dapat diubah dari dua tempat: langsung
di daftarnya, atau lewat formulir di menu **Input Data**.

| Alur | Tahapannya | Diubah dari |
|---|---|---|
| **Laporan Petugas** (kejadian) | Dilaporkan → Penyelidikan → Penyidikan → Selesai | Kolom **Ubah status** pada menu Laporan Petugas |
| **Laporan Masyarakat** | Diterima → Diverifikasi → Diteruskan → Ditangani → Selesai | Kolom **Ubah tahapan** pada menu Laporan Masyarakat, atau tab **Triase** di Input Data |

Caranya sama untuk keduanya: pilih tahapan baru dari daftar di baris yang bersangkutan, lalu
tekan **Simpan**. Status yang sedang berlaku tidak muncul di pilihan — memilihnya akan
ditolak, dan menawarkan pilihan yang pasti ditolak hanya memancing kekeliruan.

**Status boleh mundur dan boleh melompat.** Itu disengaja, dan berlaku untuk kedua alur:
belum ada SOP yang menetapkan urutannya wajib. Melarang mundur punya akibat nyata — laporan
yang keliru diverifikasi tidak dapat dikembalikan, dan perkara yang keliru ditutup tidak
akan pernah dapat dibuka kembali.

Yang **ditolak** hanya memindahkan ke status yang sedang berlaku. Itu bukan aturan alur
kerja melainkan penjagaan catatan: mencatat "perubahan" yang tidak mengubah apa pun membuat
jejak audit memuat peristiwa yang tidak terjadi.

> **Setiap perpindahan tercatat di jejak audit** lengkap dengan status sebelum dan
> sesudahnya. Karena perpindahannya sengaja dibiarkan longgar, jejak itulah yang menjadi
> penjaga: perpindahan yang tidak wajar tetap terlihat oleh yang memeriksa.

Perlu kewenangan menulis — `crime:write` untuk kejadian, `citizen_report:write` untuk
laporan masyarakat. Tanpa itu, kolomnya berbunyi "Perlu kewenangan menulis".

### Triase laporan masyarakat lewat Input Data

Formulir tersendiri untuk mengubah status laporan masyarakat. Berguna ketika beberapa
laporan ditriase berurutan tanpa mencarinya satu per satu di daftar.

> **Verifikasi adalah tindakan yang bermakna.** Laporan berstatus terverifikasi kelak
> ikut memengaruhi skor risiko. Untuk sekarang bobotnya masih nol — lihat §11.

---

## 8. PETA — DI MANA DAN MENGAPA

Menu **Live Map**.

### Cara memakai

1. Pilih layer: **Historis**, **Risiko Berjalan**, atau **Prediktif**.
2. Pada layer Historis, pilih jendela waktunya: **1 bulan**, **3 bulan**, **12 bulan**,
   atau **Seluruh data**. Pemilih ini hanya muncul di layer Historis, karena hanya di situ
   ia berpengaruh.
3. Arahkan kursor ke sebuah kecamatan untuk menyorotnya.
4. **Klik** kecamatan itu untuk membuka rinciannya di panel kanan.
5. Alamat halaman ikut berubah, sehingga tampilan itu **dapat dibagikan sebagai
   tautan** — berguna saat paparan.

### Tiga layer, tiga pertanyaan berbeda

| Layer | Menjawab | Satuannya | Warnanya |
|---|---|---|---|
| **Historis** | Di mana kejadian selama ini menumpuk | **Cacah kejadian** | Kuning-jingga |
| **Risiko Berjalan** | Di mana risikonya tinggi sekarang | Skor 0–100 berkelas | Tangga hijau→merah |
| **Prediktif** | Di mana risikonya diperkirakan tinggi | Skor 0–100 **tanpa kelas** | Sian |

Ketiganya digambar di bidang yang sama, jadi warnanya sengaja dibuat berjauhan — dari
kursi belakang ruang paparan, ketiganya tetap dapat dibedakan.

**Satu hal yang paling mudah keliru:** angka besar di tengah kecamatan berganti satuan
mengikuti layer. Pada layer Historis angka itu **jumlah kejadian** (bisa 180), pada dua
layer lain **skor 0–100**. Legenda di bawah peta selalu menyebutkan satuan yang sedang
berlaku.

### Membaca layer Historis

- **Bidang warna** = jumlah kejadian per kecamatan pada jendela terpilih.
- **Titik** = satu lokasi; luas lingkarannya sebanding dengan jumlah kejadian di situ.
- Kepekatan warnanya **relatif terhadap kecamatan terbanyak pada jendela yang sedang
  tampil** — bukan terhadap ambang apa pun. Berganti jendela berarti berganti pembanding,
  jadi warna yang sama di dua jendela berbeda **tidak** berarti jumlah yang sama. Angka
  puncak yang sedang berlaku selalu tertulis di legenda.
- Layer ini **tidak punya kelas risiko**, dan itu disengaja. Kecamatan dengan kejadian
  terbanyak belum tentu kecamatan paling rawan: cacah mentah tidak ditimbang dan tidak
  dinormalkan terhadap luas maupun jumlah penduduk.
- **Titik berada di koordinat lokasi, bukan di TKP sebenarnya.** Basis data mencatat
  kejadian pada `location_id` dan tidak menyimpan koordinat kejadiannya sendiri, sehingga
  seluruh kejadian pada satu lokasi menumpuk di satu titik.
- Karena bentuk wilayah hanyalah perkiraan, sebagian kecil titik dapat tampak sedikit
  melewati garis kecamatannya. Nama kecamatan yang benar selalu diambil dari data, bukan
  dari poligon tempat titik itu tergambar.

### Isi panel rincian

| Bagian | Isinya |
|---|---|
| Ancaman | Jenis ancaman di wilayah itu, berperingkat menurut skor |
| Jendela waktu | Jam-jam paling rawan |
| Riwayat | Jumlah kejadian historis dan rentang tanggalnya |
| Peringatan aktif | Peringatan yang masih menunggu tindakan |
| Prediksi | Prediksi teratas **beserta faktor dominannya** |

### Membaca faktor dominan — bagian terpenting

Setiap faktor membawa label sumbernya:

| Label | Artinya |
|---|---|
| **RULE** | Berasal dari aturan berbobot yang benar-benar dijalankan — **bukan** temuan model terlatih |
| **MODEL** | Kontribusi fitur dari model terlatih |

Pada prototipe ini **seluruh faktor berlabel RULE**. Label itu ditampilkan justru agar
tidak ada yang mengira sistem sudah memakai model pembelajaran mesin.

### Dua hal yang sengaja dibuat demikian

- **Layer prediktif tidak memiliki kelas risiko** (Rendah/Sedang/Tinggi/Kritis), hanya
  skor mentah. Sejak 9 September 2026 ini **keputusan pemilik proyek**, bukan kekurangan
  yang menunggu diperbaiki: tangga kelas ditetapkan pada hari yang sama, tetapi bagi
  penilaian keadaan **berjalan**. Skor prediksi 80 tidak menyatakan hal yang sama dengan
  skor penilaian 80, dan memakai satu tangga untuk keduanya membuat perkiraan terbaca
  sebagai keadaan.
- **Bentuk wilayah adalah perkiraan** dari titik koordinat lokasi, **bukan batas
  administratif resmi**. Ini dinyatakan di layar.

---

## 9. CRIME PATTERN DNA — POLA TIAP JENIS GANGGUAN

Menu **Pattern DNA**. Untuk satu jenis gangguan, lima dimensi ditampilkan berdampingan:

| Dimensi | Menjawab |
|---|---|
| **Where** | Kecamatan dan kategori TKP |
| **When** | Jam dan hari |
| **How** | Modus |
| **Target** | Objek sasaran |
| **Repeat** | Grid yang mengalami kejadian berulang |

**Ini analisis kejadian yang sudah terjadi — bukan prediksi.** Tidak ada skor risiko dan
tidak ada tingkat keyakinan di sini.

> **Tidak ada pola yang ditandai "signifikan".** Ambang untuk itu belum ditetapkan siapa
> pun. Sebagai gantinya tiap profil menyebut aritmetikanya: *"dihitung dari 76 kejadian;
> satu kejadian setara 1,3 persen poin"*. Untuk jenis dengan sedikit kejadian, kalimat
> itu sendiri sudah menyatakan kerapuhannya — dan itu lebih jujur daripada batas karangan.

Setiap persentase menyebut penyebutnya. "62%" tanpa "dari 464 kejadian" menyesatkan.

---

## 10. ANALYTICS — PERBANDINGAN LINTAS JENIS DAN WAKTU

Menu **Analytics**. Tiga sudut: **tren** per bulan, **matriks hari × jam** untuk melihat
jam rawan, dan **perbandingan antarwilayah**.

Bedanya dengan Pattern DNA: yang ini membandingkan **lintas jenis dan lintas waktu**,
sedangkan DNA memprofilkan **satu jenis** pada lima dimensinya. Perbandingan antarwilayah
karena itu sengaja **tidak menerima penyaring jenis** — menyaringnya ke satu jenis akan
mengubahnya menjadi dimensi Where milik DNA.

> **Perbandingan antarwilayah memakai jumlah mentah**, bukan angka per penduduk atau per
> luas — data wilayah tidak menyimpan keduanya. Ini dinyatakan di layar, karena tanpa itu
> kecamatan besar akan selalu tampak paling rawan.

---

## 11. PENILAIAN RISIKO — DARI MANA SKORNYA

Menu **Risk Scoring**. Menampilkan **dasar** perhitungan, bukan hanya hasilnya: versi
bobot yang berlaku, tiap faktor beserta bobotnya, dan jenis ancaman yang dicakup.

### Dua profil, karena dua jenis ancaman yang berbeda sifatnya

| | Kelompok A — kejahatan | Kelompok B — gangguan terencana |
|---|---|---|
| Contoh | Curanmor, Curat, Curas, Begal | Unjuk rasa, keramaian, tawuran |
| Diketahui | **setelah** terjadi | **sebelum** terjadi |
| Petunjuk utama | riwayat kejadian | informasi intelijen |
| Yang dinilai | kemungkinan terjadi | **dampak bila terjadi** |
| Peringatan terbit | skor ≥ 70 | skor ≥ **60** |

Ambang Kelompok B lebih rendah bukan karena lebih berbahaya, melainkan karena ia punya
**waktu persiapan**. Peringatan yang terbit sejam sebelum massa berkumpul sudah terlambat
untuk menyiapkan pengamanan.

### Menjalankan penilaian

Tersedia bagi Administrator. **Uji coba dijalankan lebih dulu** — hasilnya ditampilkan
sebelum satu baris pun ditulis. Menimpa penilaian pada tanggal yang sudah ada **ditolak**:
skor yang sudah dipakai menerbitkan peringatan tidak boleh berubah di belakang peringatan
itu.

Kombinasi yang salah satu faktornya tidak dapat dihitung **tidak diberi skor sama sekali**,
beserta alasannya — bukan diberi skor dengan bobot dibagi ulang, sebab itu berarti
mengarang bobot.

> Bobot dan ambang versi `dummy-v1` berstatus `FINAL` sejak 9 September 2026. Setiap baris
> skor menyimpan versi bobot yang menghasilkannya, sehingga angka lama tetap dapat
> ditelusuri meskipun bobotnya kelak diganti — dan penggantian itu menuntut versi baru,
> bukan penyuntingan versi yang sudah ditetapkan.

---

## 12. PREDICTION CENTER — MENJALANKAN DAN MEMPUBLIKASIKAN PREDIKSI

Menu **Prediction**. Menjalankan prediksi, meninjau hasilnya, lalu mempublikasikannya.

### Membaca horizon

**Horizon adalah jarak, bukan panjang rentang.** `24H` berarti hari berikutnya, `7D`
berarti tujuh hari ke depan — dan setiap prediksi tetap menunjuk satu **jendela enam jam**.
Karena itu jumlah baris satu penjalanan sama untuk semua horizon.

> `6H` dan `12H` menghasilkan hari sasaran yang sama. Itu bukan kekeliruan melainkan batas
> model data: tanggal prediksi disimpan tanpa jam, sehingga jarak enam dan dua belas jam
> sama-sama jatuh pada hari yang sama. Dinyatakan terbuka di layar.

### Dua langkah, sengaja terpisah

1. **Menjalankan** menghasilkan prediksi berstatus **Draf**.
2. **Mempublikasikan** mengubahnya menjadi **Terbit**.

Hanya prediksi terbit yang boleh melahirkan peringatan. Itulah sebabnya publikasi adalah
tindakan tersendiri — bukan efek samping menjalankan.

> **Ini bukan model terlatih.** Skor prediksi diproyeksikan dari penilaian risiko terakhir
> pada sel, jenis, dan jendela yang sama. Layar menyatakannya sendiri, dan setiap faktor
> berlabel `RULE`.
>
> *Confidence* berasal dari banyaknya kejadian historis yang menopang kombinasi itu, dan
> **tidak menurun** mengikuti panjang horizon — koefisien peluruhannya belum ditetapkan,
> dan mengarangnya akan membuat angka keyakinan tampak lebih berdasar daripada kenyataannya.

---

## 13. WARNING CENTER — MENANGANI PERINGATAN

Menu **Early Warning**.

### Status peringatan

| Status | Artinya |
|---|---|
| **ACTIVE** | Menunggu penanganan |
| **ACKNOWLEDGED** | Sudah diterima petugas |
| **RESOLVED** | Sudah tertangani |

### Langkah

1. Pilih peringatan dari daftar.
2. Panel kanan menampilkan prediksi sumbernya beserta faktor dominannya — **dasar**
   peringatan itu, bukan sekadar pemberitahuan.
3. Tekan **Terima Peringatan** (Administrator, atau Polsek di wilayahnya).
4. Tekan **Nyatakan Selesai** bila sudah tertangani (Administrator).

Tombol hanya muncul bila status **dan** kewenangan mengizinkan. Bila Anda tidak
berwenang, layar menyatakannya terus terang.

---

## 14. REKOMENDASI & KEPUTUSAN — INTI SISTEM

Menu **Recommendation**. **Bagian ini yang membuat sistem dapat dipertanggungjawabkan.**

### Membaca daftar

Terbagi dua: **Menunggu Keputusan** dan **Sudah Diputus**. Yang menunggu diletakkan
lebih dulu, karena itulah yang menuntut tindakan.

Kalimat usulan **dibangkitkan dari prediksi yang dirujuknya**, bukan diambil dari daftar
kalimat siap pakai. Satu butir menyebut tindakan menurut fungsi yang diminta bertindak,
kelurahan dan kecamatannya, jendela waktunya, jenis ancamannya, skor dan keyakinan
prediksinya, serta faktor yang paling berkontribusi:

> Tingkatkan patroli dan penjagaan di Karet Kuningan, Setiabudi pada 18:00-23:59 WIB
> terhadap CURANMOR. Dasar: prediksi PRD-00061 berskor 70/100 dengan keyakinan 88%, faktor
> terkuat kepadatan kejadian historis. Usulan, bukan perintah — keputusan tetap pada
> pejabat berwenang.

Kalimat penutupnya sama pada semua butir dengan sengaja: rekomendasi bukan perintah, dan
pernyataan itu tidak boleh berubah-ubah.

### Memutuskan (Pimpinan)

1. Pilih rekomendasi berstatus *Menunggu Keputusan*.
2. Baca usulan sistem, fungsi sasarannya, dan prediksi asalnya.
3. Pilih salah satu: **Setujui**, **Modifikasi**, atau **Tolak**.
4. Bila memilih **Modifikasi**, tuliskan rekomendasi yang telah disesuaikan. Isian ini
   **wajib** — modifikasi tanpa isi baru tidak bermakna.
5. Tuliskan pertimbangan Anda.
6. Tekan **Catat Keputusan**.

### Setelah diputus

Layar menampilkan **usulan asli sistem** dan **rekomendasi hasil penyesuaian pejabat**
secara berdampingan, beserta pertimbangan dan waktunya.

Inilah bukti visual yang paling penting bagi sistem ini: yang dijalankan di lapangan
adalah **penilaian manusia**, bukan keluaran mesin yang diteruskan begitu saja.

> Keputusan bersifat **final** dan tidak dapat diubah. Aturan tentang pembatalan
> keputusan menunggu penetapan SOP.

---

## 15. OPERASI — TINDAKAN DAN HASIL NYATA

Menu **Operations**. Di sinilah keputusan menjadi kegiatan, dan kegiatan menjadi bahan
evaluasi.

Daftar terbagi tiga menurut **ada-tidaknya hasil**, bukan menurut tanggal:

| Kelompok | Artinya |
|---|---|
| Sudah diputus, belum ditindaklanjuti | Keputusan sudah diambil tetapi belum dijalankan |
| Berjalan, hasil belum tercatat | Penugasan sudah dibuat, hasilnya belum dilaporkan |
| Hasil sudah tercatat | Selesai |

Pembagian itu yang membuat **lengan yang menganga terlihat**. Keputusan yang diambil lalu
tidak pernah dijalankan sebelumnya tidak dapat dilihat dari mana pun.

### Mencatat penugasan

Pilih keputusan dari antrean, tentukan satuannya. Lokasinya **tidak diisi bebas** —
diambil dari prediksi yang mendasarinya, agar tindakan tetap dapat ditelusuri ke wilayah
yang diprediksi.

### Mencatat hasil

Pilih **Selesai** atau **Dibatalkan**, tuliskan hasilnya, dan **sebutkan waktu selesainya**.
Waktu selesai diminta, bukan diisi otomatis: penugasan yang dibuat dan diselesaikan pada
sesi yang sama akan berdurasi nol, dan mengarang durasinya berarti memasukkan angka palsu
ke data yang justru dipakai evaluasi.

Hasil yang sudah tercatat **tidak dapat diubah** dari layar.

---

## 16. EVALUASI — MENILAI KETEPATAN

Menu **Evaluation**.

| Metrik | Artinya |
|---|---|
| **Precision** | Dari seluruh prediksi, berapa bagian yang benar-benar terjadi |
| **Recall** | Dari seluruh kejadian nyata, berapa bagian yang berhasil diprediksi |
| **False Positive** | Diprediksi, tetapi tidak terjadi |
| **False Negative** | Terjadi, tetapi **tidak** diprediksi |

**Mengapa *false negative* penting.** Sistem evaluasi yang hanya membandingkan
"prediksi → kenyataan" membuat kejadian yang terlewat menjadi tidak terlihat, sehingga
angka ketepatan tampak jauh lebih baik daripada kenyataannya. Sistem ini sengaja
mencatat kejadian yang tidak diprediksi, agar *recall* benar-benar dapat dihitung.

Seluruh angka bertanda **`PROPOSED`** karena aturan pencocokan prediksi dengan kejadian
nyata belum ditetapkan resmi.

---

## 17. LAPORAN MASYARAKAT

### Bagaimana masyarakat mengirim laporan

Warga **tidak masuk ke aplikasi ini**. Mereka membuka halaman muka dan menekan **Lapor
Kejadian**:

```text
siintel.awansurya.com  →  Lapor Kejadian  →  formulir  →  nomor tiket
```

Tanpa akun, tanpa pendaftaran, tanpa identitas. Yang diterima pelapor sebagai bukti
pengiriman adalah **nomor tiket** seperti `RPT-0151` — satu-satunya penanda yang
dipegangnya, dan ia tidak terikat ke nama siapa pun.

Yang **tidak** ada di formulir itu, dan ketiadaannya disengaja:

| Tidak ada | Alasannya |
|---|---|
| Kolom nama, telepon, alamat pelapor | Basis data memang tidak punya tempat untuk itu. Menyediakan kolomnya hanya akan menampung data yang lalu dibuang, sementara pelapor mengira datanya tersimpan |
| Unggah foto atau video | Menyimpan berkas warga menyentuh retensi dan klasifikasi data — keputusan kebijakan yang belum diambil, bukan pekerjaan yang belum sempat |
| Penanda "mendesak" | Urgensi ditetapkan petugas saat triase. Bila pelapor dapat mengisinya, siapa pun dapat menaikkan prioritas laporannya sendiri |

Yang dijaga di sisi sistem:

- **Kategori dari daftar tertutup**, bukan isian bebas. Dua ejaan untuk satu hal akan
  memecah seluruh analisis pola, dan pada kanal publik ejaannya pasti bermacam-macam.
- **Lokasi sebatas kecamatan.** Pelapor memilih kecamatan dan boleh menambahkan keterangan
  tempat sebagai teks. Titik pada peta adalah pusat kecamatan, **bukan TKP sebenarnya** —
  dan itu dinyatakan di layar.
- **Paling banyak 10 laporan per jam dari satu jaringan.** Longgar dengan sengaja: satu
  kantor atau satu keluarga dapat berbagi satu alamat IP.
- **Kejadian paling lama 30 hari ke belakang.** Yang lebih lama diarahkan ke Polsek
  setempat.
- **Setiap pengiriman tercatat di jejak audit tanpa nama pengguna** — memang tidak ada
  pengguna di baliknya, dan mengarangnya akan merusak arti kolom itu.

> **Halaman itu menyatakan sendiri bahwa ia bukan pengganti laporan polisi resmi**, dan
> mengarahkan keadaan darurat ke **110**. Peringatan itu diletakkan **di atas** formulir,
> bukan di bawah tombol kirim: orang yang sedang panik tidak membaca catatan kaki.

Laporan yang masuk berstatus **Diterima** dan menunggu verifikasi petugas. Selama belum
diverifikasi, ia tidak menjadi dasar tindakan.

### Mencari dan menyaring

Menu **Laporan Masyarakat** dan **Laporan Petugas** sama-sama memiliki panel **Cari dan
Saring** di atas daftarnya:

| Isian | Mencari pada |
|---|---|
| **Cari** | Kode, kategori atau jenis, isi laporan, wilayah, modus |
| **Tanggal dari / sampai** | Tanggal lapor (masyarakat) atau tanggal kejadian (petugas) |
| **Penyaring** | Tahapan/status, kategori atau jenis, dan kecamatan |

Hasil saringan **tersimpan di alamat halaman**, sehingga tautannya dapat dibagikan — berguna
saat meminta rekan melihat hal yang sama, dan saat paparan. Tombol mundur peramban bekerja
seperti yang diharapkan, dan **Hapus saringan** mengembalikan daftar utuh.

Penyaringan wilayah tetap ditegakkan server: saringan di layar hanya **mempersempit** apa
yang sudah menjadi hak Anda, tidak pernah memperluasnya.

### Yang dilihat petugas

Menu **Masyarakat**. Ringkasan sinyal dari masyarakat: jumlah per status dan kategori,
wilayah dengan laporan terbanyak, dan daftar laporan yang dapat disaring. Triasenya
dikerjakan dari tab **Triase** pada menu **Input Data** (§7).

> **Laporan masyarakat belum memengaruhi skor risiko sama sekali.** Spesifikasi menuntut
> klasifikasi, deteksi duplikasi, deteksi spam, dan validasi analis lebih dulu — keempatnya
> belum ada. Kalimat itu dibawa setiap tampilan, bukan disembunyikan.
>
> Skor urgensi dan skor verifikasi pada tiap laporan adalah nilai sintetis berstatus
> `DEMO`, **bukan** hasil penilaian model.

Laporan **tidak menyimpan identitas pelapor** — tidak ada nama, telepon, maupun NIK. Itu
rancangan yang disengaja, dan itu pula sebabnya masyarakat bukan salah satu peran pada §3:
kanal pelaporan berdiri terpisah dari sistem ini.

Sebagian laporan tidak tertaut ke sel grid mana pun. Laporan seperti itu **tidak
diberikan** kepada petugas yang dibatasi wilayah — menebak wilayahnya berarti mengarang
lokasi, dan menyertakannya berarti membocorkan laporan luar wilayah.

---

## 18. LAPORAN INTELIJEN

Menu **Intelligence**. Daftar laporan intelijen beserta kategori, wilayah, keandalan
sumber, tingkat keyakinan, urgensi, dampak, dan statusnya.

> **Keandalan dan keyakinan di sini dicatat manusia**, bukan keluaran model — berbeda
> artinya dari *confidence* pada prediksi. Layar menyatakan perbedaan itu tepat di bawah
> ketiga angkanya.

Peran **Fungsi** untuk sementara tidak berwenang membaca laporan intelijen. Kewenangan itu
dicabut karena pembatasannya menurut fungsi tidak dapat ditegakkan pada model data
sekarang, dan menaikkannya menjadi akses penuh adalah pelebaran kewenangan yang menunggu
keputusan pemilik proyek. Layar menyatakan hal ini, bukan menampilkan halaman kosong.

---

## 19. ADMINISTRASI — PENGGUNA DAN PERAN

Menu **Admin**. Daftar pengguna beserta peran dan **status kredensialnya**, daftar peran
beserta jumlah pemegang dan kewenangannya, serta formulir memindahkan penugasan.

### Yang dapat diubah

Hanya empat hal: **peran**, **polsek**, **fungsi**, dan **status akun**. Empat penolakan
ditegakkan sistem, dan masing-masing punya alasan:

| Ditolak | Mengapa |
|---|---|
| Mengubah password lewat layar | Password hanya ditetapkan lewat perintah di server. Kredensial tidak boleh melewati jalur yang sama dengan pengelolaan data |
| Mengubah peran **sendiri** | Bila bisa, seorang Administrator dapat mengangkat dirinya menjadi Pimpinan, dan seluruh pemisahan kewenangan runtuh |
| Menghabiskan pemegang persetujuan terakhir | Tanpa Pimpinan, tidak ada yang dapat menyetujui rekomendasi — rantai human-in-the-loop mati. Berlaku juga untuk **menonaktifkan** akunnya, sebab akibatnya sama persis |
| Memberi peran ber-cakupan tanpa atributnya | Akun Polsek tanpa polsek akan ditolak setiap layar dan tampak seperti sistem rusak |

Setiap perubahan tercatat audit beserta nilai **sebelum dan sesudah**. Bidang yang
menyerupai kredensial tidak pernah masuk ke catatan itu — bahkan nilainya tidak, hanya
nama bidangnya.

### Menetapkan password

Di server, lewat perintah:

```bash
pnpm prod:password -- <username>
```

Password diketik pada prompt tersembunyi — **ketikan tidak terlihat di layar**, dan itu
normal. Panjang minimal 12 karakter. Melihat daftar akun beserta status kredensialnya:

```bash
pnpm prod:users
```

### Yang belum dapat dilakukan dari layar

- **Membuat dan menghapus pengguna.** Menghapus akan gagal karena akun dirujuk keputusan
  dan tindakan yang tercatat; membuat memerlukan penetapan password yang jalurnya sengaja
  terpisah.
- **Menyunting kewenangan sebuah peran.** Daftar permission berasal dari berkas
  konfigurasi dan diselaraskan saat seed. Menyuntingnya lewat layar akan membuat berkas
  itu berhenti menjadi sumber kebenaran. Layar menampilkannya, dan menyebut asalnya.
- **Menelusuri audit trail.** Catatannya ada dan bertambah terus, tetapi layar pembacanya
  belum dibangun.

---

## 20. JEJAK AUDIT — MENELUSURI SIAPA MELAKUKAN APA

Menu **Audit**. Kewenangan `audit:read` — dimiliki Pimpinan dan Administrator.

### Yang dibuka lebih dulu: penolakan

Layar ini membuka **percobaan yang ditolak**, bukan daftar keberhasilan. Itu disengaja:
yang pertama dicari saat memeriksa audit adalah percobaan yang gagal, dan audit yang hanya
menonjolkan keberhasilan hanya membuktikan bahwa yang berhasil memang berhasil.

| Hasil | Artinya |
|---|---|
| **Berhasil** | Permintaan berwenang dan aturannya terpenuhi |
| **Ditolak — kewenangan** | Peran pengguna tidak memiliki kewenangan itu |
| **Gagal — aturan** | Pengguna berwenang, tetapi permintaannya melanggar aturan bisnis — misalnya menyelesaikan peringatan yang sudah berstatus akhir |

Membedakan keduanya penting: yang pertama menunjukkan **pembatasan kewenangan bekerja**,
yang kedua menunjukkan **aturan bisnis bekerja**.

### Yang tercatat

Percobaan masuk, akses data sensitif, penerimaan dan penyelesaian peringatan, persetujuan
dan penolakan rekomendasi, pencatatan tindakan, pemasukan data, penjalanan penilaian dan
prediksi, perubahan penugasan pengguna — beserta nilai **sebelum dan sesudah**.

Peristiwa yang tidak dipicu pengguna ditandai **“peristiwa sistem, tanpa pengguna”** —
bukan diisi nama pengganti yang seolah-olah ada pelakunya.

### Dua sifat yang membuatnya bernilai sebagai bukti

**Hanya-tambah.** Tidak ada satu pun jalan mengubah maupun menghapus catatan audit —
termasuk bagi Administrator, dan termasuk lewat API. Catatan yang dapat disunting bukan
bukti. Ketiadaan jalan itu dijaga sebuah test yang memeriksa daftar endpoint yang
benar-benar terdaftar.

**Tidak dapat dibatasi wilayah.** Catatan audit tidak menyimpan lokasi, sehingga jejak ini
mustahil dipersempit per polsek. Itulah sebabnya kewenangan membacanya hanya diberikan
kepada peran bercakupan penuh — dan sebabnya `audit:read` dicabut sementara dari peran
Polsek dan Fungsi: memberikannya berarti memberi akses penuh, dan itu pelebaran kewenangan
yang menunggu keputusan pemilik proyek.

### Menyaring

Menurut hasil, jenis aksi, jenis sumber daya, dan rentang tanggal. Rentang dibaca sebagai
waktu setempat dan **mencakup seluruh hari yang dipilih** — memilih satu tanggal yang sama
untuk awal dan akhir tetap menampilkan aktivitas hari itu. Satu permintaan dibatasi 366
hari.

---

## 21. BATASAN YANG WAJIB DIPAHAMI

Bagian ini bukan penafian formalitas. Menyampaikannya terbuka justru yang membuat
klaim sistem ini dapat dipertahankan.

| Batasan | Keterangan |
|---|---|
| **Data sintetis** | Seluruh data adalah bangkitan, bukan data operasional Polres. Tidak ada identitas nyata |
| **Belum memakai model terlatih** | Prediksi berasal dari aturan berbobot. Seluruh faktor berlabel `RULE` |
| **Bobot dan ambang sudah ditetapkan, belum terbukti** | Versi `dummy-v1` berstatus `FINAL` sejak 9 September 2026. Ditetapkan berarti berlaku sebagai ketentuan, bukan berarti terbukti tepat — itu urusan evaluasi |
| **Prediksi bukan kepastian** | Menunjuk **wilayah dan rentang waktu**, bukan individu, dan bukan jaminan kejadian |
| **Bukan alat penindakan** | Keluaran sistem adalah bahan pertimbangan, bukan dasar tindakan terhadap seseorang |
| **Batas wilayah adalah perkiraan** | Bentuk pada peta diturunkan dari koordinat, bukan batas administratif resmi |

---
