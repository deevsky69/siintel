# 200 — Batas kecamatan Bekasi dan Depok dari geoBoundaries/HDX (25 November 2026)

**USER DECISION.** Pemilik proyek, 25 November 2026: "untuk beberapa polres seperti bekasi kota
ko ketika di klik gak muncul petanya. munculkan saja peta dan kecamatannya."

## Sebab kosong

OpenStreetMap tidak memuat relasi kecamatan (`admin_level=6`) untuk Kota Bekasi dan Kabupaten
Bekasi, dan hanya 8 dari 11 untuk Kota Depok (diperiksa lewat Overpass 25 November 2026).

## Sumber pengganti

geoBoundaries **gbHumanitarian**, Indonesia ADM3 (kecamatan), keluaran `9469f09` — dari OCHA
ROAP/HDX atas data Badan Pusat Statistik; lisensi **CC BY 3.0 IGO** (wajib atribusi, ditulis
di kaki peta).

- `scripts/ambil-batas-kecamatan-hdx.py` mengunduh berkas (26 MB, seluruh Indonesia),
  memeriksa SHA-256-nya, dan menyimpan hanya potongan tiga wilayah itu di
  `data/batas-osm/kecamatan-hdx.json.gz` (17 KB) supaya peta dapat dibangun ulang persis sama.
- `scripts/bangun-batas-kecamatan-polda.py` memakai potongan itu untuk SELURUH kecamatan
  ketiga wilayah (termasuk delapan kecamatan Depok yang ada di OSM), supaya garis
  antarkecamatan dalam satu kota tidak berasal dari dua pemetaan.
- Hasil: Kota Bekasi 12, Kabupaten Bekasi 23, Kota Depok 11 kecamatan — sesuai jumlah resmi.

**Batas.** Garis kota/kabupaten di bawahnya tetap dari OpenStreetMap, sehingga tepi luar
kecamatan tidak berimpit sempurna dengan garis kota (selisih beberapa puluh meter, terlihat
sebagai tepi ganda tipis). Ejaan nama mengikuti sumber ("Pondokgede", "Sukma Jaya").
Peta tetap hanya garis batas: angka per kecamatan untuk Polres lain tidak ada.

Tetap tanpa peta: Polres Pelabuhan Tanjung Priok dan Polresta Bandara Soekarno-Hatta — tidak
punya wilayah administratif tersendiri.

## Verifikasi

Web `tsc`, `biome`, `vitest` 441 lulus, `next build`; pada salinan lokal seluruh sebelas Polres
berwilayah menampilkan peta kecamatan (Bekasi Kota 12, Bekasi 23, Depok 11), dan dua Polres
tanpa wilayah menampilkan keterangan; Bekasi Kota dan Depok diperiksa lewat potret.
