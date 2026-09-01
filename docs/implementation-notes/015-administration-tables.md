# TASK 015 — ADMINISTRATION TABLES

Tanggal: 2026-09-01
Status: **SELESAI — terverifikasi terhadap PostgreSQL 17.5 + PostGIS 3.5.2.**

Tabel: `roles`, `users`, `permissions`, `role_permissions`, `audit_logs` (docs/02 §16–§20).

| Kriteria | Hasil |
|---|---|
| Model ORM sesuai `docs/02` §16–§20 | Ya |
| Migration `0004` | Ya |
| Migration dari kondisi kosong | Ya — `downgrade base` → `upgrade head` (4 revisi) |
| Constraint terbentuk di database | Ya — diperiksa lewat `pg_constraint` |
| Test | 86 lulus dengan database; 72 lulus + 10 dilewati tanpa database |

---

## 1. PERUBAHAN URUTAN TASK (disetujui pemilik proyek)

TASK 015 dikerjakan **sebelum** 013 dan 014. Nomor task tidak berubah; `docs/08` PHASE 2 diperbarui.

Alasan konkret: tanpa `users`, empat foreign key harus ditunda —
`early_warnings.acknowledged_by`, `early_warnings.resolved_by` (013),
`commander_decisions.decision_by`, `operational_actions.created_by` (014).
Pola penundaan itu sudah terlanjur terjadi sekali (`public_alerts.warning_id`) dan menambah
utang teknis yang harus ditagih lewat migration susulan. Dengan urutan baru, tidak ada FK tertunda
selain satu yang sudah ada dan akan lunas di TASK 013.

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | `role_permissions` membawa kolom `scope` (`ALL`/`OWN_JURISDICTION`/`OWN_FUNCTION`) dengan CHECK | Mewujudkan simbol `L` pada matriks `docs/03`, ditegakkan backend — bukan sekadar menyembunyikan tombol (CLAUDE.md §15) |
| 2 | `users.polsek` dan `users.function` | Tanpa keduanya `scope` tidak dapat dievaluasi |
| 3 | FK `role_permissions` memakai `ON DELETE CASCADE` | Mencabut role/permission tidak boleh meninggalkan pemberian yang menggantung. Tabel lain tetap `RESTRICT` (docs/06 §3) |
| 4 | `audit_logs.result` memakai CHECK `SUCCESS`/`DENIED`/`FAILED` | Nilai teknis yang ditetapkan sistem, bukan taksonomi bisnis, sehingga aman dikunci. `DENIED` wajib ada — tanpanya penolakan otorisasi tidak terekam |
| 5 | `audit_logs` **tanpa** `updated_at`, dan tanpa endpoint tulis di `docs/05` | Audit bersifat append-only (CLAUDE.md §29). Ada test yang menjaganya |
| 6 | `audit_logs.user_id` nullable | Peristiwa sistem (mis. import terjadwal) tidak dipicu pengguna |
| 7 | `audit_logs.resource_id` bertipe teks | Menyimpan UUID maupun `code` (dataset dummy memakai `REC-0062` dan sejenisnya) |
| 8 | `roles.level` `smallint` dengan CHECK 1–6 | `docs/06` §3; dataset dummy menyimpan teks `"Level 1"` yang dinormalkan saat seed |
| 9 | `users.status` **tanpa** CHECK | Taksonomi status masih menunggu keputusan B-3, konsisten dengan tabel lain |
| 10 | `password_hash` NOT NULL | Akun seed dibuat dengan hash yang dihasilkan saat seed; password mentah tidak pernah masuk dataset |

---

## 3. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
alembic downgrade base && alembic upgrade head → 0001, 0002, 0003, 0004
alembic current                                → 0004 (head)
pg_tables                                      → 13 tabel domain

pg_constraint (users, role_permissions, audit_logs):
  ck_audit_logs_result_allowed        pk_audit_logs
  ck_role_permissions_scope_allowed   pk_role_permissions
  fk_audit_logs_user_id               pk_users
  fk_role_permissions_permission_id   uq_audit_logs_code
  fk_role_permissions_role_id         uq_users_code
  fk_users_role_id                    uq_users_username

ruff check + format (28 berkas) → bersih
mypy (23 berkas)                → no issues
pytest tanpa DATABASE_URL       → 72 lulus, 10 dilewati
pytest dengan DATABASE_URL      → 86 lulus
```

Integration test baru terhadap database nyata:

| Uji | Hasil |
|---|---|
| Menghapus role yang punya pemberian permission | pemberiannya ikut terhapus (CASCADE), tidak menggantung |
| `scope = 'SEMUA_WILAYAH'` | **ditolak** CHECK |
| Audit dengan `result = 'DENIED'` | diterima |
| Audit dengan `result = 'BERHASIL'` | **ditolak** CHECK |
| Audit peristiwa sistem tanpa `user_id` | diterima, `user_id` NULL |

---

## 4. YANG BELUM DIKERJAKAN DI SINI

- **Isi** role/permission belum di-seed; katalog `docs/03` §2 baru diterapkan pada TASK 020/024.
- Matriks pemberian permission per role masih `PROPOSED` sampai pertanyaan P-1…P-7 (`docs/03` §4) dijawab.
- Hashing dan verifikasi password (Argon2id) dibuat pada TASK 050.

## 5. TASK BERIKUTNYA

**TASK 013 — Intelligence Tables**: `risk_scores`, `predictions`, `early_warnings`, `recommendations`,
sekaligus melunasi FK `public_alerts.warning_id → early_warnings`.

Bobot dan threshold tetap **tidak** dikunci (U-01, U-02); yang disimpan hanya
`weights_version`/`threshold_version` yang menunjuk konfigurasi di `config/risk/`.
