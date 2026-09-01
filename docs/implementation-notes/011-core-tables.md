# TASK 011 — CORE TABLES

Tanggal: 2026-08-31 (dituntaskan 2026-09-01)
Status: **SELESAI — terverifikasi terhadap PostgreSQL 17.5 + PostGIS 3.5.2.**

Tabel yang diimplementasikan (`docs/08` TASK 011):
`locations`, `police_units`, `crime_incidents`, `intelligence_reports`, `patrol_activity`.

| Kriteria | Hasil |
|---|---|
| Model ORM sesuai `docs/02` §1–§5 | **Ya** |
| Migration tersedia (`0002`) | **Ya** |
| Constraint & index sesuai `docs/06` §3–§4 | **Ya** — diperiksa langsung di database (§4) |
| Migration cocok dengan model | **Ya** — diuji otomatis, termasuk uji mutasi |
| Migration dijalankan terhadap database hidup | **Ya** — termasuk siklus downgrade/upgrade |

---

## 1. VERIFIKASI TERHADAP DATABASE SUNGGUHAN

Akses Docker tersedia sejak 2026-09-01, sehingga acceptance TASK 010 dan 011 dituntaskan bersamaan.
Hasil pemeriksaan langsung pada `\d locations`:

```text
location_id | uuid                     | not null | gen_random_uuid()
geom        | geometry(Point,4326)     | not null |
grid_size_m | integer                  | not null |
created_at  | timestamp with time zone | not null | now()

Indexes:
  pk_locations           PRIMARY KEY, btree (location_id)
  ix_locations_geom      gist (geom)              ← index spasial, satu saja (tidak ganda)
  ix_locations_kecamatan btree (kecamatan)
  ix_locations_polsek    btree (polsek)
  uq_locations_code      UNIQUE CONSTRAINT
  uq_locations_grid_id   UNIQUE CONSTRAINT

Referenced by:
  crime_incidents      FOREIGN KEY (location_id) ... ON DELETE RESTRICT
  intelligence_reports FOREIGN KEY (location_id) ... ON DELETE RESTRICT
  patrol_activity      FOREIGN KEY (location_id) ... ON DELETE RESTRICT
```

Uji perilaku (dalam transaksi, di-rollback sehingga database tetap kosong):

| # | Uji | Hasil |
|---|---|---|
| 1 | `INSERT` tanpa primary key | `gen_random_uuid()` mengisi `location_id` |
| 2 | Geometri `ST_SetSRID(ST_MakePoint(...), 4326)` | tersimpan `POINT(106.855133 -6.230653)`, SRID 4326 |
| 3 | Join `crime_incidents → locations` | mengembalikan kecamatan/kelurahan lewat join (bukan kolom duplikat) |
| 4 | `DELETE` lokasi yang masih dirujuk | **ditolak** oleh `fk_crime_incidents_location ... RESTRICT` |
| 5 | `confidence = 150` | **ditolak** oleh `ck_intelligence_reports_confidence_range` |
| 6 | `INSERT` tanpa `geom` | **ditolak** oleh NOT NULL |
| 7 | `ST_DWithin` radius 100 m | menemukan lokasi, jarak 9,1 m |
| 8 | Setelah `ROLLBACK` | `locations` dan `crime_incidents` kembali 0 baris |

Butir 4–6 memang **diharapkan gagal**; kegagalannya justru bukti constraint bekerja.

---

## 2. YANG DIBUAT

```text
apps/api/src/prediksi_presisi_api/models/__init__.py            registrasi model
apps/api/src/prediksi_presisi_api/models/base.py                uuid_pk(), TimestampMixin
apps/api/src/prediksi_presisi_api/models/location.py            locations
apps/api/src/prediksi_presisi_api/models/police_unit.py         police_units
apps/api/src/prediksi_presisi_api/models/crime_incident.py      crime_incidents
apps/api/src/prediksi_presisi_api/models/intelligence_report.py intelligence_reports
apps/api/src/prediksi_presisi_api/models/patrol_activity.py     patrol_activity
database/migrations/versions/0002_core_tables.py                migration
apps/api/tests/test_core_tables.py                              11 test
```

`database/migrations/env.py` kini mengimpor paket `models` agar seluruh tabel terdaftar pada
`Base.metadata` saat Alembic membandingkan schema.

---

