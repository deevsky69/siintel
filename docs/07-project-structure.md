# STRUKTUR FOLDER — PREDIKSI PRESISI

Monorepo: web, API, mobile, ML, database, data, dan dokumentasi berada dalam satu repository dengan tanggung jawab terpisah.
Isi paket berada langsung di **root repository** (`siintel`).

```text
./
├── CLAUDE.md
├── README.md
├── .gitignore
├── .env.example
│
├── docs/
│   ├── 01-master-technical-specification.md
│   ├── 02-data-dictionary.md
│   ├── 03-role-permission-matrix.md
│   ├── 04-erd.md
│   ├── 05-api-design.md
│   ├── 06-database-schema.md
│   ├── 07-project-structure.md
│   ├── 08-implementation-roadmap.md
│   ├── implementation-notes/     # audit, decision log, catatan per task
│   └── source/                   # dokumen sumber (PDF konsep/Taskap)
│
├── design/                       # referensi visual UI
│
├── apps/
│   ├── web/                      # Next.js — dashboard internal
│   │   └── src/
│   ├── api/                      # FastAPI — API + business rules
│   │   └── src/
│   └── mobile/                   # Android LAPOR PRESISI (fase berikutnya)
│       └── src/
│
├── packages/
│   └── shared/                   # artefak lintas aplikasi
│       ├── types/                # tipe TS HASIL GENERATE dari OpenAPI — jangan ditulis manual
│       ├── schemas/              # skema validasi bersama sisi klien
│       └── constants/            # konstanta & label taksonomi
│
├── ml/
│   ├── notebooks/
│   ├── src/
│   │   ├── preprocessing/
│   │   ├── features/
│   │   ├── spatial/
│   │   ├── temporal/
│   │   ├── models/
│   │   ├── evaluation/
│   │   └── explainability/
│   └── configs/
│
├── database/
│   ├── migrations/               # Alembic
│   ├── seeds/
│   └── schema/
│
├── data/
│   ├── raw/                      # data mentah; tidak di-commit
│   ├── import/                   # siap mapping/import; tidak di-commit
│   ├── processed/                # hasil ETL/clean/anonymization; tidak di-commit
│   └── sample/                   # DATA DUMMY (satu-satunya yang di-commit)
│
├── scripts/
│   ├── import/
│   ├── seed/
│   ├── validation/
│   └── development/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── infra/
│   └── docker/                   # postgres+postgis, tile server pengembangan
│
└── config/
    ├── risk/                     # bobot risk score, threshold warning
    ├── model/                    # konfigurasi model
    └── taxonomy/                 # pemetaan nilai & label Bahasa Indonesia
```

---

## Tooling

`TECHNICAL DECISION` (SDL-03, SDL-04, SDL-05):

| Bagian | Keputusan |
|---|---|
| Frontend | Next.js + TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python + FastAPI |
| ORM/Migration | SQLAlchemy 2.x + Alembic + GeoAlchemy2 |
| Package manager Python | `uv` |
| Workspace TypeScript | pnpm workspaces |
| Peta | MapLibre GL JS (sumber tile: lihat `.env.example`) |
| Test | pytest + httpx (API), Vitest + Testing Library (web), Playwright (E2E) |

**Berbagi tipe antara Python dan TypeScript**: backend menghasilkan OpenAPI; tipe TS di `packages/shared/types` **digenerate** dari OpenAPI. Tipe tidak ditulis dua kali di dua bahasa — itu sumber kebenaran ganda yang pasti menyimpang.

---

## Aturan

1. Frontend tidak mengakses database secara langsung.
2. Semua perubahan schema melalui migration.
3. Data resmi tidak boleh diletakkan di `data/sample`.
4. Data sensitif di `data/raw`, `data/import`, `data/processed` di-ignore dari Git.
5. Pipeline data resmi mengikuti canonical pipeline CLAUDE.md §18:
   `data/raw → validation → mapping → anonymization → geo/grid → data/processed → database`.
   Tahap analitik (feature engineering → analysis → model → prediction → evaluation) berjalan **setelah** data berada di database, bukan sebagai bagian dari import.
6. Model ML dipisahkan dari API.
7. Recommendation → Commander Decision → Operational Action tetap human-in-the-loop.
8. Bobot risiko dan threshold warning yang belum disetujui tidak boleh di-hardcode; letakkan di `config/`.
9. Endpoint sensitif wajib authentication + authorization.
10. Aktivitas penting dicatat di audit trail.
11. Setiap prediction menyimpan `model_version`; setiap risk score menyimpan `weights_version`.
12. Setiap evaluation menunjuk prediction yang dievaluasi, **atau** kejadian aktual yang tidak diprediksi (false negative).
13. `packages/shared/types` berisi artefak generate — jangan diedit manual.
14. Dokumen sumber (PDF) disimpan di `docs/source/`, referensi visual di `design/`.

---

## Hubungan dengan MVP

Struktur web/API mendukung modul inti: Executive Dashboard, Live Crime Map, Historical Heatmap, Current Risk Layer, Predictive Heatmap, Crime Pattern DNA, AI Prediction, Risk Score, Early Warning, Explainability/WHY, AI Recommendation, Commander Approval, Operation Center, dan Prediction vs Actual.

Modul yang belum punya penopang requirement — Executive Brief dan AI Assistant — belum diberi tempat khusus sampai sumber kontennya diputuskan (U-11).
