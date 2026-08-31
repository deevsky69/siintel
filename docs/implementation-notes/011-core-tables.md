# TASK 011 — CORE TABLES

Tanggal: 2026-08-31
Status: **SELESAI SEBAGIAN — migration belum dijalankan terhadap database sungguhan (akses Docker).**

Tabel yang diimplementasikan (`docs/08` TASK 011):
`locations`, `police_units`, `crime_incidents`, `intelligence_reports`, `patrol_activity`.

| Kriteria | Hasil |
|---|---|
| Model ORM sesuai `docs/02` §1–§5 | **Ya** |
| Migration tersedia (`0002`) | **Ya** |
| Constraint & index sesuai `docs/06` §3–§4 | **Ya** |
| Migration cocok dengan model | **Ya** — diuji otomatis (lihat §4) |
| Migration dijalankan terhadap database hidup | **Belum** — grup `docker` masih kosong |

---

## 1. PENGHALANG YANG TERSISA (sama seperti TASK 010)

```text
$ grep ^docker /etc/group
docker:x:988:           ← masih kosong

$ id kim
uid=1000(kim) gid=1000(kim) groups=1000(kim),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd)
```

`id kim` membaca database grup sistem (bukan kredensial proses sesi ini), jadi ini bukan efek
"sesi lama". Perintah `usermod` benar-benar belum berlaku untuk user `kim`.

```bash
sudo usermod -aG docker kim && getent group docker    # harus menampilkan: docker:x:988:kim
# lalu logout/login dan mulai ulang sesi Claude Code
```

Setelah itu:

```bash
pnpm db:up && pnpm db:migrate && pnpm db:current      # menuntaskan acceptance TASK 010 dan 011
```

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

**Belum dijalankan:** `pnpm db:up`, `pnpm db:migrate` terhadap PostgreSQL sungguhan.
Artinya perilaku khas PostgreSQL/PostGIS — pembuatan tipe `geometry`, index GIST, dan
`gen_random_uuid()` — belum diuji di database nyata.

---

## 5. TASK BERIKUTNYA

**TASK 012 — Public Tables**: `citizen_reports`, `public_alerts`, `community_feedback`.

Sebelum itu, dua hal yang sebaiknya dibereskan:

1. akses Docker (§1) agar acceptance TASK 010–011 dapat dituntaskan;
2. keputusan **B-3 taksonomi** — tidak memblokir, tetapi menentukan isi `config/taxonomy/`
   yang dibutuhkan saat seed (PHASE 3).
