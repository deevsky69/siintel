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
| Pejabat yang menyetujui rekomendasi | §3, §5, §7 |
| Petugas Command Center | §3, §5, §6 |
| Analis | §3, §5, §8 |
| Petugas Polsek | §3, §5 |
| Administrator | §3, §9 |
| Penguji / peninjau | §2, §4, §10, §11 |

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

## 3. ENAM PERAN DAN FUNGSINYA

Pemisahan peran di sini bukan sekadar pengelompokan menu. Ia menjalankan **pemisahan
kewenangan**: tidak ada satu akun pun yang dapat mengusulkan, menyetujui, dan
melaksanakan sekaligus.

### 3.1 Ringkasan

| Peran | Tugas pokok dalam sistem | Cakupan data | Kewenangan khas yang tidak dimiliki peran lain |
|---|---|---|---|
| **Pimpinan** | Menilai dan memutuskan rekomendasi | Seluruh Polres | **Satu-satunya** yang dapat menyetujui, memodifikasi, atau menolak rekomendasi |
| **Command Center** | Menjalankan pengendalian harian | Seluruh Polres | Menerima dan menyelesaikan peringatan; mencatat pelaksanaan operasi |
| **Analyst** | Menyiapkan bahan analisis dan prediksi | Seluruh Polres | Menjalankan penilaian risiko, prediksi, publikasi prediksi, dan evaluasi |
| **Fungsi** | Menindaklanjuti sesuai fungsi masing-masing | **Hanya fungsinya sendiri** | Menulis laporan intelijen dan kegiatan fungsinya |
| **Polsek** | Bertindak di wilayah hukumnya | **Hanya polseknya sendiri** | Menerima peringatan di wilayahnya; mencatat laporan masyarakat |
| **Administrator** | Mengelola akun, peran, dan konfigurasi | Seluruh Polres | Mengelola pengguna dan peran |

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

> Pimpinan **sengaja tidak** dapat menerima atau menyelesaikan peringatan harian. Itu
> pekerjaan Command Center. Pemisahan ini yang membuat sistem tidak menumpuk seluruh
> kewenangan pada satu akun.

#### Command Center

Mata dan tangan pengendalian harian. Command Center memantau peringatan yang aktif,
**menerima** peringatan sebagai tanda sudah ditangani, dan **menyatakan selesai** bila
situasinya sudah tertangani. Ia juga mencatat pelaksanaan tindakan operasional yang
sudah disetujui Pimpinan.

Command Center **dapat menyusun** rekomendasi, tetapi **tidak dapat menyetujuinya
sendiri** — usulan tetap harus melewati Pimpinan.

#### Analyst

Peran teknis di hulu. Analyst menyiapkan bahan: memasukkan dan mengoreksi data
kejadian, menjalankan penilaian risiko, menjalankan dan mempublikasikan prediksi, serta
menjalankan evaluasi ketepatan prediksi.

Analyst melihat semuanya dan menyentuh hampir semuanya — tetapi **tidak dapat
memutuskan apa pun**. Itu disengaja: yang menyiapkan angka tidak boleh menjadi yang
menyetujui tindakan atas angka itu.

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
menyatakannya selesai** — penutupan peringatan tetap kewenangan Command Center.

#### Administrator

Mengelola akun, peran, dan konfigurasi sistem. Perhatikan yang **tidak** dimilikinya:
Administrator **tidak dapat menyetujui rekomendasi**, dan **tidak dapat menjalankan
prediksi**. Kewenangan teknis atas sistem sengaja dipisahkan dari kewenangan
operasional atas keputusan.

### 3.3 Prinsip yang mendasari pembagian ini

| Prinsip | Wujudnya di sistem |
|---|---|
| Pemisahan kewenangan | Yang menyiapkan (Analyst) ≠ yang memutuskan (Pimpinan) ≠ yang melaksanakan (Command Center, Fungsi, Polsek) |
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

## 6. PETA — DI MANA DAN MENGAPA

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

## 7. WARNING CENTER — MENANGANI PERINGATAN

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
3. Tekan **Terima Peringatan** (Command Center atau Polsek di wilayahnya).
4. Tekan **Nyatakan Selesai** bila sudah tertangani (Command Center).

Tombol hanya muncul bila status **dan** kewenangan mengizinkan. Bila Anda tidak
berwenang, layar menyatakannya terus terang.

---

## 8. REKOMENDASI & KEPUTUSAN — INTI SISTEM

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

## 9. EVALUASI — MENILAI KETEPATAN

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

## 10. ADMINISTRASI AKUN

Penetapan password **hanya** dilakukan di server melalui perintah, tidak pernah lewat
berkas atau kode:

```bash
pnpm prod:password -- <username>
```

Password diketik pada prompt tersembunyi — **ketikan tidak terlihat di layar**, dan itu
normal. Panjang minimal 12 karakter.

Melihat daftar akun beserta status kredensialnya:

```bash
pnpm prod:users
```

---

## 11. YANG DICATAT SISTEM

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

## 12. BATASAN YANG WAJIB DIPAHAMI

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

## 13. YANG BELUM DIBANGUN

Empat menu masih berupa rencana, dan ketika dibuka menyatakannya terus terang beserta
nomor pekerjaannya: **Prediction Engine**, **Analytics**, **Intelligence**, dan
**Administrasi**.

Menampilkannya sebagai rencana — bukan menyembunyikannya, dan bukan pula mengisinya
dengan angka contoh — adalah pilihan yang disengaja. Sistem yang menyatakan batasnya
sendiri lebih dapat dipercaya daripada sistem yang tampak selesai seluruhnya.