## 3. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | **Kolom taksonomi bertipe `String`, bukan ENUM database** (`incident_type`, `modus`, `target_type`, `location_type`, seluruh `status`, `function`) | Taksonomi final belum ditetapkan (U-16 / B-3). ENUM database akan memaksa migration `ALTER TYPE` setiap kali daftar nilai berubah. Validasi dilakukan di lapisan aplikasi terhadap `config/taxonomy/`. Keputusan ini **tidak mendahului** keputusan bisnis mana pun. |
| 2 | `occurred_at timestamptz` sebagai sumber kebenaran waktu kejadian, `incident_date`/`incident_time` dipertahankan | `docs/02` §3 meminta ketiganya; query rentang waktu memakai satu kolom, analisis jam rawan memakai kolom `time` |
| 3 | Tabel transaksi **tidak** menyimpan `kecamatan`/`kelurahan`/`polsek`/`grid_id` | `docs/02` K-8 dan CLAUDE.md §19 — diperoleh lewat join ke `locations`. Ada test yang menjaganya |
| 4 | `geom` dan `grid_size_m` dibuat `NOT NULL` | Mengikuti `docs/02` §1 yang menandainya wajib, meskipun besaran grid finalnya belum ditetapkan (U-04) |
| 5 | `Geometry(..., spatial_index=False)` + index GIST dideklarasikan eksplisit | GeoAlchemy2 membuat index spasial otomatis; membiarkannya aktif akan menghasilkan dua index yang sama |
| 6 | Seluruh FK `ON DELETE RESTRICT` | `docs/06` §3 — data operasional tidak dihapus, gunakan status |
| 7 | Geometri **poligon** belum ditambahkan pada `locations` | Menunggu keputusan ukuran grid & sumber batas wilayah (U-04 / B-4). CLAUDE.md §37 — jangan membangun yang belum dibutuhkan |
| 8 | `RUF002`/`RUF003` dimatikan di Ruff | Dokumentasi berbahasa Indonesia memakai tanda baca tipografis (en dash) di docstring/komentar. `RUF001` (kode/string) tetap aktif |

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
alembic history              → <base> -> 0001 -> 0002 (head)
alembic upgrade head --sql   → merender 5 CREATE TABLE, 13 CREATE INDEX (termasuk GIST),
                               4 FOREIGN KEY ... ON DELETE RESTRICT, 2 CHECK 0..100

ruff check (17 berkas)       → All checks passed
ruff format --check          → 17 berkas terformat
mypy (14 berkas)             → Success: no issues found
pytest                       → 20 test lulus (4 skeleton + 5 database + 11 tabel inti)
```

**Uji mutasi terhadap test drift.** Untuk memastikan test benar-benar dapat gagal, `grid_size_m`
sengaja diubah menjadi `nullable=True` **hanya pada migration**; hasilnya:

```text
FAILED tests/test_core_tables.py::test_migration_matches_model_columns[locations]
```

Perubahan itu langsung dikembalikan, lalu seluruh 20 test lulus kembali. Jadi
`test_migration_matches_model_columns` memang membandingkan nama kolom **dan** nullability antara
migration dan model, bukan sekadar lulus tanpa memeriksa apa pun.

Terhadap database sungguhan (§1): migration naik, turun, dan naik lagi dari kondisi kosong;
seluruh constraint dan index terbentuk sesuai desain.

**Integration test ditambahkan** (`apps/api/tests/test_integration_database.py`): 7 test yang
memeriksa revisi Alembic, ekstensi, tabel, kolom geometri, default UUID, FK RESTRICT, dan CHECK
terhadap database nyata. Test ini **dilewati otomatis** bila `DATABASE_URL` kosong, sehingga
`pytest` tetap hijau di mesin tanpa database:

```text
tanpa DATABASE_URL  → 20 lulus, 7 dilewati
dengan DATABASE_URL → 27 lulus
```

CI diperbarui: job `api` kini menjalankan service `postgis/postgis:17-3.5`, melakukan
`upgrade head`, menguji reversibilitas (`downgrade base` lalu `upgrade head`), lalu menjalankan
seluruh test termasuk integration test. Dengan begitu celah "migration tidak pernah menyentuh
database nyata" tidak dapat terulang tanpa ketahuan.

---

## 5. TASK BERIKUTNYA

**TASK 012 — Public Tables**: `citizen_reports`, `public_alerts`, `community_feedback`.

Catatan: keputusan **B-3 taksonomi** tidak memblokir TASK 012, tetapi menentukan isi
`config/taxonomy/` yang dibutuhkan saat seed (PHASE 3).
