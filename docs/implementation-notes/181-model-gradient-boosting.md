# 181 — Model gradient boosting, pembanding, PAI, dan uji tanda (17 November 2026)

Penyesuaian aplikasi ke naskah Taskap Bab III–IV (keputusan pemilik proyek 17 November 2026:
"menyesuaikan seperti Taskap", butir 1 dan 3 hasil audit naskah–aplikasi). Angka pada naskah
berstatus sementara dan mengikuti hasil aplikasi.

Menggantikan keputusan 2A (6 November 2026, catatan 176): "peta 3 bulan dulu, model menyusul
setelah diuji di dalam aplikasi". Modelnya kini ada dan diuji di dalam aplikasi.

## Yang berubah

| Bagian | Sebelum | Sesudah |
|---|---|---|
| Metode utama peringkat | Rata-rata 3 bulan (`HISTORY_3M`); `MODEL` ditolak 400 | `MODEL`: gradient boosting per kelurahan (`services/monthly_model.py`) |
| Pembanding | Peta 3 bulan, 12 bulan | + `HISTORY_1M` (bulan sebelumnya), `ANNUAL` (peta tahunan tetap, tahun = akhir masa latih) |
| Cakupan bawaan | `ALL_3C` | `VEHICLE` (kelompok berobjek kendaraan — yang diuji naskah) |
| "Model hanya bila lebih tepat" | Komentar YAML | `ranking.operational`: penjaga yang dijalankan kode |
| PAI | Selalu kosong | Dihitung; luas dari `config/ranking/kelurahan-area.yaml` |
| Uji tanda | Tidak ada | `GET /evaluation/monthly/backtest` |
| Alasan perkiraan | Angka dasar | + kontribusi tiap masukan, dari pohon model (CLAUDE.md §27) |
| Skema | — | 0024: CHECK `monthly_rankings.method` menerima `HISTORY_1M`, `ANNUAL` |

## Rancangan model — TECHNICAL DECISION

- **Satu baris** = satu kelurahan × satu bulan sasaran. **Masukan** (sepuluh): rata-rata
  bulanan 1, 3, 6, 12 bulan terakhir; tren (3 bulan terakhir dikurangi bulan-bulan
  sebelumnya); bulan kalender sasaran (sin, cos); rata-rata 1, 3, 12 bulan kelurahan lain
  sekecamatan. **Keluaran**: perkiraan jumlah kejadian bulan sasaran.
- **Batas informasi**: riwayat baris bulan T hanya memuat kejadian yang sudah dilaporkan
  sebelum T (klausa yang sama dengan `_known_by`); label dihitung dari yang sudah dilaporkan
  sampai `train_until`.
- **Masa latih**: `data_from` 2023-01-01 sampai `train_until` 2024-12-31; bulan sasaran latih
  April 2023 – Desember 2024 (sekurangnya 3 bulan riwayat) = 21 bulan × 65 kelurahan = 1.365
  baris. Riwayat dinyatakan sebagai rata-rata bulanan supaya jendela yang belum 12 bulan
  tetap sebanding.
- **Dibekukan**: parameter di `config/ranking/monthly.yaml`. Pelatihan deterministik
  (`random_state` tetap) dan dijalankan di dalam proses saat pertama dibutuhkan — tidak ada
  berkas model biner di repositori. `model_version` = `gbr-<versi>#<sidik data latih>`;
  sidik berubah bila data latih atau parameter berubah, sehingga perubahan itu terlihat pada
  peringkat yang dibekukan.
- **Pustaka**: scikit-learn `GradientBoostingRegressor` (dependensi baru API).
- **Kejadian sebelum 2023** (16 baris tercecer di ekstrak) diabaikan. Tanpa itu, awal data
  dianggap 2022 dan baris latih 2023 mendapat riwayat kosong — percobaan pertama dengan
  kekeliruan itu hanya mencakup 134 dari 634 kejadian.

## Pemilihan parameter

Empat set parameter dibandingkan pada **validasi di dalam masa latih**: model dilatih sampai
30 Juni 2024, dinilai pada Juli–Desember 2024 (268 kejadian berobjek kendaraan, enam
kelurahan per bulan). Peta 3 bulan pada masa yang sama: 57.

| n_estimators | learning_rate | max_depth | min_samples_leaf | Validasi (dari 268) |
|---|---|---|---|---|
| 200 | 0,05 | 3 | 5 | 57 |
| 100 | 0,05 | 2 | 10 | 57 |
| **300** | **0,03** | **2** | **20** | **60** |
| 60 | 0,10 | 2 | 20 | 56 |

Yang dipakai adalah set dengan validasi tertinggi.

**Keterbukaan.** Selama pengembangan, varian lain (sasaran log, masukan berupa pangsa
wilayah) juga sempat dilihat hasilnya pada masa uji 2025/2026. Rancangan yang dipakai adalah
yang diuraikan naskah (riwayat dan sasaran berupa jumlah kejadian), dan parameternya dipilih
menurut validasi di atas — tetapi masa uji itu tidak lagi sepenuhnya "belum pernah dilihat"
oleh perancang. Uji yang benar-benar bersih adalah bulan-bulan sesudah 17 November 2026.

