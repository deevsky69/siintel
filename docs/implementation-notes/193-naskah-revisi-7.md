# 193 — Penyesuaian aplikasi dengan naskah Taskap revisi 7 (22 November 2026)

**USER DECISION.** Pemilik proyek, 22 November 2026: naskah
`docs/TASKAP_-_IRKHAMUL_KHAKIM_-_202608003058_REVISI_v7.docx` menjadi acuan, dan **aplikasi
yang disesuaikan, bukan naskahnya**. Salinan naskah "angka disamakan dengan aplikasi"
(catatan 190) tidak lagi menjadi acuan.

## Yang berubah pada naskah revisi 7 dan menyentuh aplikasi

| Naskah revisi 7 | Aplikasi sebelumnya | Sekarang |
|---|---|---|
| Luas kelurahan BPS, wilayah hukum 144,75 km² (Lampiran J bagian M) | perkiraan dari poligon peta, 145,73 km², berlabel PROPOSED | `config/ranking/kelurahan-area.yaml` berisi 28 luas BPS dari naskah; skrip pembangkit perkiraan dihapus |
| PAI: 3,05 dan 2,64 (2025); 1,47 dan 1,29 (Jan–Ags 2026); porsi luas 9,84% / 10,51% / 12,08% / 12,66% | 3,08 / 2,72 / 1,49 / 1,30 | **sama dengan naskah** |
| Pembanding acak 6/65 = 9,23%; 58,5 dan 44,6 kejadian; kelipatan 3,25× / 3,01× / 1,93× / 1,77× | tidak ada | baris "Acak 6 dari 65" dan kolom "Kelipatan acak" — **sama dengan naskah** |
| PAI bulanan AI lebih tinggi pada 8 dari 12 bulan 2025 dan 5 dari 8 bulan 2026 | tidak ada | kolom "PAI model unggul" — **8 dan 5** |
| Peta Okt–Des 2024: 147, porsi luas 9,67%, PAI 2,40, 2,51× | hanya cakupan | **sama dengan naskah** |
| Sasaran 3.3.1 dan Lampiran L: cakupan AI tiga siklus melampaui historis terbaik ≥ 1 poin persen dengan PAI ≥ 2,0; bila belum, peringkat historis terbaik dipakai | penjaga: 12 bulan, cukup "lebih tinggi" | penjaga `guard` di `config/ranking/monthly.yaml`: `months: 3`, `min_margin_pct: 1.0`, `min_pai: 2.0` |
| Model AI Jan–Ags 2026: 86 (17,81%) | 86 | sudah sama |

Muatan dan ringkasan SOP pada halaman SOP & modul dicocokkan kalimat demi kalimat dengan
revisi 7: tidak ada yang berbeda.

## Keputusan teknis

- **TECHNICAL DECISION — kelurahan tanpa luas.** Naskah hanya memuat 28 kelurahan. Bila ada
  kelurahan pilihan di luar itu, PAI metode tersebut tidak dihitung (kosong), persis seperti
  naskah ("PAI … tidak dihitung"). Perkiraan dari sumber lain tidak dicampurkan.
- **TECHNICAL DECISION — angka sebatas satu Polsek.** PAI tidak dihitung, karena pembaginya
  (luas wilayah hukum) hanya ada untuk seluruh Polres.
- **TECHNICAL INFERENCE — "rata-rata cakupan tiga siklus".** Dihitung sebagai kejadian
  tercakup tiga bulan dibagi kejadian aktual tiga bulan, dan PAI = cakupan itu dibagi
  rata-rata bulanan porsi luas — cara yang sama dengan tabel Lampiran J bagian M.
- Penjaga hanya menentukan metode bawaan untuk peringkat yang BELUM dibekukan; peringkat
  beku dan produk yang sudah berjalan tidak berubah.

## Dampak ambang baru pada data Pusiknas (dihitung, bukan diandaikan)

Bulan sasaran → dasar prioritas: Mei–September 2025, November–Desember 2025, Januari 2026,
Juni 2026 → model. April dan Oktober 2025, Februari–Mei 2026, Juli–Oktober 2026 → peta
historis terbaik. Untuk Januari 2026 (bulan peragaan): selisih 3,36 poin persen, PAI 3,26 →
model tetap dasar.

## Yang BELUM sama dan tidak dapat disamakan dari sisi aplikasi

1. **Skenario tetap "AI tetap (data s.d. 2024)"**: naskah 149 kejadian, porsi luas 10,13%,
   PAI 2,32; aplikasi 148, 10,03%, 2,33. Begitu pula uji 4 dan 8 kelurahan (naskah
   139/235/63/119; aplikasi 138/237/67/103). Lebih dari 70 varian model sudah diuji
   (catatan 189–190) tanpa satu pun yang menghasilkan semua angka naskah sekaligus; kode
   aslinya (`Uji_Prediksi_2025_Pusiknas.xlsx`, lembar "Replikasi Python") diperlukan.
   Angka tidak boleh ditulis tangan ke aplikasi (CLAUDE.md §18, §27).
2. **Naskah revisi 7 tidak seragam di dalam dirinya** — REQUIRES USER DECISION:
   - Gambar 4.3 dan Lampiran I butir 7 memuat pemeriksaan **Wakasatintelkam**; Lampiran D dan
     Lampiran M masih menulis rantai tanpa Wakasat ("KBO memeriksa mutu, Kasatintelkam
     menelaah").
   - Tabel Bab IV menulis model 2026 = **86**; Lampiran D masih menulis "273 dari 1.117"
     (190 + 83). Dengan 86 jumlahnya 276.
   - Lampiran D/M masih menulis "tiga kartu Bulan ini", "Staf Intelkam", dan "Administrator
     55 izin"; aplikasi mengikuti keputusan 19–21 November 2026 (Analis Intelkam, Wakasat,
     Administrator memegang seluruh 65 izin, ringkasan wilayah lewat Humas).
   Aplikasi dibiarkan mengikuti batang tubuh naskah dan keputusan pemilik proyek.
3. Lampiran K huruf F masih menyebut "usulan kecocokan AI"; di aplikasi itu aturan tertulis
   dan tidak diberi label AI (CLAUDE.md §27).

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh; test baru untuk luas
BPS, pembanding acak, dan ambang. Angka pada tabel di atas dihitung dengan `backtest` pada
data Pusiknas lokal. Web `tsc`, `biome`, `vitest`, `next build`; layar Evaluasi diperiksa
lewat potret pada salinan lokal.
