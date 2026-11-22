# 190 — Pencocokan Lampiran J, K, dan M naskah revisi dengan aplikasi (22 November 2026)

Permintaan pemilik proyek 21 November 2026: "betulkan datanya agar sama persis, dan yang
lainnya dicocokkan dulu agar sama." Catatan ini mencatat apa yang dapat dan tidak dapat
disamakan dari sisi aplikasi, dan — untuk yang tidak dapat — **teks pengganti untuk naskah**.

## 1. Data: yang sama, dan yang tidak dapat disamakan tanpa menebak

Sama persis dengan naskah: jumlah dan rincian laporan (Tabel 4.1), kelompok uji (4.854
kejadian; 3.677 kejadian latih; 9.750 baris latih), **seluruh pembanding historis** pada uji
4, 6, dan 8 kelurahan (149/65, 176/79, 224/101), dan **uji utama enam kelurahan** per bulan
(190 dan 86; unggul/setara/lebih rendah 6/4/2 dan 4/1/3).

Tidak sama: uji tambahan 4 dan 8 kelurahan dan skenario tetap. Lebih dari tujuh puluh varian
cara hitung masukan model sudah diuji terhadap daftar per bulan pada Lampiran J (cara
menghitung rerata kelurahan sekecamatan, selisih rerata, konvensi sudut bulan, cara menghitung
sinus/kosinus, pembulatan, batas informasi data latih). Tidak ada yang mereproduksi keenam
angka sekaligus; model peka terhadap perbedaan pada digit terakhir bilangan pecahan, sehingga
yang menentukan adalah urutan operasi persis pada kode asli (lembar "Replikasi Python",
`Uji_Prediksi_2025_Pusiknas.xlsx`), yang tidak ada di server.

**Angka tidak ditulis tangan ke aplikasi.** Layar Evaluasi menampilkan hasil hitungan model
yang benar-benar dijalankan; mengisinya dengan angka naskah akan menjadikannya angka karangan
(CLAUDE.md butir 18 dan §27). Pilihannya tinggal dua: kode asli diserahkan, atau naskah
memakai angka aplikasi di bawah ini.

### Pengganti Lampiran J huruf K (hasil aplikasi, 22 November 2026)

| Periode | Kelurahan | AI perbulan | Pembanding historis | Selisih (poin persen) | Bulan unggul/setara/lebih rendah |
|---|---|---|---|---|---|
| 2025 | 4 | 138 (21,77%) | 149 (23,50%) | −1,74 | 0 / 8 / 4 |
| 2025 | 6 | 190 (29,97%) | 176 (27,76%) | +2,21 | 6 / 4 / 2 |
| 2025 | 8 | 237 (37,38%) | 224 (35,33%) | +2,05 | 5 / 5 / 2 |
| Jan–Ags 2026 | 4 | 67 (13,87%) | 65 (13,46%) | +0,41 | 3 / 3 / 2 |
| Jan–Ags 2026 | 6 | 86 (17,81%) | 79 (16,36%) | +1,45 | 4 / 1 / 3 |
| Jan–Ags 2026 | 8 | 103 (21,33%) | 101 (20,91%) | +0,41 | 4 / 1 / 3 |

Kalimat sesudah tabel perlu ikut berubah: pada empat kelurahan pembanding historis lebih
tinggi **pada 2025 saja**; pada 2026 AI sedikit lebih tinggi. Skenario tetap 2025: 148 dari
634 (23,34%), naskah 149 (23,50%).

### Ralat angka di bagian lain naskah

| Tempat | Tertulis | Seharusnya |
|---|---|---|
| Tabel 4.6, baris "Bulanan – AI", kolom Jan–Ags 2026 | 83 (17,81%) | **86 (17,81%)** |
| Tabel 4.6, baris "Akhir 2024 – AI untuk 12 bulan 2025" | 149 (23,50%) | 148 (23,34%) bila mengikuti aplikasi |
| Lampiran M, D.9 "Uji historis model" | 273 dari 1.117 (24,4%) | **276 dari 1.117 (24,7%)**; Peta 3 bulan 254 (22,7%) dan nilai uji tanda 0,133 tetap |

