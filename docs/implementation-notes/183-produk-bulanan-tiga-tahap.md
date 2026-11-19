# 183 — Produk bulanan tiga tahap: Staf → Kasat → Pimpinan (17 November 2026)

Keputusan pemilik proyek 17 November 2026 (pilihan A), atas saran Kasat Intelkam — "rantai
aplikasi: Staf – Kasat – Pimpinan; staf/KBO sama saja" — dan sejalan dengan naskah Taskap
Bab IV (analis/KBO memeriksa, Kasat Intelkam menelaah sebagai pemilik proses, Kapolres
memutuskan). **Membalik keputusan 1B 10 November 2026** (catatan 177, dua tahap).

## Riwayat rantai

| Masa | Rantai |
|---|---|
| 6–10 November 2026 | Analis → KBO → Kasat → Pimpinan |
| 10–17 November 2026 | Analis → Pimpinan (KBO dan Kasat diklik orang yang sama berturut-turut) |
| sejak 17 November 2026 | **Staf Intelkam → Kasat Intelkam → Pimpinan** |

## Yang berubah

- **Peran.** `Analis Intelkam` (ROLE-03) berganti nama menjadi `Staf Intelkam`; haknya tetap.
  `Kasat Intelkam` (ROLE-02) dibuat lagi: hak baca seperti sebelumnya dan satu hak tindakan,
  `monthly_product:validate`. Enam peran.
- **Administrator** kehilangan `monthly_product:draft`. Selama ia dapat menyusun dan mengirim
  draf, rantainya dapat dilewati lewat akun admin. `ranking:manage` (membekukan peringkat)
  tetap padanya.
- **Alur status.** `DRAFT → ANALYST_REVIEWED → VALIDATED → DECIDED`. Status dan tahap `KASAT`
  sudah sah di skema sejak 0021 — tidak ada perubahan tabel. `KBO_CHECKED` (tinggalan)
  diperlakukan seperti `ANALYST_REVIEWED`.
- **Telaah Kasat** (`POST /monthly-products/{month}/kasat`): `ACCEPTED` meneruskan ke
  Pimpinan; `REJECTED` mengembalikan ke staf dan alasannya wajib. Kasat tidak mengubah isi
  usulan — yang menulis tetap staf, supaya jelas siapa menulis apa.
- **Pimpinan** hanya dapat menetapkan produk berstatus `VALIDATED`.
- **Akun peragaan.** `demo.kasat` kembali ke peran Kasat dengan status aktif; kata sandinya
  tidak disentuh migrasi (hash `!` dari 0023), jadi baru dapat dipakai setelah
  `scripts/sandi-peragaan-produksi.sh` dijalankan. Skrip itu kini mencakup enam akun.

## Mengapa kali ini tahap Kasat menambah kontrol

Tahap KBO/Kasat dihapus 10 November karena diklik orang yang sama. Yang berbeda sekarang:

1. tiga hak — `draft`, `validate`, `decide` — masing-masing dipegang tepat satu peran, dan
   itu dijaga test (`test_monthly_product_chain_is_held_by_three_different_roles`);
2. Administrator tidak lagi punya jalan pintas;
3. tahap KBO tidak dihidupkan — tidak ada dua tahap milik satu orang.

Yang TIDAK dapat dijamin kode: bila akun staf dan Kasat dipakai orang yang sama, masalah
10 November terulang. Itu urusan penugasan akun.

## Dampak pada produk yang sedang berjalan

Produk berstatus `ANALYST_REVIEWED` yang tadinya menunggu Pimpinan kini menunggu telaah Kasat.
Tidak ada baris yang diubah migrasi; produk yang sudah `DECIDED` tidak terpengaruh.

## TECHNICAL DECISION

- Telaah memakai dua formulir terpisah di layar (teruskan; kembalikan + alasan), supaya
  menekan Enter di kolom alasan tidak pernah meneruskan produk ke Pimpinan tanpa sengaja.
- Alasan pengembalian tampil di atas draf staf (`stages` terakhir = KASAT/REJECTED).
- Lencana sidebar tetap hanya untuk Pimpinan; antrean Kasat lewat lonceng dan kartu beranda.

## Verifikasi

- API: 789 lulus pada basis data berisi data contoh; migrasi 0026 naik-turun.
- Tes baru: rantai penuh termasuk pengembalian dan kirim ulang, 403 untuk setiap peran di
  luar gilirannya, produk tinggalan `KBO_CHECKED`, antrean Kasat, pemisahan tiga hak.
- Web: `tsc`, `biome`, `vitest` (430 lulus), `next build`.
