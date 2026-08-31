# TASK 001 — INITIALIZE REPOSITORY

Tanggal: 2026-08-31
Status: **SELESAI — acceptance criteria terpenuhi dan diverifikasi.**

Acceptance dari `docs/08`:

| Kriteria | Hasil |
|---|---|
| Project dapat dijalankan | **Ya** — web build + typecheck berhasil; API melayani permintaan HTTP (bukti di §3) |
| Folder sesuai structure | **Ya** — mengikuti `docs/07` |
| Environment example tersedia | **Ya** — `.env.example` di root |

Tidak ada fitur bisnis, database, autentikasi, maupun endpoint domain yang dibuat.

---

## 1. YANG DIBUAT

```text
package.json                                  workspace root (scripts dev/build/typecheck)
pnpm-workspace.yaml                           apps/web + packages/*
pnpm-lock.yaml

apps/web/package.json                         Next.js 15 + React 19 + Tailwind 4
apps/web/tsconfig.json                        strict, path alias @/*
apps/web/next.config.ts
apps/web/postcss.config.mjs
apps/web/next-env.d.ts                        (dihasilkan Next)
apps/web/src/app/layout.tsx                   lang="id", metadata dasar
apps/web/src/app/page.tsx                     halaman penanda skeleton
apps/web/src/app/globals.css                  entry Tailwind

apps/api/pyproject.toml                       FastAPI + uvicorn, PEP 621
apps/api/uv.lock
apps/api/src/prediksi_presisi_api/__init__.py
apps/api/src/prediksi_presisi_api/main.py     satu route: GET /

docs/implementation-notes/001-project-bootstrap.md
README.md                                     bagian "Menjalankan"
```

`.gitkeep` pada `apps/web/src` dan `apps/api/src` dihapus karena direktorinya sudah berisi file.
`apps/mobile/`, `packages/shared/`, `ml/`, `database/`, `infra/`, `scripts/`, `tests/` tetap placeholder — fasenya belum tiba.

---

## 2. KEPUTUSAN

| # | Keputusan | Kategori |
|---|---|---|
| 1 | Route yang dibuat adalah `GET /` yang mengembalikan `{name, version, state}`, **bukan** `/health`. Health endpoint, konfigurasi, error handling, validation, dan logging adalah lingkup TASK 030 — jangan didahului. | `TECHNICAL DECISION` |
| 2 | Next.js App Router ditempatkan di `apps/web/src/app` agar sesuai struktur `apps/web/src/` pada `docs/07`. | `TECHNICAL DECISION` |
| 3 | Skeleton ditulis manual, bukan lewat `create-next-app`, agar tidak ada halaman contoh/aset demo yang harus dibersihkan. | `TECHNICAL DECISION` |
| 4 | Lint, formatter, test runner, dan placeholder koneksi database **tidak** dibuat di sini — itu TASK 002. | Mengikuti roadmap |
| 5 | `uv` dipasang di level pengguna (`~/.local/bin/uv`, tanpa sudo) karena sistem ini tidak memiliki `pip` maupun `python3-venv`, sedangkan `uv` adalah package manager yang ditetapkan `docs/07`. | `TECHNICAL DECISION` |
| 6 | `pnpm` dijalankan lewat Corepack (`corepack pnpm …`) karena belum ter-*enable* secara global. Script di `package.json` tetap ditulis dengan `pnpm` standar. | `TECHNICAL DECISION` |

**Catatan lingkungan:** `python3-venv` dan `pip` tidak tersedia di mesin ini. Bila di kemudian hari
diperlukan tanpa `uv`, pemasangannya butuh `sudo apt install python3.12-venv` — tindakan tingkat sistem
yang tidak dilakukan tanpa persetujuan.

---

## 3. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
corepack pnpm install
  → 46 paket, selesai 5.4s

corepack pnpm --filter @prediksi-presisi/web build
  → ✓ Compiled successfully
  → Route (app):  ○ /  123 B, first load JS 102 kB
                  ○ /_not-found

corepack pnpm --filter @prediksi-presisi/web typecheck
  → tsc --noEmit, tanpa error

uv sync            (apps/api)
  → fastapi 0.141.1, starlette 1.6.0, uvicorn 0.52.4, pydantic 2.13.5

uvicorn prediksi_presisi_api.main:app --port 8011
  → GET /             200  {"name":"prediksi-presisi-api","version":"0.1.0","state":"skeleton"}
  → GET /openapi.json 200  title "PREDIKSI PRESISI API"
  → GET /health       404  (benar — belum dibuat, lihat TASK 030)
```

Belum ada unit/integration test — test runner dikonfigurasi pada TASK 002.

---

## 4. SISA MASALAH

1. `corepack enable pnpm` belum dijalankan di mesin ini, sehingga `pnpm dev` langsung dari root
   perlu Corepack aktif; sementara ini pakai `corepack pnpm …`.
2. Belum ada lint/format/test — TASK 002.
3. Belum ada `infra/docker` (PostGIS + tile server pengembangan sesuai keputusan B-1 opsi C) — TASK 002/010.

## 5. TASK BERIKUTNYA

**TASK 002 — Development Environment**: konfigurasi lokal, placeholder koneksi database, lint, formatter,
test runner, dengan acceptance `install / run / lint / test` berhasil.