## 2. Lampiran M (panduan aplikasi) terhadap layar produksi

Empat puluh enam pernyataan Lampiran M diperiksa terhadap `sigap.awansurya.com` (akun
administrator, 22 November 2026). **Empat puluh sama**, termasuk seluruh bagian C (SIGAP
Bersama) dan angka pada Analitik, Mutu Data, Peta, serta menu. Enam berbeda — semuanya akibat
keputusan sesudah tangkapan layar Lampiran M diambil (19–20 November 2026):

| Bagian | Tertulis di Lampiran M | Keadaan aplikasi | Penyebab |
|---|---|---|---|
| B.1, D.7, E.5 | analis → KBO → Kasatintelkam → pimpinan; "lima tahap berjenjang" | **enam** langkah: analis, KBO, **Wakasatintelkam**, Kasatintelkam, pimpinan, pelaksanaan | Bab IV dan Gambar 4.3 naskah (catatan 188) |
| D.3 | tiga kartu "Bulan ini" | empat kartu pada akun administrator (tambahan: kegiatan di kelurahan prioritas) | administrator memegang seluruh kewenangan (catatan 187) |
| D.4 | lonceng terbagi tiga (darurat, laporan warga, ulasan) | pada akun administrator juga memuat produk bulanan dan buletin | catatan 187 |
| D.9 | 273 dari 1.117 (24,4%) | 276 dari 1.117 (24,7%) | angka model 86 (catatan 189) |
| D.16 | empat panel | lima panel: tambahan **Ringkasan wilayah untuk masyarakat** | persetujuan Humas (catatan 189) |
| D.18 | enam peran; Staf Intelkam; Administrator 55 | **sembilan** peran: Pimpinan 31, Kasat Intelkam 18, Wakasat Intelkam 18, KBO 18, Humas 8, Analis Intelkam 19, Fungsi 20, Polsek 31, Administrator 65 | catatan 186–188 |

Aplikasi tidak dapat dikembalikan agar sama dengan keenam butir ini tanpa membatalkan
keputusan yang justru diambil untuk menyamakannya dengan Bab IV; karena itu **Lampiran M yang
perlu disesuaikan**. Teks pengganti:

- **B.1 butir ketiga dan E.5:** "… disusun analis, diperiksa KBO dan Wakasatintelkam, ditelaah
  Kasatintelkam, lalu ditetapkan pimpinan."
- **D.7:** "Enam tahap berjenjang di bagian atas: (1) analis menyusun dan memeriksa, (2) KBO
  memeriksa mutu, (3) Wakasatintelkam memeriksa, (4) Kasatintelkam menelaah, (5) pimpinan
  menetapkan, (6) pelaksanaan dicatat." Langkah 3: "KBO memeriksa mutu daftar itu, lalu
  Wakasatintelkam memeriksanya. Kasatintelkam kemudian menelaahnya …"; "tahap keenam".
- **D.16:** "Halaman terdiri atas lima panel. … *Ringkasan wilayah untuk masyarakat* memuat
  jumlah kejadian dan sebaran tingkat kerawanan periode berjalan, yang baru tayang di SIGAP
  Bersama setelah disetujui Humas."
- **D.18:** ganti tabel dengan sembilan peran di atas; "Panel Peran & Kewenangan memuat
  sembilan peran."
- **C.1/C.2:** tambahkan satu kalimat: "Peta dan angka kerawanan tayang setelah ringkasan
  wilayah disetujui Humas."
- Halaman baru yang belum disebut Lampiran M: **SOP & modul** (dari Beranda) dan panel **Mutu
  draf dan waktu kerja** pada Evaluasi.

Butir bersyarat, bukan beda: pita merah "Segera" hanya tampil bila ada laporan mendesak yang
belum dipilah.

## 3. Lampiran K (mekanisme analisis) terhadap aplikasi

