# TASK 010 — POSTGRESQL / POSTGIS

Tanggal: 2026-08-31
Status: **SELESAI SEBAGIAN — satu acceptance criterion belum dapat diverifikasi (akses Docker).**

Acceptance dari `docs/08`:

| Kriteria | Hasil |
|---|---|
| Database dapat dibuat | **Belum diverifikasi** — daemon Docker tidak dapat diakses dari sesi ini |
| Migration dapat dijalankan dari kondisi kosong | **Belum diverifikasi terhadap database hidup.** Terverifikasi dalam mode offline: Alembic merender seluruh SQL dari kondisi kosong sampai `head` |
| Sistem migration tersedia | **Ya** — Alembic terpasang dan berfungsi |
| PostGIS | **Ya** — baseline `0001` mengaktifkan `postgis` dan `pgcrypto` |

---

## 1. PENGHALANG YANG TERSISA

Perintah `usermod` belum berlaku:

```text
$ getent group docker
docker:x:988:            ← daftar anggota kosong

$ id
uid=1000(kim) gid=1000(kim) groups=1000(kim),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),101(lxd)
                                                                    ← tidak ada grup docker
```

Daemon Docker sendiri `active`, socket-nya `srw-rw---- root:docker`. Perbaikan (butuh hak sistem,
tidak dijalankan tanpa persetujuan):

```bash
sudo usermod -aG docker $USER
# lalu logout/login, dan mulai ulang sesi Claude Code agar prosesnya membawa grup baru
```

Alternatif tanpa Docker: sediakan PostgreSQL 16/17 dengan PostGIS lalu sesuaikan `DATABASE_URL`.
`sg docker`/`newgrp` tidak menolong karena keanggotaan grup memang belum ada, dan `sudo` di mesin
ini meminta password sehingga tidak dapat dijalankan dari sesi non-interaktif.

Setelah akses tersedia, satu perintah menyelesaikan sisa acceptance:

```bash
pnpm db:up && pnpm db:migrate && pnpm db:current
```

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

**Belum dijalankan:** `pnpm db:up`, `pnpm db:migrate` terhadap database sungguhan.

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
