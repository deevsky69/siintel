# TASK 016 — DATABASE CONSTRAINTS & INDEX

Tanggal: 2026-09-01
Status: **SELESAI — PHASE 2 (DATABASE) TUNTAS.**

Karena constraint dan index sudah dipasang bersama tabelnya masing-masing sejak TASK 011,
task ini dikerjakan sebagai **peninjauan berbasis bukti** terhadap database nyata: menanyakan
`pg_constraint`/`pg_index` dan menguji perilaku, bukan menebak apa yang kurang.
Roadmap secara eksplisit melarang membuat index membabi buta.

| Kriteria | Hasil |
|---|---|
| FK lengkap sesuai `docs/06` §3 | Ya — 0 FK hilang |
| Unique & CHECK lengkap | Ya, ditambah 4 CHECK baru |
| Index sesuai `docs/06` §4 | Ya, ditambah 10 index FK |
| Tidak ada index redundan | Ya — pemeriksaan menemukan 0 (yang muncul milik PostGIS tiger) |
| Test | 135 lulus dengan database; 106 lulus + 29 dilewati tanpa database |

---

## 1. TIGA CELAH YANG DITEMUKAN

Semua ditemukan lewat pemeriksaan langsung, bukan dugaan.

### 1.1 Sepuluh kolom foreign key tanpa index

```sql
-- FK yang kolom pertamanya tidak punya index
SELECT c.conrelid::regclass, a.attname FROM pg_constraint c ... WHERE c.contype='f' ...
```

Hasil: 10 kolom, seluruhnya `RESTRICT` atau `CASCADE`.

```text
commander_decisions.decision_by        operational_actions.created_by
early_warnings.acknowledged_by         operational_actions.location_id
early_warnings.resolved_by             prediction_actual.actual_incident_id
predictions.baseline_risk_score_id     prediction_actual.actual_location_id
recommendations.warning_id             role_permissions.permission_id
```

PostgreSQL tidak membuat index otomatis untuk kolom FK. Tanpa index, setiap `DELETE` pada tabel
induk memicu sequential scan pada tabel anak untuk memeriksa `RESTRICT`/`CASCADE`.

**Aturan yang ditetapkan:** setiap kolom FK memiliki index, kecuali sudah menjadi kolom pertama
index lain. Bukan "index semua kolom" — hanya kolom FK, dengan alasan integritas yang jelas.

### 1.2 `updated_at` tidak pernah berubah di luar ORM

Diuji langsung:

```text
INSERT ... updated_at = 2020-01-01
UPDATE locations SET kecamatan = 'Tebet Baru'
→ sebelum perbaikan: updated_at tetap 2020-01-01
```

`onupdate` pada SQLAlchemy hanya berlaku untuk penulisan lewat ORM. Seed script, perbaikan data
manual, dan SQL langsung melewatinya — kolomnya berbohong. Diperbaiki dengan fungsi
`set_updated_at()` dan trigger pada 18 tabel yang memiliki kolom itu.

Setelah perbaikan: `updated_at` berubah menjadi waktu sekarang pada UPDATE lewat SQL biasa.

### 1.3 Koordinat mustahil diterima

```text
INSERT ... latitude = 999, longitude = -999   → sebelum perbaikan: DITERIMA
```

Ditambahkan CHECK rentang `latitude BETWEEN -90 AND 90` dan `longitude BETWEEN -180 AND 180`
pada `locations` dan `citizen_reports`. Batas ini bersifat universal, bukan batas wilayah Jakarta —
membatasi ke bounding box Jakarta akan berarti mengarang requirement (U-04 belum dijawab).

---

## 2. DUA ATURAN DIBUAT SELF-ENFORCING

Nilai terbesar task ini bukan index yang ditambahkan, melainkan dua test yang membuat aturannya
berlaku otomatis untuk tabel yang dibuat di kemudian hari:

| Test | Menjaga |
|---|---|
| `test_every_foreign_key_column_is_indexed` | Tabel baru yang lupa index FK langsung gagal |
| `test_every_table_with_updated_at_has_its_trigger` | Tabel baru yang lupa trigger `updated_at` langsung gagal |

Keduanya menanyakan katalog PostgreSQL, sehingga tidak perlu daftar manual yang harus dirawat.

---

## 3. YANG SENGAJA TIDAK DILAKUKAN

| Hal | Alasan |
|---|---|
| Index tambahan "untuk jaga-jaga" | Tidak ada query nyata yang membutuhkannya; roadmap TASK 016 melarangnya |
| Constraint bobot risiko dan threshold | Menunggu U-01/U-02 — lihat `docs/06` §3 "Constraint yang SENGAJA DITUNDA" |
| Batas koordinat khusus Jakarta Selatan | Akan mengarang requirement; cakupan wilayah masih U-04 |
| Partitioning / index khusus performa | Volume data nyata belum diketahui (U-17) |

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
alembic downgrade base && alembic upgrade head → 0001 … 0007
FK tanpa index                                  → 0 (sebelumnya 10)
trigger updated_at                              → 18 (satu per tabel yang punya kolomnya)
index redundan pada tabel proyek                → 0
UPDATE lewat SQL biasa                          → updated_at ikut berubah
latitude = 999                                  → ditolak ck_locations_latitude_range

ruff check + format (39 berkas) → bersih
mypy (31 berkas)                → no issues
pytest tanpa DATABASE_URL       → 106 lulus, 29 dilewati
pytest dengan DATABASE_URL      → 135 lulus
```

---

## 5. PHASE 2 SELESAI — RINGKASAN

| Task | Isi |
|---|---|
| 010 | PostgreSQL + PostGIS, Alembic, baseline ekstensi |
| 011 | 5 tabel inti |
| 012 | 3 tabel publik |
| 015 | 5 tabel administrasi (dinaikkan urutannya agar tidak ada FK tertunda) |
| 013 | 4 tabel intelijen + pelunasan FK `public_alerts.warning_id` |
| 014 | 3 tabel operasional + trigger invarian human-in-the-loop |
| 016 | Peninjauan constraint & index |

**20 tabel, 7 migration, 135 test.** Seluruhnya reproducible dari database kosong.

## 6. TASK BERIKUTNYA — PHASE 3 (SEED)

TASK 020–024 dengan 12 acceptance criteria kualitas data (`docs/08` PHASE 3).

Yang perlu diputuskan sebelum atau saat seed:

- **B-3 taksonomi final (U-16)** — nilai dummy berbahasa Indonesia (`Dilaporkan`, `Sedang`,
  `Aktif`) perlu dipetakan ke nilai tersimpan lewat `config/taxonomy/`. Bila belum ada
  keputusan resmi, pemetaan tetap dibuat dengan status `PROPOSED` dan mudah diubah.
- Bobot dan threshold (U-01/U-02) **belum** dibutuhkan untuk seed; yang diisi hanya
  `weights_version`/`threshold_version` bernilai `dummy-*`.
