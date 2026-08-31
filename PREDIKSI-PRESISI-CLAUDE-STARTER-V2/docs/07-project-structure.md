# STRUKTUR FOLDER — PREDIKSI PRESISI

Gunakan monorepo agar web, API, mobile, ML, database, data, dan dokumentasi berada dalam satu repository dengan tanggung jawab terpisah.

```text
PREDIKSI-PRESISI/
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
│   └── 07-project-structure.md
│
├── apps/
│   ├── web/                 # Dashboard internal
│   │   └── src/
│   ├── api/                 # Backend/API + business rules
│   │   └── src/
│   └── mobile/              # Android LAPOR PRESISI (fase berikutnya)
│       └── src/
│
├── packages/
│   └── shared/              # Type/schema/constant bersama
│       ├── types/
│       ├── schemas/
│       └── constants/
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
│   ├── migrations/
│   ├── seeds/
│   └── schema/
│
├── data/
│   ├── raw/                 # Data mentah; jangan commit data sensitif
│   ├── import/              # File siap mapping/import
│   ├── processed/           # Hasil ETL/clean/anonymization
│   └── sample/              # DATA DUMMY
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
│   └── docker/
│
└── config/
    ├── risk/
    ├── model/
    └── taxonomy/
```

## Aturan

1. Frontend tidak mengakses database secara langsung.
2. Semua perubahan schema melalui migration.
3. Data resmi tidak boleh diletakkan di `data/sample`.
4. Data sensitif di `data/raw` harus di-ignore dari Git.
5. Data resmi melewati `validation → mapping → anonymization → geo/grid → processed → database`.
6. Model ML dipisahkan dari API.
7. Recommendation → Commander Decision → Operational Action tetap human-in-the-loop.
8. Bobot risk dan threshold warning yang belum disetujui tidak boleh di-hardcode.
9. Endpoint sensitif wajib authentication + authorization.
10. Aktivitas penting dicatat di audit trail.
11. Setiap prediction menyimpan `model_version`.
12. Setiap evaluation menunjuk prediction yang dievaluasi.

## Hubungan dengan MVP

Struktur web/API mendukung modul inti: Executive Dashboard, Live Crime Map, Historical Heatmap, Crime Pattern DNA, Predictive Heatmap, AI Prediction, Risk Score, Early Warning, Explainability/WHY, AI Recommendation, Commander Approval, dan Prediction vs Actual. fileciteturn2file13
