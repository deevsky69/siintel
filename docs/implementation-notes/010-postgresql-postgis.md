# TASK 010 — POSTGRESQL / POSTGIS

Tanggal: 2026-08-31 (dituntaskan 2026-09-01)
Status: **SELESAI — seluruh acceptance terverifikasi terhadap database sungguhan.**

Acceptance dari `docs/08`:

| Kriteria | Hasil |
|---|---|
| Database dapat dibuat | **Ya** — `pnpm db:up` menjalankan PostgreSQL 17.5 + PostGIS 3.5.2 |
| Migration dapat dijalankan dari kondisi kosong | **Ya** — `upgrade head` → `downgrade base` → `upgrade head` berhasil |
| Sistem migration tersedia | **Ya** — Alembic terpasang dan berfungsi |
| PostGIS | **Ya** — `postgis 3.5.2` dan `pgcrypto 1.3` aktif di database |

---

## 1. PENGHALANG YANG SEMPAT ADA (SUDAH SELESAI)

Selama TASK 010–011 dikerjakan, user belum tergabung di grup `docker` sehingga migration hanya
dapat diverifikasi lewat render SQL. Pemilik proyek menjalankan `sudo usermod -aG docker kim`
pada 2026-09-01 dan sejak itu verifikasi penuh dapat dilakukan.

Catatan untuk lingkungan baru: sesi yang sudah berjalan tidak otomatis membawa grup baru;
gunakan `sg docker -c "..."`, atau logout/login.

Jalur alternatif yang sempat ditelusuri dan **tidak** memadai (dicatat agar tidak diulang):

| Jalur | Kendala |
|---|---|
| Docker rootless | `newuidmap`/`newgidmap` (paket `uidmap`) tidak terpasang, dan `kernel.apparmor_restrict_unprivileged_userns=1` |
| PostgreSQL user-space (`pgserver` dari PyPI) | Hanya membawa PostgreSQL 16.2 + `plpgsql` + `vector`; **tanpa PostGIS dan pgcrypto** |

---

## 2. YANG DIBUAT

```text
apps/api/alembic.ini                              konfigurasi Alembic; TIDAK memuat URL database
database/migrations/env.py                        membaca DATABASE_URL dari environment
database/migrations/script.py.mako                template revisi (bertipe, sesuai gaya proyek)
database/migrations/versions/0001_enable_extensions.py
database/migrations/README
apps/api/src/prediksi_presisi_api/db.py           engine lazy, session factory, Base
apps/api/tests/test_database.py                   5 test tanpa database hidup
```

Dependensi baru: `sqlalchemy 2.0.52`, `alembic`, `geoalchemy2 0.20.0`, `psycopg[binary] 3.3.4`.

Script root baru: `db:migrate`, `db:rollback`, `db:current`, `db:history`, `db:sql`.

---

## 3. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | Migration diletakkan di `database/migrations`, konfigurasinya di `apps/api/alembic.ini` | `docs/07` menempatkan migration di `database/`, sementara Alembic perlu berjalan di dalam venv API yang memuat model |
| 2 | `DATABASE_URL` **tidak pernah** ditulis di `alembic.ini`; `env.py` membacanya dari environment | CLAUDE.md §28 — tidak ada kredensial di repository |
| 3 | Engine dibuat *lazy* (`lru_cache`) dan bukan saat import | Import modul aplikasi tidak boleh membuka koneksi; test dan build tetap berjalan tanpa database |
| 4 | Baseline `0001` hanya mengaktifkan ekstensi, tidak membuat tabel | TASK 010 adalah "database + PostGIS + sistem migration"; tabel adalah TASK 011 (CLAUDE.md §7 — jangan melompat) |
| 5 | `downgrade()` tidak men-*drop* ekstensi | Objek lain dapat bergantung padanya; men-drop ekstensi berisiko merusak database |
| 6 | `pgcrypto` ikut diaktifkan | Diperlukan `gen_random_uuid()` untuk primary key UUID (`docs/02` K-1) |
| 7 | Berkas migration ikut dicakup Ruff, tidak dicakup mypy | Nama berkas revisi diawali angka sehingga bukan nama modul Python yang sah bagi mypy |

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
uv sync --all-groups        → sqlalchemy 2.0.52, alembic, geoalchemy2 0.20.0, psycopg 3.3.4

alembic history             → <base> -> 0001 (head)
alembic heads               → 0001 (head)
alembic upgrade head --sql  → merender: CREATE TABLE alembic_version,
                              CREATE EXTENSION IF NOT EXISTS postgis,
                              CREATE EXTENSION IF NOT EXISTS pgcrypto,
                              INSERT INTO alembic_version VALUES ('0001'), COMMIT

ruff check . ../../database/migrations         → All checks passed
ruff format --check (8 berkas)                 → sudah terformat
mypy                                            → no issues in 6 source files
pytest                                          → 9 test lulus (4 skeleton + 5 database)
biome check (web)                               → 10 berkas bersih
vitest (web)                                    → 2 test lulus
```

**Dijalankan terhadap database sungguhan (2026-09-01):**

```text
pnpm db:up                  → PostgreSQL 17.5 (Debian), container predpol-db healthy
alembic upgrade head        → 0001, lalu 0002
select extname, extversion  → postgis 3.5.2, pgcrypto 1.3, plpgsql 1.0 (+ topology, tiger)
select version_num          → 0002
alembic downgrade base      → kedua migration turun bersih
alembic upgrade head        → naik lagi dari kosong; 5 tabel inti kembali terbentuk
```

---

## 5. TASK BERIKUTNYA

**TASK 011 — Core Tables**: `locations`, `police_units`, `crime_incidents`, `intelligence_reports`,
`patrol_activity` mengikuti `docs/02`.

Catatan: TASK 011 memerlukan database hidup untuk menguji migration, jadi penghalang §1 sebaiknya
dibereskan lebih dulu. Selain itu dua keputusan pengguna berikut memengaruhi bentuk tabelnya —
sebaiknya dijawab sebelum migration tabel ditulis:

- **B-3 taksonomi final** (U-16) — menentukan enum `incident_type`, `modus`, `target_type`, `location_type`;
- **B-4 ukuran grid & batas wilayah** (U-04) — menentukan apakah `locations` perlu geometri poligon.

Keduanya dapat ditunda dengan konsekuensi migration tambahan di kemudian hari.