| Butir | Naskah | Aplikasi |
|---|---|---|
| A.6, D | analis → KBO → Kasatintelkam → Kapolres | memuat Wakasatintelkam (mengikuti Bab IV) — **naskah perlu disesuaikan** |
| E | rumus, skala, dan batas kategori IKW; status lengkap/sementara/ditahan; format isian dampak | sama |
| F "Peta kejadian" | kejadian resmi **dan kejadian tambahan terverifikasi** | peta belum menggambar kejadian tambahan — **belum ada** |
| F "Mutu data" | usulan kecocokan **AI** | usulan disusun aturan tertulis, bukan model — beda istilah |
| F "Tindak lanjut", "Evaluasi", "Rekomendasi", "Prediksi" | — | ada (Produk Bulanan, Evaluasi, Peringkat) |
| G | kalender harian sampai tahunan | aturan kerja; aplikasi tidak menjadwalkan atau mengingatkan |
| H | status "pengecekan tertunda" saat sumber tidak tersedia | **belum ada** pada Cek Kendaraan |
| H | pencocokan informasi warga dengan laporan SPKT | ada pada Mutu Data (wilayah sama, selisih ≤ 3 hari); belum memakai nomor laporan, ciri objek, dan uraian |
| I | Kabagops mengoordinasikan tindak lanjut; Humas menyajikan ringkasan yang disetujui | Humas sudah; **Bagops belum** menjadi pilihan fungsi (fungsi yang dikenal: Samapta, Binmas, Intelkam, Reskrim, Lantas) |

Tiga butir "belum ada" (kejadian tambahan pada peta, status pengecekan tertunda, Bagops
sebagai fungsi) adalah fitur baru; menambahkannya memerlukan keputusan pemilik proyek
(CLAUDE.md §14: fungsi baru meminta persetujuan).

## Cara pemeriksaan

Skrip peramban membaca teks tiap layar produksi dan mencocokkannya dengan pernyataan Lampiran
M; tiga laporan "beda" palsu (huruf besar pada tombol, waktu muat halaman masuk) diperiksa
ulang dengan tangan dan ternyata sama. Hasil model diambil dari
`GET /evaluation/monthly/backtest` produksi dan dari perhitungan ulang 4, 6, 8 kelurahan pada
data yang sama.

## 4. Salinan naskah dengan angka disamakan (22 November 2026)

Atas permintaan pemilik proyek ("data dibuat persis antara naskah dan aplikasi"), dibuat
salinan `docs/TASKAP - IRKHAMUL KHAKIM - 202608003058 REVISI - angka disamakan dengan
aplikasi.docx`. **Arahnya naskah mengikuti aplikasi** — arah sebaliknya memerlukan angka yang
ditulis tangan ke layar. Naskah asli tidak diubah. Seluruh 44 perubahan berupa
*perubahan terlacak* atas nama "Claude", sehingga dapat diterima atau ditolak satu per satu di
Word (Tinjau → Terima/Tolak).

Yang diubah hanya angka uji model; deskripsi data (Tabel 4.1, 4.2, 4.5) sudah sama dengan
basis data dan tidak disentuh, begitu pula kolom AI perbulan dan seluruh pembanding historis.

