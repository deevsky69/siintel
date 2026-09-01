# TASK 014 — OPERATIONAL TABLES

Tanggal: 2026-09-01
Status: **SELESAI — terverifikasi terhadap PostgreSQL 17.5 + PostGIS 3.5.2.**

Tabel: `commander_decisions`, `operational_actions`, `prediction_actual` (docs/02 §13–§15).
Seluruh 20 tabel kanonik CLAUDE.md §20 kini ada di database.

| Kriteria | Hasil |
|---|---|
| Model ORM sesuai `docs/02` §13–§15 | Ya |
| Migration `0006` | Ya |
| Migration dari kondisi kosong | Ya — 6 revisi berurutan |
| Test | 131 lulus dengan database; 106 lulus + 25 dilewati tanpa database |

---

## 1. INVARIAN HUMAN-IN-THE-LOOP DITEGAKKAN DI DATABASE

Ini perubahan paling penting pada task ini, sekaligus penyimpangan yang disengaja dari
rencana sebelumnya di `docs/06`.

**Rencana semula:** aturan "tindakan hanya boleh lahir dari keputusan `APPROVED`/`MODIFIED`"
ditegakkan di service layer.

**Yang dilakukan:** ditegakkan di database lewat trigger
`trg_operational_actions_require_approved_decision`.

**Alasan:** ini invarian inti produk — jaminan bahwa AI tidak pernah langsung memerintahkan
tindakan operasional (CLAUDE.md §13). Aturan sepenting itu tidak boleh bergantung pada satu
jalur kode: script seed, perbaikan data manual, atau endpoint yang ditulis belakangan bisa
melewatinya. CHECK constraint tidak bisa dipakai karena tidak boleh merujuk tabel lain,
sehingga trigger adalah satu-satunya cara deklaratif di PostgreSQL.

Ini **pengecualian yang disengaja**, bukan pola umum. Aturan bisnis lain tetap di service layer.
`docs/06` §3 sudah diperbarui.

### Uji mutasi terhadap trigger

Untuk memastikan test-nya benar-benar menangkap dan bukan lolos karena sebab lain, trigger
sengaja dilepas dari database lalu test dijalankan:

```text
DROP TRIGGER trg_operational_actions_require_approved_decision ON operational_actions;

FAILED tests/test_integration_database.py::test_action_cannot_be_created_from_a_rejected_decision
       - Failed: DID NOT RAISE DatabaseError
```

Trigger dikembalikan lewat `alembic downgrade base && alembic upgrade head`, lalu seluruh
131 test lulus kembali.

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | `commander_decisions.modified_text` terpisah dari `recommendations.recommendation_text` | U-07. Usulan asli sistem **tidak ditimpa**, sehingga jejak "apa yang diusulkan AI" dan "apa yang diputuskan manusia" keduanya utuh dan dapat diaudit. Ada integration test yang membuktikan keduanya tetap terbaca |
| 2 | CHECK `decision = 'MODIFIED'` ⇒ `modified_text IS NOT NULL` | Modifikasi tanpa isi baru tidak bermakna dan membuat jejak keputusan tidak lengkap |
| 3 | CHECK pada `decision`, `match_type` | Nilai-nilai ini **menentukan perilaku sistem** (boleh-tidaknya tindakan lahir; cara precision/recall dihitung) dan sudah ditetapkan CLAUDE.md §13 dan §26 — berbeda dari taksonomi domain yang masih menunggu penelitian |
| 4 | `decision_by` **NOT NULL** | Keputusan operasional selalu punya pejabat yang bertanggung jawab |
| 5 | `prediction_actual.prediction_id` nullable + CHECK konsistensi `match_type` | Kejadian yang tidak diprediksi harus dapat direpresentasikan, jika tidak recall mustahil dihitung (CLAUDE.md §26) |
| 6 | `operational_actions.created_by` nullable | Sebagian penugasan pada dataset dummy tidak memuat pembuatnya; tetap dapat diisi bila diketahui |

### Aturan penggunaan CHECK yang dipakai konsisten sejak TASK 011

- **Dikunci CHECK** bila daftar nilainya menentukan perilaku sistem dan sudah ditetapkan
  spesifikasi: `forecast_horizon`, `decision`, `match_type`, `audit_logs.result`,
  `role_permissions.scope`.
- **Tidak dikunci** bila merupakan taksonomi domain yang masih menunggu penelitian/SOP:
  `incident_type`, `modus`, `target_type`, `location_type`, `severity`, `risk_class`,
  dan seluruh kolom `status`.

---

## 3. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
alembic downgrade base && alembic upgrade head → 0001 … 0006
pg_tables (tabel domain)                       → 20 (lengkap sesuai CLAUDE.md §20)
pg_trigger                                     → trg_operational_actions_require_approved_decision

ruff check + format (38 berkas) → bersih
mypy (31 berkas)                → no issues
pytest tanpa DATABASE_URL       → 106 lulus, 25 dilewati
pytest dengan DATABASE_URL      → 131 lulus
```

Integration test baru terhadap database nyata:

| Uji | Hasil |
|---|---|
| Tindakan dari keputusan `APPROVED` | diterima |
| Tindakan dari keputusan `REJECTED` | **ditolak trigger** |
| Keputusan `MODIFIED` tanpa `modified_text` | **ditolak** CHECK |
| Setelah keputusan `MODIFIED` | usulan asli **dan** teks hasil modifikasi keduanya masih terbaca |
| `FALSE_NEGATIVE` tanpa `prediction_id` | diterima — recall dapat dihitung |
| `HIT` tanpa `prediction_id` | **ditolak** CHECK |

---

## 4. STATUS PHASE 2

| Task | Status |
|---|---|
| 010 PostgreSQL/PostGIS + Alembic | Selesai |
| 011 Tabel inti | Selesai |
| 012 Tabel publik | Selesai |
| 015 Tabel administrasi | Selesai |
| 013 Tabel intelijen | Selesai |
| 014 Tabel operasional | Selesai |
| 016 Constraint & index | **Berikutnya** |

Sebagian besar constraint dan index sudah dipasang bersama tabelnya masing-masing, sehingga
TASK 016 menjadi tugas **peninjauan**: memeriksa `docs/06` §3–§4 satu per satu terhadap
database nyata, menambahkan yang terlewat, dan memastikan tidak ada index yang dibuat
tanpa alasan.

## 5. TASK BERIKUTNYA

**TASK 016 — Database Constraints & Index**, lalu PHASE 3 (seed) dengan 12 acceptance criteria
kualitas data yang sudah tertulis di `docs/08`.

Menjelang seed, keputusan **B-3 (taksonomi final)** mulai relevan: nilai enum dalam dataset
dummy berbahasa Indonesia perlu dipetakan ke nilai tersimpan lewat `config/taxonomy/`.
