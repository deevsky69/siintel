# 179 — Menu /ops diringkas 20 → 14 submenu; peta dan lonceng mengikuti siklus bulanan (12 November 2026)

> Keputusan pemilik proyek **A** atas analisis keringkasan /ops (10 November 2026): seluruh
> usulan diterapkan. Tidak ada perubahan basis data maupun kontrak API selain isi
> `GET /notifications`.

## Temuan yang ditindaklanjuti

| # | Temuan | Tindakan |
|---|---|---|
| 1 | 20 submenu; Administrator melihat semuanya | 14 submenu (`navigation.ts`); test `NAV_ITEMS` 14 |
| 2 | Wilayah: Peta, Wilayah Rawan, Pola, Analitik tumpang tindih; dua masih rantai harian | Wilayah Rawan keluar (isinya = Peringkat); Pola jadi **tab** di Analitik (`ScreenTabs`) |
| 3 | Peringkat ganda dengan Produk Bulanan sejak pembekuan otomatis | Peringkat jadi tab di Produk Bulanan |
| 4 | Data: triase ganda, Input Data dan Pembakuan berdiri sendiri | Input Data (`+ Catat kejadian`) dan Pembakuan jadi tab di Laporan Petugas, disaring permission `crime:write` / `crime:triage` |
| 5 | Pengaturan Sistem hanya membaca bobot skor harian | keluar dari menu; alamat tetap |
| 6 | Lonceng masih rantai harian | `GET /notifications`: kelompok `WARNING`, `DECISION`, `PREDICTION`, `OPERATION`, `PATROL_PLAN` dihapus; ditambah `MONTHLY_PRODUCT` (Pimpinan: menunggu penetapan — status `AWAITING_DECISION`; Analis/Administrator: draf belum dikirim) dan `BULLETIN` (`bulletin:approve`, buletin `DRAFT`) |
| 7 | Peta dan beranda memakai lapisan risiko harian | `toMapLayer` bawaan **historis**; `mapHref` menulis `layer=` hanya bila bukan historis; pemilih lapisan di `/ops/peta` hanya Historis (+ lapisan harian bila sedang dibuka lewat alamat lama); **kelurahan prioritas bulan ini** (`lib/monthly-products.getPriorityKelurahan`: produk DECIDED terakhir) digarisi emas pada kanvas (`MapCanvas.priority`) dan ditampilkan sebagai panel tautan di atas peta; beranda meneruskan prioritas yang sama ke `MapHero` |

## Pilihan teknis

- `components/shell/screen-tabs.tsx`: tab server-side, aktif menurut rute, disaring
  permission — kenyamanan, bukan otorisasi (backend tetap memeriksa).
- `groupOf` kini mengembalikan **id kelompok** dan mengenali layar di luar menu
  (`OFF_MENU_GROUP`) supaya kelompok sidebar tetap terbuka saat tab dibuka.
- `screens.test.tsx`: daftar `keptOffMenu` bertambah `input`, `pembakuan`, `pengaturan`,
  `peringkat`, `pola`, `wilayah` — daftar tertutup, layar baru di luar menu tetap tertangkap.
- Lapisan `current`/`predictive` dan endpoint `/map/current-risk`, `/map/predictive-heatmap`
  tidak dihapus: tautan lama (`?layer=current`) tetap bekerja dan evaluasi mundur tetap
  membacanya.
- Komponen rantai harian (peringatan, rekomendasi, operasi, brief) tidak disentuh.

## Verifikasi

- Web: `tsc --noEmit`, `biome check`, `vitest run` (420), `next build` — lulus.
- API: `ruff`, `pytest` notifikasi (11), produk bulanan, buletin — lulus.
