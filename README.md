# PREDIKSI PRESISI

Repository: `siintel`

Sistem pendukung keputusan Kamtibmas berbasis predictive policing & spatial intelligence.

> Optimalisasi Deteksi Dini Kerawanan Kamtibmas melalui Predictive Policing Artificial Intelligence
> guna meningkatkan efektivitas pencegahan gangguan terpeliharanya Kamtibmas.

Status proyek: **PHASE 0 selesai — spesifikasi terkunci sebagian.**
Butir yang menunggu keputusan pemilik proyek tercatat pada `docs/implementation-notes/000c-specification-lock.md`.

---

## Isi repository

| Path | Keterangan |
|---|---|
| `CLAUDE.md` | Aturan kerja AI coding assistant |
| `docs/01-master-technical-specification.md` | Spesifikasi utama |
| `docs/02-data-dictionary.md` | Definisi data kanonik |
| `docs/03-role-permission-matrix.md` | RBAC: matriks, katalog permission, scope |
| `docs/04-erd.md` | ERD & relasi |
| `docs/05-api-design.md` | Kontrak API |
| `docs/06-database-schema.md` | Panduan implementasi schema |
| `docs/07-project-structure.md` | Struktur folder & aturan repository |
| `docs/08-implementation-roadmap.md` | Roadmap, TASK-ID, urutan eksekusi |
| `docs/implementation-notes/` | Audit, decision log, catatan pelaksanaan task |
| `docs/source/` | Dokumen sumber (PDF konsep/Taskap) |
| `design/` | Referensi visual UI |
| `apps/`, `packages/`, `ml/`, `database/`, `data/`, `scripts/`, `tests/`, `infra/`, `config/` | Lihat `docs/07` |

## Urutan baca

1. `CLAUDE.md`
2. `docs/01-master-technical-specification.md`
3. `docs/02-data-dictionary.md`
4. `docs/03-role-permission-matrix.md`
5. `docs/04-erd.md`
6. `docs/05-api-design.md`
7. `docs/06-database-schema.md`
8. `docs/07-project-structure.md`
9. `docs/08-implementation-roadmap.md`
10. `docs/implementation-notes/` (audit + keputusan yang sudah diambil)

## Stack

Next.js + TypeScript · Tailwind CSS + shadcn/ui · Python + FastAPI · PostgreSQL + PostGIS ·
SQLAlchemy 2.x + Alembic + GeoAlchemy2 · MapLibre GL JS · Python ecosystem untuk analitik/ML.

Rincian dan alasannya: `docs/01` §10.

## Menjalankan (skeleton — TASK 001)

Prasyarat: Node ≥22 (dengan Corepack), Python ≥3.12, dan [`uv`](https://docs.astral.sh/uv/).

```bash
# sekali saja
corepack enable pnpm          # atau jalankan pnpm lewat: corepack pnpm <perintah>

# frontend (http://localhost:3000)
pnpm install
pnpm dev

# backend (http://localhost:8000)
cd apps/api
uv sync
uv run uvicorn prediksi_presisi_api.main:app --reload --port 8000
```

```bash
# database (PostgreSQL + PostGIS via Docker)
pnpm db:up          # jalankan container
pnpm db:migrate     # alembic upgrade head
pnpm db:current     # revisi terpasang

# pemeriksaan mutu
pnpm verify         # lint + typecheck + test untuk web dan API
```

Salin `.env.example` menjadi `.env` untuk pengembangan lokal. Database baru berisi ekstensi
PostGIS/pgcrypto — tabel dibuat mulai TASK 011. Autentikasi dan endpoint domain menyusul.

## Cara kerja

- Satu task = satu perubahan terukur, mengikuti TASK-ID pada `docs/08`.
- Jangan melompati fase; lihat GATE RULE pada `docs/08`.
- Setiap perubahan schema lewat migration.
- Setiap endpoint sensitif: authentication + authorization + validation + audit.

## Data

`data/sample/` berisi **data sintetis/dummy**. Data resmi mengikuti alur
`data/raw/ → data/import/ → validation → mapping → anonymization → geo/grid → data/processed/ → database`
dan tidak boleh di-commit. Jangan memasukkan password, API key, token, atau data pribadi ke repository.