| Tempat | Semula | Menjadi |
|---|---|---|
| Tabel 4.6, AI tetap 2025 | 149 (23,50%) | 148 (23,34%) |
| Tabel 4.6, AI bulanan Jan–Ags 2026 | 83 (17,81%) | 86 (17,81%) |
| Lampiran J.C, AI tetap | 149 dari 634 | 148 dari 634 |
| Lampiran J.C, AI tetap (persen) | 23,50% | 23,34% |
| Lampiran J.F 2025-04, AI tetap | 14 | 13 |
| Lampiran J.F jumlah AI tetap | 149 | 148 |
| Lampiran J.K 2025, 4 kelurahan, AI | 139 (21,92%) | 138 (21,77%) |
| Lampiran J.K 2025, 4 kelurahan, selisih | −1,58 | −1,74 |
| Lampiran J.K 2025, 4 kelurahan, bulan unggul/setara/lebih rendah | 1 / 7 / 4 | 0 / 8 / 4 |
| Lampiran J.K 2025, 8 kelurahan, AI | 235 (37,07%) | 237 (37,38%) |
| Lampiran J.K 2025, 8 kelurahan, selisih | +1,74 | +2,05 |
| Lampiran J.K 2025, 8 kelurahan, bulan unggul/setara/lebih rendah | 6 / 3 / 3 | 5 / 5 / 2 |
| Lampiran J.K Jan–Ags 2026, 4 kelurahan, AI | 63 (13,04%) | 67 (13,87%) |
| Lampiran J.K Jan–Ags 2026, 4 kelurahan, selisih | −0,41 | +0,41 |
| Lampiran J.K Jan–Ags 2026, 4 kelurahan, bulan unggul/setara/lebih rendah | 3 / 2 / 3 | 3 / 3 / 2 |
| Lampiran J.K Jan–Ags 2026, 8 kelurahan, AI | 119 (24,64%) | 103 (21,33%) |
| Lampiran J.K Jan–Ags 2026, 8 kelurahan, selisih | +3,73 | +0,41 |
| Lampiran J.K Jan–Ags 2026, 8 kelurahan, bulan unggul/setara/lebih rendah | 6 / 1 / 1 | 4 / 1 / 3 |
| Lampiran J.K, kalimat sesudah tabel | Pada empat kelurahan, pembanding historis mencakup lebih banyak kej… | Pada empat kelurahan, pembanding historis mencakup lebih banyak kej… |
| Lampiran M D.9, uji historis | 273 dari 1.117 kejadian (24,4%) | 276 dari 1.117 kejadian (24,7%) |
| Lampiran J.H (12 baris), kolom AI tetap | daftar enam kelurahan | daftar menurut model yang berjalan (April 2025 berbeda satu kelurahan; urutan berbeda pada bulan lain) |
| Lampiran J.I dan J.J (20 baris), kolom AI perbulan | daftar enam kelurahan | urutan menurut model yang berjalan; **himpunan enam kelurahannya sama**, kecuali yang memang sudah sama urutannya tidak diubah |

Yang TIDAK diubah dan masih perlu disunting penulis sendiri (bukan angka uji): tahap
Wakasatintelkam pada Lampiran K, L, dan M; tabel peran D.18; jumlah panel D.16; jumlah kartu
dan isi lonceng D.3–D.4; kalimat PAI pada Bab III (lihat bagian 2 dan 3 catatan ini).
Dibuat oleh skrip yang membaca hasil model dari basis data yang sama dengan produksi dan
memeriksa lebih dulu bahwa kolom yang tidak diubah memang sudah sama.

## 5. Bagian non-angka pada salinan naskah ikut disunting (22 November 2026)

Atas permintaan pemilik proyek ("tolong anda yang sunting agar datanya menjadi sama persis"),
salinan pada bagian 4 disunting lagi: 24 perubahan terlacak tambahan dan lima gambar
Lampiran M diganti dengan tangkapan layar produksi 22 November 2026 (ukuran sama dengan
gambar asal): D.1 Beranda, D.10 Produk Bulanan, D.13 uji historis, D.26 dan D.27 Buletin &
Imbauan. Penggantian gambar tidak dapat ditandai sebagai perubahan terlacak.

