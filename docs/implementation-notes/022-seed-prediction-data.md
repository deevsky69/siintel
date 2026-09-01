# TASK 022 — SEED PREDICTION DATA

Tanggal: 2026-09-01
Status: **SELESAI — data dummy dibangkitkan ulang dan dimuat ke PostgreSQL 17.5.**

| Tabel | Jumlah |
|---|---:|
| `risk_scores` | 2.019 (1.848 asli + 171 pendamping baru) |
| `predictions` | 180 |
| `early_warnings` | 84 |
| `recommendations` | 84 |

---

## 1. PEMBANGKITAN ULANG DATA DUMMY — ATAS PERSETUJUAN PEMILIK PROYEK

Berbeda dari TASK 020–021 yang hanya memuat data, task ini **menulis ulang sebagian isi
`data/sample/*.csv`**. Pemilik proyek memilih opsi ini agar isi CSV dan isi database konsisten,
dan agar siapa pun yang membuka berkasnya melihat data yang benar. Versi lama tetap ada di
riwayat Git.

| Temuan audit | Sebelum | Sesudah |
|---|---|---|
| **A-3** faktor tidak menghasilkan `risk_score` | 1.822 dari 1.848 baris menyimpang | **0 dari 2.019** |
| **A-4** horizon prediksi | hanya `24h` | `6H/12H/24H/3D/7D`, masing-masing 36 |
| **A-5** penjelasan WHY | 1 kalimat identik untuk 180 prediksi | **180 penjelasan berbeda** |
| **A-6** prediksi tanpa pendamping risk score | 171 dari 180 | **0 dari 180** |

`risk_score` dan `risk_class` yang sudah ada **tidak diubah** — yang dibangkitkan ulang hanya
komponen penyusun dan metadatanya, sehingga sebaran risiko dataset tetap seperti aslinya.

---

## 2. BOBOT DAN THRESHOLD KINI TERBUKA, BUKAN TERSEMBUNYI

Agar faktor dapat dibuat konsisten, hubungan `risk_score = round(Σ(bobot × faktor))` memerlukan
bobot. Bobot itu belum ditetapkan (U-02), sehingga dibuat sebagai konfigurasi bertanda
**`DEMO / PROPOSED`** — sesuai izin eksplisit CLAUDE.md §11.

| Berkas | Isi | Status |
|---|---|---|
| `config/risk/risk-weights.yaml` | 5 bobot faktor, berjumlah 1 | `DEMO / PROPOSED` |
| `config/risk/warning-thresholds.yaml` | batas kelas risiko dan severity peringatan | `DEMO / PROPOSED` |

Nilai threshold-nya **bukan angka baru**: itu ambang yang selama ini sudah tertanam diam-diam
di dataset (warning terbit pada skor ≥70, kritis ≥85). Menuliskannya sebagai konfigurasi lebih
jujur daripada membiarkannya tersembunyi — ambang yang tidak tertulis tetap bekerja, tetapi
tidak dapat ditinjau maupun diubah.

Setiap baris menyimpan `weights_version`/`threshold_version`, sehingga angka lama tetap dapat
ditelusuri ke konfigurasi yang berlaku saat itu. Constraint database untuk hubungan ini tetap
**tidak dipasang** (docs/06 §3).

---

## 3. PENJELASAN (WHY) KINI BENAR-BENAR MENJELASKAN

Sebelumnya seluruh 180 prediksi memakai kalimat yang sama persis:
`"Historical hotspot; recent incidents; temporal pattern; nearby activity"`.

Sekarang WHY diturunkan dari faktor risiko pendamping prediksi itu sendiri:

```json
[{"factor": "historical_incident_density", "contribution": 0.312, "source": "RULE"},
 {"factor": "recent_incident_trend",       "contribution": 0.227, "source": "RULE"},
 {"factor": "time_window_pattern",         "contribution": 0.182, "source": "RULE"}]
```

`source` bernilai **`RULE`**, bukan `MODEL`. Angka ini dihasilkan aturan aritmetika, bukan temuan
model; menyebutnya `MODEL` akan menjadi penjelasan fiktif yang dilarang CLAUDE.md §27.
UI wajib menampilkan `source` ini.

---

## 4. DUA MASALAH YANG DITEMUKAN DAN DIPERBAIKI

**Pembangkitan sempat bergantung pada urutan baris.** Versi pertama memakai satu aliran acak
untuk seluruh berkas, sehingga menjalankan ulang di atas hasil sebelumnya menghasilkan angka
berbeda. Diperbaiki: setiap baris memakai seed turunan dari kodenya sendiri, sehingga hasilnya
murni bergantung pada isi baris. Terverifikasi: dijalankan dua kali menghasilkan berkas identik.

**Bug pada `downgrade()` migration 0007.** `op.drop_constraint("ck_locations_latitude_range", …)`
menghasilkan `ck_locations_ck_locations_latitude_range` — jebakan prefix ganda dari naming
convention, kali ini di sisi drop. Seluruh `alembic downgrade base` gagal karenanya.
Diperbaiki dengan memakai nama pendek. CI sebenarnya menguji reversibilitas migration, tetapi
belum sempat berjalan; masalahnya ketahuan saat mereset database lokal.

---

## 5. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
regenerate (dua kali berturut-turut) → berkas identik (deterministik)
alembic downgrade base / upgrade head → 7 turun, 7 naik
pnpm seed (database kosong)           → 13 tabel terisi, 3.981 baris
pnpm seed (dijalankan ulang)          → seluruh tabel +0 (idempoten)

Di database:
  forecast_horizon  6H/12H/24H/3D/7D → 36 masing-masing
  dominant_factors unik              → 180 dari 180
  prediksi dengan baseline risk score → 180 dari 180
  peringatan di bawah threshold      → 0

ruff check + format (53 berkas) → bersih
mypy (45 berkas)                → no issues
pytest tanpa DATABASE_URL       → 127 lulus, 51 dilewati
pytest dengan DATABASE_URL      → 178 lulus
```

---

## 6. TASK BERIKUTNYA

**TASK 023 — Seed Operational Data**: `commander_decisions`, `operational_actions`,
`prediction_actual`.

Tiga temuan audit menunggu di sana:

| Temuan | Acceptance |
|---|---|
| `decision_by` = `USER-DEMO-PIMPINAN` yang tidak ada di `users` (63/63 baris) | A-1 |
| 3 tindakan operasional untuk 33 keputusan `Approved` | A-8 |
| Evaluasi menyentuh prediksi `Draft`, dan tidak ada satu pun `FALSE_NEGATIVE` | A-7 |

Yang terakhir yang paling penting: tanpa baris `FALSE_NEGATIVE`, **recall tidak dapat dihitung**
dan klaim evaluasi model menjadi tidak sahih (CLAUDE.md §26).
