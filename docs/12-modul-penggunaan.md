# MODUL TATA CARA PENGGUNAAN — PREDIKSI PRESISI

Sistem Deteksi Dini Kerawanan Kamtibmas berbasis *Predictive Policing*
Polres Metro Jakarta Selatan

> **Versi halaman.** Modul ini juga disajikan di dalam aplikasi pada `/modul.html`
> (tautan **Modul** di bilah atas), dengan tata letak siap cetak. Berkasnya ada di
> `apps/web/public/modul.html`; dokumen inilah acuannya bila keduanya berbeda.
>
> **Status prototipe.** Seluruh angka pada aplikasi ini berasal dari **data sintetis**,
> dan bobot maupun ambangnya berstatus `DEMO / PROPOSED` — belum ditetapkan sebagai
> ketentuan resmi. Modul ini menjelaskan cara kerja sistem, bukan menyatakan bahwa
> angkanya sudah dapat dipakai sebagai dasar tindakan nyata.

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
- Halaman masuk memuat jalan kembali ke **Lapor Kejadian** dan **Halaman Muka**, untuk warga
  yang salah menekan tombol.

### Susunan menu

Menu dikelompokkan menurut **apa yang Anda lakukan**, bukan menurut jenis datanya:

| Kelompok | Isinya | Untuk |
|---|---|---|
| **Putuskan** | Keputusan · Peringatan · Operasi | Hal yang menunggu tindakan seseorang |
| **Pantau** | Beranda · Brief · Peta | Keadaan sekarang |
| **Telaah** | Prediksi · Skoring · Pola · Analitik · Evaluasi | Ditelusuri saat ada pertanyaan |
| **Data** | Input Data · Masyarakat · Intelijen | Pekerjaan harian petugas |
| **Sistem** | Audit · Admin | Pemeriksaan atas sistem |

**Putuskan diletakkan paling atas.** Bagi Pimpinan, menu **Keputusan** adalah satu-satunya
yang memuat sesuatu yang **hanya dapat diselesaikan olehnya**; sebelumnya ia berada di
urutan kesembilan tanpa satu pun penanda bahwa ada yang menunggu di dalamnya. Kini ia
membawa **lencana berisi jumlah rekomendasi yang menunggu keputusan Anda** — dan lencana
itu hanya muncul bagi yang berwenang memutuskan, karena angka yang tidak dapat Anda
selesaikan hanya menjadi kecemasan tanpa jalan keluar.

### Menu utama dan "Lainnya"

Sidebar hanya menampilkan menu **utama**; sisanya berada di balik tombol **Lainnya** yang
dapat dibuka. Tidak ada satu pun layar yang hilang — yang berubah hanya bahwa ia tidak ikut
dibaca setiap kali sidebar dipandang.

Aturan pemisahannya satu kalimat: **menu utama adalah yang dapat Anda kerjakan, ditambah
enam layar inti** (Keputusan, Beranda, Brief, Peta, Peringatan, Audit).

Layar inti tetap utama walau tidak ada yang dapat Anda kerjakan di sana, karena dua alasan
yang berbeda:

- **Beranda, Brief, Peta, Peringatan, Audit** adalah konteks untuk mengambil keputusan.
  Menyembunyikannya berarti menuntut keputusan tanpa konteks — hal yang paling ingin
  dihindari sistem ini.
- **Keputusan** adalah pekerjaan yang **dialamatkan kepada pembacanya**. Rekomendasi selalu
  menyebut fungsi yang menanganinya, dan bagi fungsi yang dialamati ia bacaan harian —
  bukan layar yang ditengok saat penasaran. Karena itu ia menu utama bagi setiap peran yang
  dapat membacanya, bukan hanya bagi Pimpinan yang memutuskannya.

Aturan ini **diturunkan dari kewenangan**, bukan dari daftar per peran yang ditulis tangan.
Daftar tulis tangan akan menua diam-diam setiap kali permission berubah, dan menuanya tidak
terlihat sebagai kesalahan apa pun — hanya sebagai menu yang terasa "agak aneh".

Hasilnya berbeda menurut peran:

| Peran | Menu utama | Di dalam "Lainnya" |
|---|---|---|
| **Pimpinan** | Keputusan · Peringatan · Beranda · Brief · Peta · Evaluasi · Audit | Operasi · Prediksi · Skoring · Pola · Analitik · Masyarakat · Intelijen |
| **Polsek** | Keputusan · Peringatan · Operasi · Beranda · Brief · Peta · Input Data · Masyarakat | Prediksi · Skoring · Pola · Analitik · Evaluasi · Intelijen |
| **Fungsi** | Keputusan · Peringatan · Operasi · Beranda · Brief · Peta · Input Data | Prediksi · Skoring · Pola · Analitik · Evaluasi |
| **Administrator** | 14 menu | Pola · Evaluasi |