| Tempat | Semula | Menjadi |
|---|---|---|
| Bab III, kalimat PAI | dihitung pada uji penerapan setelah luas resmi setiap kel… | dihitung pada uji penerapan setelah luas resmi setiap kelurahan dimasukkan ke dalam kam… |
| Lampiran K huruf A butir 6 | KBO memeriksa mutu; Kasatintelkam menelaah dan menyampaik… | KBO memeriksa mutu, Wakasatintelkam memeriksa, lalu Kasatintelkam menelaah dan menyampa… |
| Lampiran K huruf D, baris baru | (baris baru) | Wakasatintelkam | Memeriksa produk yang sudah lolos pemeriksaan KBO sebelum ditelaah Ka… |
| Lampiran L huruf A, formulir validasi | Penelaahan KBO/Kasatintelkam | Penelaahan KBO/Wakasatintelkam/Kasatintelkam |
| Lampiran M B.1 | disusun analis, diperiksa KBO, ditelaah Kasatintelkam, la… | disusun analis, diperiksa KBO dan Wakasatintelkam, ditelaah Kasatintelkam, lalu ditetap… |
| Lampiran M C.2, persetujuan Humas | Angka itu bukan ramalan tentang orang tertentu, sebagaima… | Angka itu bukan ramalan tentang orang tertentu, sebagaimana ditegaskan pada bagian bawa… |
| Lampiran M D.3, kartu | Tiga kartu "Bulan ini". | Kartu "Bulan ini" — tiga sampai empat kartu menurut kewenangan akun; pada akun administ… |
| Lampiran M D.3, langkah 1 | Baca tiga kartu "Bulan ini" | Baca kartu "Bulan ini" |
| Lampiran M D.3, contoh tahap | (pada contoh: menunggu telaah Kasatintelkam) | (pada contoh: menunggu pemeriksaan Wakasatintelkam) |
| Lampiran M, keterangan Gambar D.1 | Beranda SIGAP: baris atas, menu kiri, pita "Segera", dan … | Beranda SIGAP: baris atas, menu kiri, pita "Segera", dan kartu "Bulan ini". |
| Lampiran M D.4, lonceng | Daftar terbagi tiga: permintaan bantuan darurat yang haru… | Daftar memuat permintaan bantuan darurat yang harus diterima dan ditindaklanjuti, lapor… |
| Lampiran M D.7, tahap | Lima tahap berjenjang di bagian atas: (1) analis menyusun… | Enam tahap berjenjang di bagian atas: (1) analis menyusun dan memeriksa, (2) KBO memeri… |
| Lampiran M D.7, langkah 3 | KBO memeriksa mutu daftar itu. Kasatintelkam kemudian men… | KBO memeriksa mutu daftar itu, lalu Wakasatintelkam memeriksanya. Kasatintelkam kemudia… |
| Lampiran M D.7, langkah 6 | pelaksanaannya dicatat pada tahap kelima. | pelaksanaannya dicatat pada tahap keenam. |
| Lampiran M, keterangan Gambar D.10 | Produk Bulanan: lima tahap persetujuan dan daftar kelurah… | Produk Bulanan: enam tahap persetujuan dan daftar kelurahan prioritas. |
| Lampiran M D.16, panel | Halaman terdiri atas empat panel. Menunggu persetujuan me… | Halaman terdiri atas lima panel. Ringkasan wilayah untuk masyarakat memuat jumlah kejad… |
| Lampiran M D.18, jumlah peran | Panel Peran & Kewenangan memuat enam peran: | Panel Peran & Kewenangan memuat sembilan peran: |
| Lampiran M D.18, baris KBO | (baris baru) | 3 | KBO | 18 | Seluruh wilayah; memeriksa mutu produk bulanan |
| Lampiran M D.18, baris Wakasatintelkam | (baris baru) | 2 | Wakasatintelkam | 18 | Seluruh wilayah; memeriksa produk bulanan sesudah KBO |
| Lampiran M D.18, baris Humas | (baris baru) | 4 | Humas | 8 | Seluruh wilayah; menyetujui informasi untuk masyarakat |
| Lampiran M D.18, nama peran | Staf Intelkam | Analis Intelkam |
| Lampiran M D.18, kewenangan Administrator | 55 | 65 |
| Lampiran M D.18, batas Administrator | Seluruh wilayah; berwenang menyetujui rekomendasi | Seluruh wilayah; memegang seluruh kewenangan peran lain |
| Lampiran M E.5 | Analis menyusun, KBO memeriksa mutu, Kasatintelkam menela… | Analis menyusun, KBO memeriksa mutu, Wakasatintelkam memeriksa, Kasatintelkam menelaah,… |

Yang masih berbeda setelah ini, dan tidak dapat diselesaikan lewat penyuntingan naskah:

- Lampiran K huruf F, H, dan I menyebut tiga hal yang belum ada di aplikasi (kejadian tambahan
  pada peta, status "pengecekan tertunda", Bagops sebagai penerima) — dibiarkan apa adanya di
  naskah karena keputusannya (membangun fitur atau mengubah naskah) milik pemilik proyek.
- Gambar D.11 dan D.12 tidak diganti; isinya tidak berubah.
- Gambar D.1 diambil ulang setelah pembetulan teks kartu "Persetujuan warga" di-deploy
  (22 November 2026), sehingga tidak lagi memuat tulisan "imbauan bulanan otomatis".
