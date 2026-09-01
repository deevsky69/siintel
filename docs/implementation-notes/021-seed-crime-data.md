# TASK 021 — SEED CRIME DATA

Tanggal: 2026-09-01
Status: **SELESAI — dimuat ke PostgreSQL 17.5 dan diverifikasi.**

| Tabel | Jumlah | Sumber |
|---|---:|---|
| `crime_incidents` | 1.200 | `data/sample/crime_incidents.csv` |
| `intelligence_reports` | 120 | `data/sample/intelligence_reports.csv` |
| `patrol_activity` | 180 | `data/sample/patrol_activity.csv` |

---

## 1. ACCEPTANCE CRITERIA YANG TERPENUHI

| Kriteria | Bukti |
|---|---|
| **A-2** — setiap `grid_id` terpetakan ke `location_id` | 1.500 baris dimuat tanpa satu pun grid tidak dikenal; `crime_incidents` dengan `location_id` NULL = 0 |
| **A-11** — waktu ternormalisasi ke `timestamptz` | `INC-00001` tercatat `13:51` WIB → `06:51 UTC`, dan kembali menjadi `13:51` saat ditampilkan dalam WIB |
| **A-12** — enum mengikuti `config/taxonomy/` | `status` tersimpan sebagai `REPORTED` / `PRELIMINARY_INVESTIGATION` / `INVESTIGATION` / `CLOSED`, dengan jumlah per nilai sama persis dengan data sumber berbahasa Indonesia |

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | `grid_id` tidak dikenal **menghentikan** seed, bukan dilewati | Melewati baris berarti data hilang diam-diam. Acceptance A-2 menuntut seluruh baris terpetakan |
| 2 | `occurred_at` (UTC) **dan** `incident_date`/`incident_time` (lokal) disimpan bersama | `occurred_at` untuk query rentang waktu, kolom lokal untuk analisis jam rawan (docs/02 §3) |
| 3 | `modus`, `target_type`, `location_type` dipertahankan apa adanya | Istilah lapangan (`kunci_t`, `congkel`, `pecah_kaca`), bukan taksonomi berjenjang yang perlu dipetakan |
| 4 | `patrol_activity.unit_id` dipetakan lewat `police_units.code` | CSV memuat kode unit, bukan UUID |

---

## 3. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
pnpm seed:crime
  crime_incidents      +1200
  intelligence_reports +120
  patrol_activity      +180

pnpm seed  (seluruh kelompok, dijalankan ulang)
  seluruh tabel +0 — idempoten

INC-00001: 2023-07-09 13:51 WIB → occurred_at 2023-07-09 06:51+00
crime_incidents tanpa location_id → 0
sebaran per kecamatan: Kebayoran Baru 188, Pasar Minggu 160, Tebet 159, Cilandak 139

ruff check + format (49 berkas) → bersih
mypy (42 berkas)                → no issues
pytest tanpa DATABASE_URL       → 118 lulus, 45 dilewati
pytest dengan DATABASE_URL      → 163 lulus
```

Test baru menjaga: grid tidak dikenal menghentikan seed, konversi WIB→UTC, seluruh kejadian
punya lokasi, status tersimpan dalam bentuk enum Inggris, istilah lapangan tidak ikut diterjemahkan,
seed idempoten, dan jumlah baris berkas sumber tidak berubah diam-diam.

---

## 4. TASK BERIKUTNYA — DAN SATU HAL YANG PERLU PERSETUJUAN

**TASK 022 — Seed Prediction Data**: `risk_scores` (1.848), `predictions` (180),
`early_warnings` (84), `recommendations` (84).

Berbeda dari TASK 020–021 yang hanya **memuat** data, TASK 022 menyentuh temuan audit yang
menuntut **perubahan isi data dummy**:

| Temuan | Acceptance |
|---|---|
| Jumlah 5 faktor ≠ `risk_score` pada 1.822 dari 1.848 baris | A-3 |
| `forecast_horizon` hanya `24h`, padahal spesifikasi menuntut 6H–7D | A-4 |
| `dominant_factors` identik untuk 180 dari 180 prediksi | A-5 |
| Prediksi tanpa `risk_scores` pendamping (171 dari 180) | A-6 |

Keempatnya **tidak dapat diselesaikan dengan pemetaan saat impor** — datanya memang perlu
dibangkitkan ulang secara deterministik, yang berarti **menulis ulang sebagian isi
`data/sample/*.csv`**.

Berkas itu berasal dari pemilik proyek, sehingga perubahannya perlu persetujuan lebih dulu.
Versi lama tetap tersimpan di riwayat Git.
