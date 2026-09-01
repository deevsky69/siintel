# TASK 013 — INTELLIGENCE TABLES

Tanggal: 2026-09-01
Status: **SELESAI — terverifikasi terhadap PostgreSQL 17.5 + PostGIS 3.5.2.**

Tabel: `risk_scores`, `predictions`, `early_warnings`, `recommendations` (docs/02 §9–§12).
Sekaligus **melunasi** FK `public_alerts.warning_id → early_warnings` yang tertunda sejak TASK 012.

| Kriteria | Hasil |
|---|---|
| Model ORM sesuai `docs/02` §9–§12 | Ya |
| Migration `0005` | Ya |
| Migration dari kondisi kosong | Ya — 5 revisi berurutan, 17 tabel domain |
| FK tertunda dari TASK 012 | **Lunas** — `fk_public_alerts_warning_id` ada di database |
| Test | 116 lulus dengan database; 97 lulus + 14 dilewati tanpa database |

---

## 1. YANG SENGAJA TIDAK DIKUNCI

Ini bagian terpenting dari task ini. Tabel-tabel ini adalah tempat angka prediksi "terasa
ingin dikunci", dan justru di sinilah CLAUDE.md §11 dan §41 paling relevan.

| Hal | Status | Yang dilakukan |
|---|---|---|
| Bobot faktor risiko (U-02) | `NOT SPECIFIED` | Hubungan `risk_score = round(Σ(bobot × faktor))` **tidak** dijadikan CHECK. Yang disimpan hanya `weights_version` yang menunjuk `config/risk/` |
| Batas kelas `risk_class` (U-01) | `NOT SPECIFIED` | Kolom teks tanpa CHECK; tidak ada ambang yang tertanam di schema |
| Threshold `severity` early warning (U-01) | `NOT SPECIFIED` | Tidak ada CHECK; hanya `threshold_version` |
| Status `predictions`/`recommendations` (U-16) | `NOT SPECIFIED` | Teks tanpa CHECK, konsisten dengan tabel lain |
| `forecast_horizon` | **Requirement** (docs/01 §5.5) | Dikunci CHECK `6H/12H/24H/3D/7D` — ini memang ditetapkan spesifikasi, bukan asumsi |

Ada test yang **menjaga agar hal-hal ini tetap tidak terkunci**
(`test_risk_score_weight_relationship_is_not_locked`, `test_risk_class_thresholds_are_not_locked`,
`test_warning_severity_thresholds_are_not_locked`). Jadi bila suatu saat ada yang menambahkan
ambang diam-diam ke schema, test akan gagal.

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | `predictions.dominant_factors` **NOT NULL**, bertipe `jsonb` berisi `{factor, contribution, source}` | CLAUDE.md §10 dan §27: setiap prediksi harus menjelaskan WHY dari mekanisme yang benar-benar dipakai. `source ∈ {RULE, MODEL}` mencegah prototipe rule terbaca sebagai temuan model |
| 2 | `predictions.baseline_risk_score_id` nullable | Menegaskan `risk_scores` dan `predictions` adalah **dua layer**, bukan rantai wajib (docs/04). Berguna untuk penelusuran, bukan syarat |
| 3 | `early_warnings` menyimpan snapshot `severity`/`risk_score`/`threat_type`/`location_id` | Riwayat peringatan tidak boleh berubah ketika prediksi sumbernya diperbarui |
| 4 | CHECK `acknowledged_at` ⇒ `acknowledged_by`, dan sama untuk `resolved_*` | Status ACKNOWLEDGED/RESOLVED tanpa pelaku membuat audit trail bohong (CLAUDE.md §29) |
| 5 | `recommendations` **tidak** punya `unit_id`/`action_id`/`decision_id` | Rekomendasi adalah opsi, bukan perintah. Jalur ke tindakan wajib lewat `commander_decisions` (CLAUDE.md §13). Ada test yang menjaganya |
| 6 | UNIQUE `(location_id, threat_type, window_start, assessment_date)` pada `risk_scores` dan padanannya pada `predictions` | Mencegah duplikasi penilaian/prediksi untuk sel yang sama — `docs/06` §3 |
| 7 | Faktor risiko nullable dengan CHECK 0–100 masing-masing | Model baseline mungkin belum menghasilkan seluruh faktor; yang terisi tetap wajib berada di rentang sah |

---

## 3. PERLUASAN TEST DRIFT

Parser drift kini juga membaca `ALTER TABLE … ADD CONSTRAINT`, bukan hanya constraint di dalam
`CREATE TABLE`. Tanpa itu, FK yang dipasang belakangan (seperti utang `public_alerts.warning_id`)
tidak akan pernah terbandingkan dengan model — persis kasus yang muncul di task ini.

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
alembic downgrade base && alembic upgrade head → 0001 … 0005
alembic current                                → 0005 (head)
pg_tables (tabel domain)                       → 17
pg_constraint fk_public_alerts_warning_id      → ada (utang TASK 012 lunas)

ruff check + format (34 berkas) → bersih
mypy (28 berkas)                → no issues
pytest tanpa DATABASE_URL       → 97 lulus, 14 dilewati
pytest dengan DATABASE_URL      → 116 lulus
```

Integration test baru terhadap database nyata:

| Uji | Hasil |
|---|---|
| Rantai prediction → warning → recommendation → public alert | tersambung; satu join mengembalikan keempat `code` |
| `public_alerts.warning_id` menunjuk peringatan yang tidak ada | **ditolak** FK (dulu tidak tertahan) |
| `forecast_horizon = '48H'` | **ditolak** CHECK |
| Prediksi tanpa `dominant_factors` | **ditolak** NOT NULL |
| `acknowledged_at` diisi tanpa `acknowledged_by` | **ditolak** CHECK |

---

## 5. TASK BERIKUTNYA

**TASK 014 — Operational Tables**: `commander_decisions`, `operational_actions`, `prediction_actual`.

Poin penting yang sudah disiapkan sejak PHASE 0 dan harus benar-benar diwujudkan di sana:

1. `commander_decisions.modified_text` — menyimpan hasil modifikasi tanpa menimpa usulan asli,
   sehingga jejak "apa yang diusulkan AI" vs "apa yang diputuskan manusia" tetap utuh (U-07);
2. `operational_actions` hanya boleh lahir dari keputusan `APPROVED`/`MODIFIED`;
3. `prediction_actual.prediction_id` **nullable** + `match_type = FALSE_NEGATIVE` agar kejadian
   yang tidak diprediksi dapat direpresentasikan — syarat CLAUDE.md §26 supaya recall terhitung.

Setelah itu tersisa TASK 016 (constraint & index) untuk menutup PHASE 2.
