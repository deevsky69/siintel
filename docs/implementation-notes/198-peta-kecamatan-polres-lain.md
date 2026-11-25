# 198 — Peta kecamatan untuk Polres lain (25 November 2026)

**USER DECISION.** Pemilik proyek, 25 November 2026: "kalo dibuat seperti biasa ketika di klik
muncul peta lagi apakah bisa?" — yaitu mengklik Polres lain membuka peta di dalamnya, seperti
Jakarta Selatan membuka peta kecamatan.

## Yang dibangun

- `scripts/bangun-batas-kecamatan-polda.py` mengambil batas kecamatan (OSM `admin_level=6`)
  untuk sebelas kota/kabupaten lain, pada proyeksi yang sama dengan skrip induk; induk tiap
  kecamatan ditentukan dari geometri. Jawaban Overpass disimpan di
  `data/batas-osm/kecamatan-polda.json.gz`; keluarannya `wilayah-polda.generated.ts`.
- Panel **Rincian** pada `/ops/polda` menggambar peta kecamatan satuan terpilih: garis batas
  dan nama, di atas garis kota/kabupatennya.
- Berkas batas itu hanya diimpor halaman Polda, yang digambar di server — paket peramban peta
  utama tidak membesar.

## Batas, dinyatakan di layar

- **Hanya garis batas.** Rekap (catatan 196) memuat jumlah per Polres, bukan per kecamatan.
  Peta tidak diwarnai dan tidak dapat diselami: warna atau angka akan menyiratkan data yang
  tidak ada.
- **Kelengkapan mengikuti OpenStreetMap** (diambil 25 November 2026): Jakarta Barat 8, Jakarta
  Pusat 8, Jakarta Timur 10, Jakarta Utara 6, Kota Tangerang 13, Tangerang Selatan 7, Kabupaten
  Tangerang 29, Kepulauan Seribu 2 kecamatan. **Kota Depok 8 dari 11** (Cimanggis, Sukmajaya,
  Cilodong belum dipetakan sebagai relasi). **Kota Bekasi dan Kabupaten Bekasi: tidak ada**
  kecamatan yang dipetakan; layar menyatakannya dan tidak menggambar peta.
- Polres Pelabuhan Tanjung Priok dan Polresta Bandara Soekarno-Hatta tidak punya wilayah
  tersendiri pada peta.

Untuk peta kecamatan yang berangka bagi Polres lain diperlukan data per kejadian tiap Polres.

## Verifikasi

Web `tsc`, `biome`, `vitest` 441 lulus, `next build`; pada salinan lokal panel Rincian
diperiksa lewat potret untuk Jakarta Timur (lengkap), Depok (sebagian), dan Bekasi Kota
(keterangan tanpa peta).