## Hasil uji historis (data Pusiknas posisi 29 September 2026)

Enam kelurahan per bulan per metode; kejadian aktual = yang dapat dipetakan ke kelurahan.

**Kelompok berobjek kendaraan (`VEHICLE`)**

| Metode | 2025 (634) | PAI | Jan–Ags 2026 (483) | PAI |
|---|---|---|---|---|
| Model AI | **186 = 29,34%** | 3,17 | **88 = 18,22%** | 1,69 |
| Peta 3 bulan | 176 = 27,76% | 2,72 | 78 = 16,15% | 1,30 |
| Peta 12 bulan | 152 = 23,97% | 2,21 | 79 = 16,36% | 1,31 |
| Bulan sebelumnya | 151 = 23,82% | 2,25 | 73 = 15,11% | 1,18 |
| Peta tahun 2024 (tetap) | 115 = 18,14% | 2,97 | 75 = 15,53% | 2,54 |

Angka keempat pembanding sama persis dengan Tabel 12 naskah. Angka model pada naskah
(190 dan 86) perlu diganti dengan 186 dan 88.

Uji tanda satu arah, model terhadap pembanding, seluruh masa uji (20 bulan):

| Pembanding | Unggul–kalah–seri | p |
|---|---|---|
| Peta 3 bulan | 10–5–5 | 0,151 |
| Peta 12 bulan | 9–4–7 | 0,133 |
| Bulan sebelumnya | 16–3–1 | 0,002 |
| Peta tahun 2024 | 18–1–1 | < 0,001 |

**Pembacaan yang jujur:** model mencakup lebih banyak kejadian daripada setiap pembanding
pada kedua periode, tetapi keunggulannya atas dua pembanding terkuat (peta 3 bulan dan
12 bulan) BELUM bermakna menurut uji tanda (p > 0,05). Naskah tidak boleh menulisnya sebagai
keunggulan yang terbukti; yang dapat ditulis adalah "lebih tinggi pada kedua periode,
dievaluasi ulang setiap bulan".

Peta tahun 2024 ber-PAI tinggi karena enam kelurahan pilihannya berluas kecil — PAI
menghargai wilayah sempit, sehingga dibaca berdampingan dengan cakupan, bukan sendiri.

**Seluruh 3C (`ALL_3C`)** — 2025: model 259 dari 1.209, peta 3 bulan 253. Jan–Ags 2026:
model 140 dari 918, peta 12 bulan 162. Model TIDAK unggul pada 2026; penjaga mengembalikan
usulan ke peta historis untuk cakupan ini. Sejalan dengan naskah: hasil kelompok kendaraan
tidak digeneralisasi ke seluruh 3C.

## Penjaga (`ranking.operational`)

Untuk bulan sasaran M: model dan seluruh pembanding dinilai pada 12 bulan terakhir sebelum M
yang berada di luar masa latih, enam kelurahan, kejadian aktual sebagaimana diketahui sebelum
M. Model menjadi dasar usulan hanya bila cakupannya LEBIH TINGGI daripada pembanding terbaik;
bila bulan ujinya kurang dari tiga atau model tidak dapat dilatih, dipakai `guard.fallback`
(peta 3 bulan). Keputusan dan buktinya disimpan pada `monthly_products.facts`
(`method_reason`, `method_evidence`) dan tampil di layar Peringkat.

Ambang penjaga (12 bulan, minimal 3, "lebih tinggi" tanpa syarat kebermaknaan) berstatus
**PROPOSED** — itu aturan pemakaian model dalam operasi, jadi penetapan akhirnya milik
pemilik proses.

## PAI

`PAI = (kejadian tercakup / seluruh kejadian) / (luas kelurahan pilihan / luas seluruh
kelurahan)`. Luas dari `scripts/bangun-luas-kelurahan.py`: poligon peta (OpenStreetMap,
ODbL), total 145,73 km² — dekat dengan luas resmi Jakarta Selatan. Poligon sudah
disederhanakan, jadi luas per kelurahan adalah **perkiraan** (status PROPOSED); bila luas
resmi tersedia, berkasnya diganti.

## Yang TIDAK dikerjakan

- Rentang jam 4 jam, rantai Kasat Intelkam, rekomendasi per tempat kejadian, Modul 1 —
  butir audit lain, menunggu keputusan tersendiri.
- Bobot dan ambang IKW tetap PROPOSED.
- Uji kualitas draf rekomendasi oleh pengguna (naskah Tabel 15) — bukan pekerjaan kode.

## Verifikasi

- `uv run pytest`: 781 lulus pada basis data berisi data contoh (setara CI).
- `tests/test_monthly_model.py` (baru): batas informasi, pelatihan deterministik, model tidak
  melihat masa uji, kontribusi berjumlah sama dengan perkiraan, uji tanda, PAI, penjaga.
- Web: `tsc`, `biome`, `vitest` (423 lulus).
