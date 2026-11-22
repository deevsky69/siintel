# 194 — Lampiran M naskah revisi 7: kartu "Bulan ini" dan lonceng (22 November 2026)

**USER DECISION.** Pemilik proyek, 22 November 2026: "update aplikasi persis seperti file
TASKAP REVISI 7 … nurut saja jangan ragu atau bimbang."

Lampiran M (Panduan Aplikasi) revisi 7 dibandingkan kalimat demi kalimat dengan aplikasi.
Aturan yang dipakai:

- **Hanya Lampiran M yang mengatur, batang tubuh diam → aplikasi mengikuti Lampiran M.**
- **Lampiran M bertentangan dengan batang tubuh naskah yang sama → aplikasi tetap pada
  batang tubuh**, karena mengubahnya hanya memindahkan ketidaksamaan ke bagian lain naskah.

## Diubah mengikuti Lampiran M

| Lampiran M | Sebelumnya | Sekarang |
|---|---|---|
| Beranda: "Tiga kartu Bulan ini" — Produk Bulanan, Evaluasi Cakupan, Persetujuan Warga | tiga sampai empat kartu (ada kartu Kegiatan di kelurahan prioritas) | tiga kartu; jumlah kegiatan dan tombol *Catat kegiatan* pindah ke kartu Produk |
| Lonceng: "Daftar terbagi tiga" — bantuan darurat, laporan warga, ulasan warga | juga memuat giliran produk bulanan dan buletin | tiga kelompok; `GET /notifications` tidak berubah, penyaringan di `bellFeed` |

## Dibiarkan karena naskah revisi 7 bertentangan dengan dirinya sendiri

| Lampiran M | Bagian lain naskah revisi 7 | Aplikasi |
|---|---|---|
| Rantai tanpa Wakasat; "lima tahap"; Gambar D.10 | Tabel 4.16, Gambar 4.3, Bab IV B (prosedur), Lampiran I butir 7: Wakasatintelkam memeriksa. Baris Lampiran I itu disunting pada revisi 7 (spasi dibetulkan), jadi memang dimaksud | enam tahap, ada Wakasat |
| Model 20 bulan "273 dari 1.117 (24,4%)" | Tabel 4.6 dan Lampiran J: 190 + 86 = 276 | 276 (24,71%) |
| Informasi Warga "empat panel" | Lampiran K: "Humas menyajikan ringkasan wilayah yang disetujui" | lima panel (ada persetujuan ringkasan wilayah) |
| "Enam peran"; Staf Intelkam | Lampiran M sendiri memakai KBO dan Humas sebagai pelaku; batang tubuh memakai analis, KBO, Wakasat | sembilan peran |
| Administrator 55 kewenangan | — (hanya Lampiran M) | 65: keputusan pemilik proyek 19 November 2026 yang tercatat di CLAUDE.md §15; angka 55 berasal dari katalog izin lama dan tidak dapat dicapai tanpa mencabut kewenangan yang diminta pemilik proyek |

## Verifikasi

Web `tsc`, `biome`, `vitest` (dua test baru: tiga kartu, tiga kelompok lonceng), `next build`;
Beranda dan lonceng diperiksa lewat potret pada salinan lokal. API tidak berubah.
