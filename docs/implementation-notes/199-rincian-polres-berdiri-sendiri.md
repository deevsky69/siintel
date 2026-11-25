# 199 — Satu wilayah diklik, hanya data wilayah itu yang tampil (25 November 2026)

**USER DECISION.** Pemilik proyek, 25 November 2026: "misal memang di klik wilayahnya ya yang
ditampilkan hanya data wilayahnya saja. jangan keseluruhan polres."

Sebelumnya `/ops/polda?polres=<satuan>` menyisipkan panel Rincian di antara ringkasan Polda dan
tabel seluruh Polres. Kini alamat itu menampilkan **hanya** satuan terpilih:

- judul = nama satuan; tautan **← Seluruh Polda Metro** kembali ke tampilan semua Polres;
- posisi data, kalimat ringkas (jumlah, porsi terhadap Polda, peringkat, perubahan), tabel per
  tahun, peta kecamatan (catatan 198), dan panel Dasar angka.

Porsi dan peringkat tetap disebut karena itu keterangan tentang satuan itu sendiri; angka
satuan lain tidak ditampilkan. `/ops/polda` tanpa parameter tidak berubah.

Sekaligus: toleransi penyederhanaan batas kecamatan diturunkan dari 60 m ke 25 m — pada 60 m
kecamatan kecil di Jakarta Pusat tampak saling tindih.

**Verifikasi.** Web `tsc`, `biome`, `vitest` 441 lulus, `next build`; pada salinan lokal
halaman Polres Metro Jakarta Pusat tidak memuat nama Polres lain maupun tabel Polda, dan
tautan kembali membuka tampilan seluruh Polres.
