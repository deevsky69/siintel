# TASK 002 — DEVELOPMENT ENVIRONMENT

Tanggal: 2026-08-31
Status: **SELESAI — acceptance criteria terpenuhi dan diverifikasi.**

Acceptance dari `docs/08` (`install / run / lint / test` berhasil):

| Kriteria | Hasil |
|---|---|
| `install` | `pnpm install` + `uv sync --all-groups` berhasil |
| `run` | web `next dev`/`next build` dan API `uvicorn` berjalan (diverifikasi pada TASK 001, build diulang di sini) |
| `lint` | Biome (web) dan Ruff (API) bersih |
| `test` | Vitest 2 test + pytest 4 test, seluruhnya lulus |
| Konfigurasi lokal | `.env.example` lengkap; `Settings` membaca environment |
| Placeholder koneksi database | `apps/api/src/prediksi_presisi_api/config.py` — **tanpa** koneksi (TASK 010) |

---

## 1. REKOMENDASI INFRASTRUKTUR YANG DIAMBIL

Pengguna mempersilakan memakai infrastruktur yang lebih efisien. Keputusan berikut diambil sebagai
`TECHNICAL DECISION` dan dokumennya (`docs/01` §10.1, `docs/07`) sudah disesuaikan.

| # | Keputusan | Alasan | Yang digantikan |
|---|---|---|---|
| 1 | **Ruff** untuk lint **dan** format Python | Satu binary, satu konfigurasi, jauh lebih cepat | black + isort + flake8 (3 alat) |
| 2 | **Biome** untuk lint **dan** format TypeScript/React/CSS | Satu binary, satu konfigurasi | ESLint + Prettier (2 alat) |
| 3 | **mypy `strict`** untuk API | Padanan `tsc --noEmit`; sistem ini banyak bekerja dengan struktur data, kesalahan tipe mahal | — |
| 4 | **Playwright ditunda** ke TASK 165 | Unduhan browser besar tanpa manfaat selama belum ada UI yang layak diuji E2E | — |
| 5 | **Script tunggal di root** (`pnpm verify`, `lint`, `typecheck`, `test`, `db:up`) | Satu entrypoint untuk monorepo dua bahasa tanpa menambah alat baru | Makefile / task runner tambahan |
| 6 | **GitHub Actions CI** | Remote `origin` sudah ada; regresi lint/type/test tertangkap otomatis | — |
| 7 | **Docker Compose dengan profile** | `db` jalan default; `tileserver` hanya pada profile `gis` sehingga tidak gagal saat berkas tile belum ada | satu compose monolitik |

**Konsekuensi yang diterima (Biome).** Biome tidak punya aturan khusus Next.js seperti
`eslint-config-next` (mis. `no-img-element`, aturan `next/script`). Bila kelak muncul kesalahan khas
Next.js yang lolos, `eslint-config-next` dapat ditambahkan berdampingan tanpa membongkar konfigurasi.

---

## 2. YANG DIBUAT / DIUBAH

```text
infra/docker/docker-compose.yml     PostGIS 17-3.5 (+ healthcheck) dan tileserver-gl (profile "gis")
data/tiles/README.md                tempat berkas .mbtiles; isinya tidak di-commit
.github/workflows/ci.yml            CI dua job: web dan api
package.json                        script lint/typecheck/test/verify/db:up/gis:up untuk kedua sisi
pnpm-workspace.yaml                 allowBuilds esbuild (dibutuhkan Vitest)
.env.example                        POSTGRES_*, TILESERVER_PORT
.gitignore                          data/tiles/*

apps/api/pyproject.toml             dependency-group dev (ruff, mypy, pytest, httpx) + konfigurasi ketiganya
apps/api/src/.../config.py          Settings berbasis pydantic-settings (placeholder DATABASE_URL)
apps/api/src/.../main.py            memakai Settings untuk menampilkan app_env
apps/api/tests/test_skeleton.py     4 test

apps/web/biome.json                 lint + format
apps/web/vitest.config.mts          jsdom + plugin react
apps/web/src/app/page.test.tsx      2 test
apps/web/package.json               script lint/format/test + dev deps

docs/01 §10.1, docs/07              tabel toolchain, struktur, aturan 15–16
```

---

## 3. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
pnpm install                              → selesai, esbuild build script disetujui via allowBuilds
uv sync --all-groups                      → ruff 0.16.5, mypy, pytest 9.1.1, httpx

biome check .            (web)            → Checked 10 files, tanpa error
ruff check .             (api)            → All checks passed!
ruff format --check .    (api)            → 4 files already formatted

tsc --noEmit             (web)            → tanpa error
mypy                     (api)            → Success: no issues found in 4 source files

vitest run               (web)            → 1 file, 2 test lulus
pytest                   (api)            → 4 test lulus

next build               (web)            → ✓ compiled; route / dan /_not-found
docker compose config                     → berkas compose valid (parse)
```

---

## 4. SISA MASALAH

1. **Docker daemon tidak dapat diakses** dari sesi ini: pengguna belum tergabung di grup `docker`
   (`permission denied … /var/run/docker.sock`, daemon `active`). Akibatnya `pnpm db:up` **belum pernah
   dijalankan** — berkas compose baru diverifikasi sampai tahap parse.
   Perbaikan butuh hak sistem: `sudo usermod -aG docker $USER` lalu login ulang. Tidak dilakukan tanpa persetujuan.
2. Peringatan `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`
   pada pytest — berasal dari kombinasi versi Starlette/httpx, tidak mempengaruhi hasil. Ditinjau ulang
   saat TASK 030.
3. `corepack enable pnpm` belum dijalankan di mesin ini (butuh tulis ke direktori bin global);
   sementara jalankan lewat `corepack pnpm …`.
4. CI belum pernah dieksekusi GitHub (belum ada push setelah workflow dibuat).

---

## 5. TASK BERIKUTNYA

**TASK 010 — PostgreSQL/PostGIS**: database pengembangan, ekstensi PostGIS, dan sistem migration
(Alembic), dengan acceptance database dapat dibuat dan migration dapat dijalankan dari kondisi kosong.

Prasyarat yang perlu dibereskan lebih dulu: akses Docker (butir 1 di atas) atau instance PostgreSQL lain.
