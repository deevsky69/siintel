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
| **Penguji Taskap** | §2 Gagasan pokok · §3 Pemisahan kewenangan · §16 Evaluasi · §21 Batasan |

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

---

## 5. DASHBOARD — LAYAR PERTAMA

Ringkasan situasi terkini dalam satu layar.

| Panel | Isinya | Yang perlu diperhatikan |
|---|---|---|
| Indeks keamanan | Angka 0–100 | **Selalu disertai keterangan asalnya.** Ini bukan indeks resmi Polri |
| Kejadian & prediksi 24 jam | Jumlah terbaru | Mengikuti waktu acuan sistem |
| Ancaman teratas | Jenis ancaman berperingkat | Diurut menurut skor risiko |
| Risiko per kecamatan | Wilayah berperingkat | Menunjukkan mana yang perlu perhatian |
| Peringatan dini | Peringatan aktif dengan risiko tertinggi | Jalan masuk ke Warning Center |
| Rekomendasi | Usulan tindakan | Disertai penegasan bahwa ini bukan perintah |
| Outlook prediktif | Prediksi tiap horizon waktu | Horizon tanpa prediksi ditandai, bukan diisi angka |
| Tren & status patroli | Tren bulanan dan kesiapan unit | |

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

1. Pilih layer: **Risiko Berjalan** atau **Prediktif**.
2. Arahkan kursor ke sebuah kecamatan untuk menyorotnya.
3. **Klik** kecamatan itu untuk membuka rinciannya di panel kanan.
4. Alamat halaman ikut berubah, sehingga tampilan itu **dapat dibagikan sebagai
   tautan** — berguna saat paparan.

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

Menu **Community**. Ringkasan sinyal dari masyarakat: jumlah per status dan kategori,
wilayah dengan laporan terbanyak, dan daftar laporan yang dapat disaring.

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

## 20. YANG DICATAT SISTEM

Aktivitas berikut tercatat beserta waktu, pelaku, dan hasilnya:

- percobaan masuk, berhasil maupun gagal;
- akses ke data sensitif;
- penerimaan dan penyelesaian peringatan;
- **persetujuan, modifikasi, dan penolakan rekomendasi**;
- percobaan akses **tanpa kewenangan**.

Catatan yang terakhir itu yang membuat audit ini bermakna: catatan yang hanya memuat
keberhasilan tidak dapat dipakai menilai apakah pembatasan kewenangan benar-benar
bekerja.

Catatan audit bersifat **hanya-tambah** — tidak dapat diubah maupun dihapus dari
aplikasi.

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
