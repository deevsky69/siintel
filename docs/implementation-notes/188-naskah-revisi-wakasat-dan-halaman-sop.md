# 188 — Naskah Taskap revisi: tahap Wakasat Intelkam dan halaman SOP (21 November 2026)

**USER DECISION.** Pemilik proyek, 21 November 2026: aplikasi disamakan dengan
`docs/TASKAP - IRKHAMUL KHAKIM - 202608003058 REVISI.docx`, "termasuk muatan dan desain
SOPnya" (`docs/MUATAN SOP.jpeg` = Tabel 4.17, `docs/desain SOP.jpeg` = Gambar 4.3).

## Hasil pembandingan naskah revisi dengan aplikasi

| Hal | Naskah revisi | Aplikasi sebelum catatan ini | Tindakan |
|---|---|---|---|
| Jumlah dan rincian data | 8.203 laporan; curat 6.223, curanmor 1.792, curas 188; per tahun laporan (Tabel 4.1); 5.119 berobjek kendaraan; 7.790 berkelurahan | sama persis (tahun laporan dihitung dalam WIB) | tidak ada |
| Rantai validasi | Gambar 4.3, Tabel 4.16, Lampiran I butir 7: analis → KBO → **Wakasatintelkam** → Kasatintelkam → Kapolres | empat pemeriksa, tanpa Wakasat | **ditambahkan** (migrasi 0031) |
| Muatan dan desain SOP | Tabel 4.17, Gambar 4.3, Lampiran I | tidak tampil di aplikasi | **halaman `/ops/sop`** |
| Model 2025 bulanan, 6 kelurahan | 190 dari 634, per bulan (Lampiran J.F) | sama | tidak ada |
| Model Jan–Ags 2026, 6 kelurahan | 86 dari 483 pada Lampiran J (C, G, K); 83 pada Tabel 4.6 dan Lampiran M | 83 | **belum** — lihat bawah |
| Model 4 / 8 kelurahan 2026 | 63 / 119 | 62 / 103 | **belum** |
| 2025 skenario tetap | 149 | 148 | **belum** |
| Modul 5: mutu draf dan waktu kerja | Tabel 4.17, Lampiran L (rubrik 0–2 × 4 unsur; cap waktu) | belum ada | **belum** |
| Ringkasan wilayah publik | Lampiran K.I: disetujui Humas | terbit otomatis | menunggu keputusan |

## Naskah revisi tidak seragam di dalam dirinya

Dua hal berikut berbeda antarbagian naskah, sehingga aplikasi tidak dapat sama dengan
semuanya sekaligus:

1. **Wakasatintelkam.** Bab IV (Gambar 4.3, Tabel 4.16, uraian desain) dan Lampiran I
   memuatnya. Lampiran K (A.6, D), Lampiran L (formulir), dan Lampiran M (panduan aplikasi:
   "lima tahap berjenjang", langkah D.7, rangkuman E.5) tidak. Aplikasi mengikuti Bab IV dan
   gambar desain SOP yang ditunjuk pemilik proyek; **Lampiran K, L, dan M perlu disesuaikan
   di naskah** (Lampiran M: "enam tahap", sisipkan Wakasat; tabel peran D.18 kini sembilan
   peran dan Administrator 65 kewenangan).
2. **Hasil model Januari–Agustus 2026.** Tabel 4.6 menulis "83 (17,81%)"; 83 dari 483 adalah
   17,18%, sedangkan 17,81% adalah 86 dari 483 — angka Lampiran J. Lampiran M menulis 273
   dari 1.117 (= 190 + 83).

## Tahap Wakasat — migrasi 0031

- Status `WAKASAT_CHECKED` dan tahap `WAKASAT`; `KBO_CHECKED` kini menunggu Wakasat.
- Peran **Wakasat Intelkam** (ROLE-09, level 2) dengan `monthly_product:examine`;
  Administrator ikut memegangnya (catatan 187). Katalog 65 permission, sembilan peran.
- `POST /monthly-products/{month}/wakasat` — ACCEPTED meneruskan ke Kasat, REJECTED
  mengembalikan ke analis dengan alasan; tercatat `REVIEW_MONTHLY_PRODUCT_WAKASAT`.
- Lonceng Wakasat memuat produk berstatus `KBO_CHECKED`.
- Web: enam langkah di atas naskah, tombol *Teruskan ke Wakasat Intelkam* (KBO) dan
  *Teruskan ke Kasat Intelkam* (Wakasat), kartu beranda "Menunggu pemeriksaan Wakasat".
- Akun peragaan `demo.wakasat` dibuat tanpa kata sandi sah; `scripts/sandi-peragaan-produksi.sh`
  kini menetapkan sembilan akun.
- Perubahan kontrak API: `next_stage` dapat bernilai `WAKASAT`; isian baru `awaiting_wakasat`.

## Halaman SOP — `/ops/sop`

Statis, mengutip naskah; `sop/content.ts` dikunci `sop.test.ts`. Tidak masuk menu (Lampiran M
mendaftar menu apa adanya); dibuka dari tautan di papan "Bulan ini".

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh; migrasi 0031 naik-turun;
web `tsc`, `biome`, `vitest` 434 lulus, `next build`; layar SOP dan enam langkah Produk Bulanan
diperiksa lewat potret pada salinan lokal.