> **Mengapa Pimpinan hanya tujuh.** Dari 22 kewenangan yang dipegang seorang Pimpinan,
> **20 di antaranya hanya membaca**. Persis dua membiarkannya mengubah sesuatu:
> menyetujui rekomendasi (`commander_decision:approve`) dan menjalankan evaluasi
> (`evaluation:run`) — dan keduanya tidak dipegang peran lain mana pun. Sebelumnya kedua
> menu itu tenggelam di antara dua belas menu bacaan yang tampil serupa.

"Lainnya" **terbuka sendiri** bila Anda sedang berada di salah satu isinya, supaya menu yang
sedang aktif tidak pernah hilang dari sidebar.

**Menu yang tidak dapat Anda pakai sama sekali tidak ditampilkan.** Seorang Pimpinan
misalnya tidak memegang satu pun izin tulis, sehingga menu **Input Data** dan **Admin**
tidak muncul — sebelumnya keduanya tampil dan hanya menyambut dengan kalimat "Akun Anda
tidak memiliki kewenangan".

> **Menyembunyikan menu bukan pengamanan.** Server tetap memeriksa setiap permintaan.
> Menyalin alamat halaman yang tersembunyi dan membukanya langsung tetap ditolak, dan
> percobaannya tercatat di jejak audit.

---

## 5. DASHBOARD — LAYAR PERTAMA

Layar ini tersusun mengikuti **urutan pertanyaan**, bukan urutan ketersediaan data:

```text
apa yang masuk hari ini
        ↓
bagaimana keadaan wilayah saya
        ↓
apa yang menuntut perhatian saya sekarang
        ↓
di mana saya menaruh sumber daya
```

Seluruh isinya dibatasi kewenangan Anda. Petugas Polsek melihat susunan yang sama berisi
wilayahnya sendiri.

### Empat kartu di baris pertama

| Kartu | Isinya | Yang perlu diperhatikan |
|---|---|---|
| **Laporan Masuk** | Jumlah laporan 24 jam terakhir | **Rinciannya tiga jenis**, dan ketiganya berbeda keandalan — lihat di bawah |
| **Status Wilayah** | Aman / Waspada / Siaga per kecamatan | Pemetaannya **belum disetujui** — lihat di bawah |
| **Perlu Perhatian Segera** | Butir yang masih menunggu manusia | Peringatan belum diterima, rekomendasi belum diputus, laporan belum diverifikasi |
| **Wilayah Prioritas** | Tiga kecamatan berisiko tertinggi | Menampilkan **sel tertinggi / rata-rata** berdampingan |

**"Laporan" bukan satu hal.** Sistem memuat tiga jenis catatan yang sama-sama disebut
laporan, dan kartu ini mencacahnya terpisah dengan sengaja:

| Jenis | Asalnya | Catatan |
|---|---|---|
| Kejadian kriminal | Dicatat petugas | Sudah terverifikasi |
| Laporan intelijen | Fungsi Intelkam | Dicacah **per hari**, bukan per 24 jam — tabelnya hanya menyimpan tanggal, tanpa jam |
| Laporan masyarakat | Warga | Termasuk yang **belum diverifikasi** |

Sebagian laporan masyarakat tidak memiliki lokasi yang cocok dengan master lokasi. Kartu
ini menyebut jumlahnya, karena laporan yang hilang tanpa keterangan hanya terlihat sebagai
angka yang lebih kecil — dan tidak ada cara membedakannya dari keadaan yang memang sepi.

### Status wilayah — yang harus Anda ketahui sebelum mengutipnya

Sistem memiliki **empat** kelas risiko (Rendah, Sedang, Tinggi, Kritis), sedangkan nama
status yang diminta hanya **tiga**. Dua kelas karena itu harus digabung, dan penggabungan
itu mengubah makna:

| Status | Berasal dari kelas |
|---|---|
| **Aman** | Rendah |
| **Waspada** | Sedang |
| **Siaga** | Tinggi + Kritis |

Yang digabung adalah dua kelas **teratas**, bukan dua kelas terbawah. Alasannya: kesalahan
kedua arah tidak sepadan. Menggabungkan dari atas hanya menyamakan dua kelas yang
sama-sama menuntut tindakan; menggabungkan dari bawah akan menyebut wilayah berkelas
Sedang sebagai "Aman", dan kata itu menghentikan orang bertanya lebih jauh.

> **Pemetaan ini berstatus PROPOSED dan belum disetujui siapa pun.** Layar menyatakannya
> sendiri. Bila SOP menetapkan pemetaan yang berbeda, yang perlu diubah hanya satu berkas
> konfigurasi — tidak ada satu pun ambang yang tertanam di kode.

