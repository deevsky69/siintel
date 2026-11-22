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
