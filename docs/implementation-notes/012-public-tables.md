# TASK 012 — PUBLIC TABLES

Tanggal: 2026-09-01
Status: **SELESAI — terverifikasi terhadap PostgreSQL 17.5 + PostGIS 3.5.2.**

Tabel: `citizen_reports`, `public_alerts`, `community_feedback` (docs/02 §6–§8).

| Kriteria | Hasil |
|---|---|
| Model ORM sesuai `docs/02` §6–§8 | Ya |
| Migration `0003` | Ya |
| Migration dijalankan dari kondisi kosong | Ya — `downgrade base` → `upgrade head` sampai `0003` |
| Constraint & index terbentuk di database | Ya — diperiksa lewat `pg_constraint` |
| Test | 56 lulus dengan database; 46 lulus + 10 dilewati tanpa database |

---

## 1. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | `citizen_reports.location_id` **nullable**, `geom`/`latitude`/`longitude` **NOT NULL** | Laporan masyarakat masuk dengan koordinat bebas dan baru dipetakan ke grid setelah geo-processing (docs/02 §6). Jadi koordinat selalu ada, pemetaan grid belum tentu |
| 2 | `citizen_reports.incident_time` bertipe `timestamptz` dan **nullable** | Pada dataset dummy nilainya berupa tanggal+jam penuh, bukan jam saja; pelapor juga bisa tidak mengetahui waktu kejadian |
| 3 | `public_alerts` **tidak** punya `location_id`/`grid_id`; memakai `area_text` | docs/02 §7 dan CLAUDE.md §24 — alert publik tidak boleh membocorkan grid internal. Ada test yang menjaganya |
| 4 | `public_alerts.warning_id` dibuat **tanpa FK** untuk sementara | Tabel `early_warnings` baru ada pada TASK 013; FK dipasang di migration TASK 013. Melompat ke TASK 013 hanya demi FK melanggar CLAUDE.md §7 |
| 5 | CHECK `window_end > window_start` pada `public_alerts` | Mengikuti aturan umum jendela waktu `docs/06` §3 |
| 6 | `community_feedback.report_id` **NOT NULL** + FK RESTRICT | Umpan balik selalu melekat pada satu laporan (docs/02 §8) |
| 7 | Identitas pelapor dan lampiran bukti **tidak** dibuat | U-13 masih `REQUIRES HUMAN / POLICY APPROVAL`; CLAUDE.md §16 meminta data pribadi diminimalkan |

---

## 2. NAMING CONVENTION CONSTRAINT (perbaikan lintas task)

Test drift yang diperluas menemukan masalah nyata: **model tidak memberi nama** pada PK/UNIQUE/FK
(hanya `primary_key=True`, `unique=True`), sementara migration menamainya manual. Akibatnya nama di
model dan di migration bisa berbeda tanpa ketahuan, dan `alembic revision --autogenerate` nanti akan
menghasilkan nama yang tidak konsisten.

Perbaikan: naming convention dipasang pada `Base.metadata` (`docs/06` §1.2), lalu nama constraint
pada migration `0002`/`0003` diselaraskan:

- FK: `fk_<tabel>_<kolom>` (mis. `fk_crime_incidents_location` → `fk_crime_incidents_location_id`);
- CHECK: ditulis dengan **nama pendek** (`confidence_range`) di model **dan** migration, karena
  konvensi `ck_%(table_name)s_%(constraint_name)s` yang menyusun prefiksnya. Menulis nama lengkap
  menghasilkan prefix ganda — sempat terjadi dan langsung tertangkap test
  (`ck_public_alerts_ck_public_alerts_window_order`).

Migration `0002` disunting, bukan ditambah migration perbaikan, karena belum pernah dipakai di
lingkungan mana pun selain database pengembangan yang isinya kosong. Setelah perubahan,
seluruh rangkaian dijalankan ulang dari nol dan nama constraint di database diperiksa langsung.

---

## 3. PERLUASAN TEST DRIFT

`tests/test_migration_drift.py` menggantikan test drift lama yang hanya membandingkan kolom.
Sekarang membandingkan, untuk **seluruh** tabel:

1. nama kolom;
2. nullability;
3. nama constraint (PK, UNIQUE, FK, CHECK);
4. nama index.

Perluasan ini dipicu kejadian nyata: sebuah CHECK sempat ditulis di migration tetapi belum di model,
dan versi test lama tidak menangkapnya.

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
alembic downgrade base && alembic upgrade head → 0001, 0002, 0003
alembic current                                → 0003 (head)
pg_tables                                      → 8 tabel domain + alembic_version + spatial_ref_sys

pg_constraint untuk tabel publik:
  ck_citizen_reports_urgency_score_range        pk_citizen_reports
  ck_citizen_reports_verification_score_range   pk_community_feedback
  ck_public_alerts_window_order                 pk_public_alerts
  fk_citizen_reports_location_id                uq_citizen_reports_code
  fk_community_feedback_report_id               uq_community_feedback_code
                                                uq_public_alerts_code

ruff check + format (24 berkas)  → bersih
mypy (20 berkas)                 → no issues
pytest tanpa DATABASE_URL        → 46 lulus, 10 dilewati
pytest dengan DATABASE_URL       → 56 lulus
```

Integration test baru terhadap database nyata:

| Uji | Hasil |
|---|---|
| Laporan masyarakat dibuat tanpa `location_id` | berhasil, `location_id` tetap NULL |
| `community_feedback` menunjuk laporan yang tidak ada | **ditolak** FK |
| `public_alerts` dengan `window_end` < `window_start` | **ditolak** CHECK |

---

## 5. TASK BERIKUTNYA

**TASK 013 — Intelligence Tables**: `risk_scores`, `predictions`, `early_warnings`, `recommendations`.

Yang harus diselesaikan di migration TASK 013:

1. memasang FK `public_alerts.warning_id → early_warnings` (utang dari task ini);
2. `predictions.baseline_risk_score_id` nullable → `risk_scores` (docs/02 §10);
3. kolom `weights_version` dan `threshold_version` untuk menelusuri konfigurasi yang dipakai.

Nilai bobot dan threshold tetap **tidak** dikunci (U-01, U-02).