Status satu kecamatan mengikuti **sel dengan skor tertinggi** di dalamnya, sama seperti
layer risiko berjalan pada peta. Definisi itu sengaja disamakan: dua layar yang menjawab
"berapa risiko di Tebet" dengan angka berbeda akan saling meruntuhkan, dan tidak ada di
layar yang akan menunjukkan mana yang benar. Kartu Wilayah Prioritas menampilkan rata-rata
seluruh sel di sebelahnya supaya selisih antara "sel terburuk" dan "keadaan menyeluruh"
tetap terbaca.

### Top area menurut jumlah laporan

Sepuluh wilayah dengan laporan terbanyak dalam 30 hari terakhir, bertingkat Kritis /
Sedang / Rendah.

> **Ini bukan peringkat kerawanan.** Yang diperingkat adalah **volume laporan**: tidak
> ditimbang, dan tidak dinormalkan terhadap luas maupun jumlah penduduk. Wilayah dengan
> pelaporan yang lebih aktif akan selalu naik, dan wilayah yang warganya jarang melapor
> akan selalu tampak lebih aman daripada kenyataannya.

Tingkatnya **relatif terhadap wilayah teratas pada jendela yang sedang tampil** — bukan
terhadap angka mutlak. Jumlah laporan yang sama dapat bertingkat berbeda di jendela lain.

### Isu menonjol sepekan

Cacah kejadian per jenis gangguan pada 7 hari terakhir, dibanding 7 hari sebelumnya.
Perubahan disajikan sebagai **selisih kejadian**, bukan persentase: dari basis satu
kejadian menjadi tiga, "naik 200%" terbaca jauh lebih dramatis daripada kenyataannya.

### Rekomendasi kebijakan

Usulan tindakan beserta fungsi yang menanganinya dan **dasar angkanya**.

> **Rencananya blok ini kelak dihasilkan AI. Sekarang belum.** Setiap butir diturunkan
> dengan **aturan** dari angka yang tampil di layar yang sama, dan diberi label `RULE` —
> label yang sama dengan faktor dominan pada peta. Menyebutnya keluaran AI sekarang akan
> menjadi penjelasan fiktif, dan justru pada blok inilah kebohongan itu paling mahal:
> inilah yang dibaca sebagai saran tindakan.
>
> Bila tidak ada yang dapat diturunkan dari data, blok ini **dibiarkan kosong** — bukan
> diisi saran umum yang terdengar masuk akal tetapi tidak bersandar pada apa pun.

Sebagian jenis rekomendasi belum mungkin dibuat sama sekali. Contohnya "rapat koordinasi
karena ada Car Free Day": sistem belum memuat kalender kegiatan, dan menambahkannya
menuntut **sumber data baru**, bukan sekadar aturan baru.

### Panel analitik — terlipat

Di bagian bawah terdapat "Panel analitik" yang **terlipat**; klik untuk membukanya. Isinya
panel yang sudah ada sebelumnya: indeks keamanan, peta ringkas, ancaman teratas, outlook
prediktif, tren bulanan, dan status patroli.

Panel itu tidak dihapus — ia masih dipakai peran selain Pimpinan — tetapi dikeluarkan dari
bacaan pertama. Enam panel teknis di bawah blok keputusan membuat halaman terlalu panjang
untuk dibaca sekali duduk, dan yang pertama dibaca seorang pimpinan seharusnya yang
menuntut keputusannya, bukan yang paling banyak angkanya.

> **Kebiasaan yang benar:** setiap angka turunan pada aplikasi ini membawa keterangan
> asal. Bacalah keterangan itu sebelum mengutip angkanya. Angka tanpa konteks adalah
> cara tercepat sebuah prototipe disalahpahami sebagai data resmi.

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

### Triase laporan masyarakat

Mengubah status laporan: Diterima → Diverifikasi → Diteruskan → Ditangani → Selesai.

Status **boleh mundur dan boleh melompat**. Itu disengaja: belum ada SOP yang menetapkan
urutannya wajib, dan melarangnya berarti laporan yang keliru diverifikasi tidak dapat
dikembalikan. Yang ditolak hanya memindahkan ke status yang sedang berlaku — itu
penjagaan catatan, bukan aturan alur kerja.

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
  skor mentah. Memberi kelas berarti menerapkan ambang yang belum ditetapkan resmi.
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

> Bobot dan ambang berstatus `DEMO / PROPOSED`, menunggu penetapan. Setiap baris skor
> menyimpan versi bobot yang menghasilkannya, sehingga angka lama tetap dapat ditelusuri
> meskipun bobotnya kelak diganti.

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
| **Bobot dan ambang belum resmi** | Berstatus `DEMO / PROPOSED`, menunggu penetapan |
| **Prediksi bukan kepastian** | Menunjuk **wilayah dan rentang waktu**, bukan individu, dan bukan jaminan kejadian |
| **Bukan alat penindakan** | Keluaran sistem adalah bahan pertimbangan, bukan dasar tindakan terhadap seseorang |
| **Batas wilayah adalah perkiraan** | Bentuk pada peta diturunkan dari koordinat, bukan batas administratif resmi |

---
