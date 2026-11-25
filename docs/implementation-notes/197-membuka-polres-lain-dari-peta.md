# 197 — Membuka Polres lain dari peta (25 November 2026)

**USER DECISION.** Pemilik proyek, 25 November 2026: "apakah saya bisa mengakses di peta agar
tetap bisa mengakses polres lain."

Sebelumnya, pada peta tingkat Polda hanya Jakarta Selatan yang dapat diklik; wilayah lain
menjawab sorotan dengan "di luar wilayah hukum". Sejak rekap per Polres masuk (catatan 196),
sistem memegang angka tahunan satuan lain, jadi wilayah itu kini punya tujuan.

| Tempat | Perilaku baru |
|---|---|
| Beranda dan halaman Peta, tingkat Polda | klik wilayah Polres lain → `/ops/polda?polres=<satuan>`; sorotan menyebut "Polres lain — klik untuk membuka rekapnya". Jakarta Selatan tetap menyelam ke kecamatan |
| Halaman Polda Metro | tiap Polres pada peta dan tiap nama pada tabel adalah tautan; panel **Rincian** menampilkan angka satuan terpilih per tahun |

- `MapCanvas` menerima `outsideLinks` (nama wilayah → alamat) — peta yang dapat diserialkan,
  bukan fungsi, karena komponennya berjalan di peramban.
- `lib/polda-area.ts` (tanpa impor) memegang padanan satuan ↔ wilayah peta; dipakai komponen
  klien dan server.
- Warna Beranda tidak berubah: tetap hanya Jakarta Selatan yang diwarnai (Lampiran M naskah).
- Pembatasan akses tetap di backend: akun tanpa `analytics:read` seluruh wilayah yang mengklik
  wilayah lain tiba pada keterangan "Tidak berwenang".

**Batas.** Untuk Polres lain yang ada hanyalah rekap per tahun. Kecamatan, kelurahan, jam, dan
titik kejadiannya tidak dapat diselami: datanya tidak ada pada sistem. Kabupaten Tangerang
tidak dapat diklik karena tidak tercantum sebagai satuan tersendiri pada rekap.

**Verifikasi.** Web `tsc`, `biome`, `vitest` (dua test baru padanan wilayah), `next build`;
pada salinan lokal: sepuluh wilayah lain menjadi tautan di Beranda dan di halaman Peta, klik
membuka panel Rincian, dan klik pada peta halaman Polda mengganti satuan terpilih.
