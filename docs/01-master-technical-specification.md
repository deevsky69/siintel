# PREDIKSI PRESISI
## MASTER TECHNICAL SPECIFICATION v1.0
### Predictive Policing & Spatial Intelligence System

> Status: Draft foundation for software development
> Source basis: uploaded PREDIKSI PRESISI concept/specification documents and supplied UI reference.
> Purpose: become the shared technical/business baseline for the human project owner and Claude Code.

---

# 1. PRODUCT VISION

PREDIKSI PRESISI is a decision-support platform intended to transform Kamtibmas data,
field information, and community signals into actionable intelligence for earlier,
more targeted, and measurable prevention.

The system is not intended to replace authorized police decisions.

Core lifecycle:

DATA
→ ANALYSIS
→ PREDICTION
→ EARLY WARNING
→ RECOMMENDATION
→ HUMAN DECISION
→ ACTION
→ EVALUATION
→ MODEL UPDATE

The key questions presented by the system are:

- WHAT may occur?
- WHERE is the relative risk?
- WHEN is the relevant time window?
- HOW HIGH is the risk?
- WHY is the system producing that assessment?
- WHAT response options may be considered?

---

# 2. RESEARCH / OPERATIONAL POSITION

The project frames AI as an instrument. The principal object remains early detection,
commander decision support, and prevention of Kamtibmas disturbances.

The prediction unit is area + time, not an individual.

For the proof of concept, Curanmor is the primary use case, with Curat and Curas as
comparison/expansion cases.

The source concept describes the scientific foundation as:
WHERE + WHEN + HOW + TARGET + REPEAT
combined with spatial, temporal, modus, and contextual information.

---

# 3. MVP SCOPE

The MVP contains:

1. Login and Role-Based Access Control
2. Executive Command Dashboard
3. Live Crime Map
4. Historical Heatmap
5. Predictive Heatmap
6. AI Risk Scoring
7. AI Prediction Center
8. Early Warning
9. AI Recommendation
10. Crime Analytics
11. Prediction vs Actual Evaluation
12. Executive Brief

A broader blueprint also identifies:
- Crime Pattern DNA
- Explainability / WHY
- Commander Approval
- Community Intelligence
- Operation Center
- Patrol Optimization
- AI Assistant

These should be treated as modules/roadmap items and implemented according to the
approved development plan rather than added indiscriminately.

---

# 4. USER ROLES

Initial role hierarchy:

## Level 1 — Pimpinan
Strategic dashboard, prediction, recommendation, approval.

## Level 2 — Command Center
Monitoring, warning, tasking, deployment.

## Level 3 — Analyst
Analytics, spatial analysis, modelling, evaluation.

## Level 4 — Fungsi
Access according to authorized function:
Intelkam / Reskrim / Samapta / Binmas / Lantas.

## Level 5 — Polsek
Data and situation within its jurisdiction.

## Level 6 — Administrator
Technical configuration and user/system management.

All important activities must be recorded in audit trail.

---

# 5. CORE MODULES

## 5.1 Executive Dashboard
Display:
- security/situation index
- incidents in last 24 hours
- top threats
- high-risk areas
- predictions
- active warnings
- active units
- 7/30-day trends
- AI executive brief

## 5.2 Live Kamtibmas Map
Map layers may include:
- actual incidents
- historical heatmap
- predictive heatmap
- patrol activity
- police facilities
- relevant POI
- administrative boundaries

Drill-down concept:
area → sub-area → grid.

## 5.3 Crime Analytics
Support:
- yearly/monthly/daily trends
- crime type distribution
- modus distribution
- geographic distribution
- risky hours
- day-hour matrix
- repeat pattern
- area comparison

## 5.4 Crime Pattern DNA
Represent:
- WHERE
- WHEN
- HOW
- TARGET
- REPEAT / NEAR-REPEAT

## 5.5 Prediction Center
Input:
- forecast horizon: 6h, 12h, 24h, 3d, 7d

Output:
- threat type
- area
- time window
- risk score
- confidence
- dominant factors / WHY

## 5.6 Predictive Heatmap
Support temporal views such as:
NOW → +6H → +12H → +24H → +3D → +7D

## 5.7 Risk Scoring
Initial conceptual scale:
0–100

Initial classes:
- Low
- Moderate
- High
- Critical

The exact weighting formula must be documented and validated; do not invent final
weights without an approved methodology.

## 5.8 Early Warning
Trigger when an approved risk threshold is crossed.

Alert should contain:
- threat
- location/area
- time window
- risk score
- confidence
- severity
- status
- creation time
- review/treatment history

## 5.9 AI Recommendation
The system proposes options for:
- Samapta
- Binmas
- Intelkam
- Reskrim
- Lantas

Recommendations are advisory only.

Commander/authorized human workflow:
REVIEW → APPROVE / MODIFY / REJECT

## 5.10 Prediction vs Actual
Compare predictions with actual events.

Metrics may include:
- precision
- recall
- false positive
- false negative
- temporal performance
- spatial performance

The evaluation should be transparent enough to support Taskap validation.

---

# 6. DATA STRATEGY

## 6.1 Minimum Crime Incident Dataset

Required / recommended fields:

- anonymous incident ID
- incident type
- incident date
- incident time
- Polsek
- Kecamatan
- Kelurahan
- address or grid
- latitude
- longitude
- location type
- modus
- target/object type
- handling status

Development should use anonymized or synthetic data.

Do not require victim/offender/witness identity for the proof of concept.

## 6.2 Supporting Internal Data

Potential sources:
- Reskrim
- Intelkam
- Samapta
- Binmas
- Lantas
- SPKT / 110
- Command Center

Examples:
- patrol activity
- intelligence indicators
- community reports
- traffic incidents
- problem solving
- threat categories
- reliability/confidence
- follow-up status

## 6.3 External Context

Potential contextual data:
- population density
- road network
- POI
- public facilities
- activity centers
- events/calendar
- weather

External data must be added only when source, legality, licensing, and usefulness are clear.

---

# 7. DATA PIPELINE

Terdapat **dua** pipeline yang sebelumnya tertulis sebagai satu rangkaian sehingga menimbulkan
penyebutan tahap yang tidak konsisten antar dokumen. Keduanya kini dipisah.

## 7.1 Pipeline ingestion (canonical — CLAUDE.md §18)

data/raw
→ VALIDATION
→ MAPPING
→ ANONYMIZATION
→ GEO / GRID
→ data/processed
→ DATABASE

Pembersihan (*cleaning*) adalah bagian dari tahap VALIDATION/MAPPING, bukan tahap tersendiri.
Format file sumber resmi tidak harus sama dengan canonical schema — gunakan ETL/mapping adapter.

## 7.2 Pipeline analitik (berjalan setelah data ada di database)

DATABASE
→ FEATURE ENGINEERING
→ ANALYSIS
→ MODEL
→ PREDICTION
→ EVALUATION

Data quality checks should cover:
- missing values
- invalid dates/times
- invalid coordinates
- duplicate records
- inconsistent categories
- impossible combinations
- outliers requiring review

---

# 8. PREDICTION DATA SPLIT

The supplied concept uses:

Training:
2023–2024

Validation:
Jan–Sep 2025

Holdout:
Oct–Dec 2025

The implementation must not leak future information into training features.

The final model and split must be documented in the evaluation report.

---

# 9. DATABASE INITIAL BLUEPRINT

Core entities:

## Administration
- users
- roles
- permissions
- audit_logs

## Kamtibmas
- crime_incidents
- locations
- intelligence_reports
- patrol_activity
- police_units

## Public
- citizen_reports
- public_alerts
- community_feedback

## Analytics
- risk_scores
- predictions
- early_warnings
- recommendations

## Operations
- commander_decisions
- operational_actions
- prediction_actual

Do not implement every table at once. Start with the entities required by the first
vertical slice and expand incrementally.

---

# 10. PROPOSED SYSTEM ARCHITECTURE

Recommended initial architecture: modular monolith.

Frontend:
Next.js + TypeScript

UI:
Tailwind CSS + shadcn/ui

Backend:
Python + FastAPI

Database:
PostgreSQL + PostGIS

Analytics/ML:
Python ecosystem

Map:
MapLibre GL JS

Version control:
Git

## 10.1 Confirmed toolchain (`TECHNICAL DECISION`)

The stack above is confirmed as-is. Items that the source documents left open are decided as follows:

| Concern | Decision |
|---|---|
| ORM / migration | SQLAlchemy 2.x + Alembic + GeoAlchemy2 |
| Python package manager | `uv` |
| TypeScript workspace | pnpm workspaces |
| Type sharing Python ↔ TypeScript | Frontend types are **generated** from the backend OpenAPI document; never hand-written twice |
| Authentication | JWT access token + refresh token in `httpOnly` cookie; Argon2id password hashing |
| Lint + format | Ruff (Python) and Biome (TypeScript/CSS) — one tool per side, lint and format combined |
| Type checking | mypy `strict` (API) and `tsc --noEmit` (web) |
| Testing | pytest + httpx (API), Vitest + Testing Library (web), Playwright (E2E, installed at TASK 165) |
| CI | GitHub Actions — lint, typecheck, test, build on both sides |

**Map tiles — decided by the project owner (2026-08-31): hybrid.** Development uses a locally hosted tile
server from `infra/docker`; the production environment and its tile source remain open until PHASE 16.
Tile and style URLs are always read from the environment — never hard-coded — so the production target can
change without touching source code.

Conceptual flow:

Web / Android
      ↓
API
      ↓
Backend modules
      ↓
PostgreSQL + PostGIS
      ↓
Analytics / ML
      ↓
Prediction / Risk / Warning
      ↓
Human review
      ↓
Decision / Action
      ↓
Evaluation

Android is a later client of the same backend API. It must not directly access the
database.

---

# 11. SECURITY & GOVERNANCE

Required principles:

- RBAC
- audit trail
- data minimization
- access restriction for sensitive information
- human-in-the-loop
- explainability
- model validation
- bias monitoring
- cybersecurity
- clear separation between AI output and police decision

Security requirements:
- no secrets in source code
- authentication required for internal functions
- authorization enforced server-side
- input validation
- secure file handling
- logging of important actions
- least-privilege access
- environment-based configuration

---

# 12. AI GOVERNANCE

The system must never describe a prediction as certainty.

Preferred wording:
"estimated relative risk", "predicted hotspot", "confidence", "dominant factors".

The AI recommendation engine produces options; it does not autonomously execute
police operations.

Every operational recommendation must pass human review and authorization.

---

# 13. UI/UX DIRECTION

The supplied visual reference establishes a command-center style.

Design intent:
- information-dense but readable
- map-centric
- executive/operational dashboard
- strong risk hierarchy
- clear warnings
- clear AI explanation
- responsive layout
- consistent component system

Primary information hierarchy:

SITUATION
→ RISK
→ LOCATION
→ TIME
→ PREDICTION
→ WHY
→ WARNING
→ RECOMMENDATION
→ HUMAN DECISION

Design reference files should be stored under /design.

---

# 14. API DIRECTION

Initial API areas:

/api/auth
/api/users
/api/roles
/api/crimes
/api/locations
/api/map
/api/analytics
/api/risk-scores
/api/predictions
/api/warnings
/api/recommendations
/api/commander-decisions
/api/evaluation
/api/executive-brief

Exact endpoints, schemas, authentication, pagination, filtering, and error contracts are defined in
`docs/05-api-design.md`, which is now the authoritative API document. Two changes made there:

- `/api/map` is split into `current-risk` (from `risk_scores`) and `predictive-heatmap` (from `predictions`),
  because those are two different layers — see `docs/04`;
- `/api/executive-brief` is **not** defined until the source of its content is decided (§19.2).

---

# 15. DEVELOPMENT METHOD

Build vertical slices, not all frontend first and backend later.

Recommended first slice:

LOGIN
→ DASHBOARD
→ CRIME DATA
→ MAP
→ RISK
→ PREDICTION
→ WARNING
→ RECOMMENDATION
→ HUMAN DECISION
→ EVALUATION

Each slice must be runnable and testable.

## 15.1 How this is reconciled with the roadmap (`TECHNICAL DECISION`)

`docs/08` is organised by layer (database → API → UI), which reads as the opposite of "vertical slices".
The reconciliation is:

- The **phase order and gates** of `docs/08` are authoritative (CLAUDE.md §38–§39). Phases are not reordered.
- The vertical-slice intent is satisfied by the **CHECKPOINT rule**: a checkpoint may only be declared when its
  slice actually runs end-to-end, not when its files exist.
- Within PHASE 4/5 the execution order *is* adjusted so authorization exists before domain APIs
  (see "URUTAN EKSEKUSI" in `docs/08`).

The intent of this section stands: a feature counts as done when it is runnable and testable end-to-end,
not when its layer is complete.

---

# 16. DEVELOPMENT PHASES

> **Penomoran.** Bagian ini adalah **tahapan konseptual**. Penomoran fase operasional yang mengikat
> adalah `docs/08-implementation-roadmap.md` (selaras dengan CLAUDE.md §38). Gunakan tabel pemetaan
> di bawah bila sebuah instruksi menyebut "Phase X".

| Tahap konseptual (dokumen ini) | PHASE pada `docs/08` |
|---|---|
| Phase 0 — Foundation | PHASE 0–1 |
| Phase 1 — Backend foundation | PHASE 2, 4, 5 |
| Phase 2 — Core dashboard | PHASE 6–7 |
| Phase 3 — GIS | PHASE 8 |
| Phase 4 — Analytics | PHASE 9 |
| Phase 5 — Risk & prediction | PHASE 10 |
| Phase 6 — Warning & recommendation | PHASE 11–13 |
| Phase 7 — Evaluation | PHASE 15 |
| Phase 8 — Delivery | PHASE 16 |
| *(tidak ada padanan di sini)* | PHASE 14 — Operation Center |

## Phase 0 — Foundation
- repository
- CLAUDE.md
- documentation
- architecture
- environment setup
- Git

## Phase 1 — Backend foundation
- database
- migrations
- models
- API structure
- authentication
- RBAC

## Phase 2 — Core dashboard
- layout
- navigation
- dashboard cards
- charts
- activity feed

## Phase 3 — GIS
- map
- incident points
- boundaries
- historical heatmap

## Phase 4 — Analytics
- trends
- day-hour matrix
- Crime Pattern DNA

## Phase 5 — Risk & prediction
- risk engine
- prediction interface
- predictive heatmap
- explainability

## Phase 6 — Warning & recommendation
- early warning
- recommendation
- commander approval

## Phase 7 — Evaluation
- prediction vs actual
- metrics
- evaluation dashboard

## Phase 8 — Delivery
- executive brief
- hardening
- testing
- documentation
- demonstration

Android is a subsequent client/application phase.

---

# 17. DEFINITION OF DONE

A feature is not complete merely because code exists.

For a meaningful feature:
- requirements are documented;
- UI exists where applicable;
- API works;
- authorization is enforced;
- validation exists;
- errors are handled;
- tests exist where appropriate;
- no secrets are committed;
- relevant audit events are recorded;
- documentation is updated;
- application runs successfully.

---

# 18. CLAUDE WORKING PROTOCOL

When asked to implement something:

1. Read relevant docs.
2. Explain what you understand.
3. Identify dependencies.
4. Propose a small plan.
5. Implement only that scope.
6. Run tests/checks.
7. Report files changed.
8. Report validation performed.
9. Report remaining risks/TODOs.

Never silently expand scope.

---

# 19. OPEN ITEMS — STATUS AFTER PHASE 0

Status setelah audit TASK 000 dan penyelesaian keputusan teknis.
Rincian: `docs/implementation-notes/000c-specification-lock.md`.

## 19.1 Sudah ditetapkan sebagai keputusan teknis (`TECHNICAL DECISION`)

| Item | Ditetapkan di |
|---|---|
| Nama field dan tipe data | `docs/02` |
| Data dictionary | `docs/02` |
| Kontrak API (bentuk, error, pagination, auth, permission per endpoint) | `docs/05` |
| Katalog permission dan model scope | `docs/03` §2 |
| Struktur repository, toolchain, migration | `docs/07`, `docs/06` §1 |
| Representasi false negative untuk evaluasi | `docs/02` §15, `docs/06` §3 |
| Penanganan waktu, timezone, dan waktu acuan demo | `docs/02` K-3, `docs/08` PHASE 3 |

## 19.2 Masih menunggu pemilik proyek / data owner (`NOT SPECIFIED`)

### Sudah ditetapkan

| Item | Ditetapkan | Nilai yang berlaku |
|---|---|---|
| Bobot risk score (U-02) | 9 September 2026 | `config/risk/risk-weights.yaml` versi `dummy-v1` |
| Threshold early warning & batas kelas risiko (U-01) | 9 September 2026 | `config/risk/warning-thresholds.yaml` versi `dummy-v1` |
| Pemetaan status wilayah Aman/Waspada/Siaga (U-22) | 9 September 2026 | `leadership_display.area_status`, Siaga = HIGH + CRITICAL |
| Taksonomi nilai (U-16) | 9 September 2026 | `config/taxonomy/mappings.yaml` versi `taksonomi-2026-09-01`, 20 domain |
| Prediksi tanpa kelas risiko | 9 September 2026 | Prediksi tetap skor mentah; tangga kelas hanya bagi penilaian keadaan berjalan |

Seluruhnya ditetapkan **memakai nilai yang sudah berlaku**, tanpa satu angka pun berubah,
sehingga baris yang sudah tersimpan tetap sah dan tetap tertelusur. Ditetapkan berarti
berlaku sebagai ketentuan — **bukan** berarti terbukti tepat; itu urusan evaluasi
(CLAUDE.md §18).

### Masih terbuka

Butir berikut **tidak diinvensi** dan memblokir task tertentu:

| Item | Memblokir |
|---|---|
| Kewenangan & kriteria publikasi alert publik (U-10 / P-2) | TASK 111 — saat ini **tidak satu peran pun** memegang `public_alert:publish` |
| Definisi target prediksi & aturan pencocokan evaluasi (U-03) | TASK 100–104, 150–151 |
| Ambang peringkat volume laporan (0,70 / 0,40) | Layar Pimpinan — dipisahkan dari U-22 pada 9 September 2026 |
| Ukuran grid & batas GIS resmi (U-04) | TASK 011, 080–084 |
| Matriks role-permission resmi + kewenangan approve (U-06, P-1…P-7) | TASK 051, 130 |
| Kebijakan kredensial (panjang/rotasi password, MFA, SSO) (U-05) | TASK 050 |
| Alur operasional resmi & state machine (U-08) | TASK 110–142 |
| Sumber konten Executive Brief (U-11) | modul MVP #12 |
| Identitas pelapor, bukti, dan status LAPOR PRESISI (U-13) | PHASE 17 |
| Lingkungan produksi & sumber tile produksi (sisa U-15 — pengembangan sudah diputuskan: tile lokal) | PHASE 16 |
| Retensi & klasifikasi data (U-14) | TASK 162–163 |
| Sumber data eksternal yang disetujui (U-19) | fase analytics/ML |
| SLA, volume data, jumlah pengguna (U-17) | TASK 164 |
| UI screens final | PHASE 6–7 |

---

# 20. FIRST IMPLEMENTATION TARGET

Do not start with advanced AI.

First create a working end-to-end prototype using synthetic data:

1. Login
2. RBAC
3. Dashboard
4. Crime incidents
5. Map
6. Historical heatmap
7. Deterministic/sample risk score
8. Sample prediction
9. Early warning
10. Recommendation
11. Human approval
12. Prediction vs actual

Once this vertical slice works, replace the sample prediction/risk components with
validated analytical/model components.

---

# 21. SOURCE TRACEABILITY

This specification is derived from the supplied PREDIKSI PRESISI documents:
- Resume Spesifikasi Aplikasi PREDIKSI PRESISI
- Concept Presentation / 90-Day Execution Plan
- Resume Taskap — Predictive Policing AI & Geospasial

The source documents establish the product concept, modules, data strategy, architecture,
MVP, governance, and roadmap. This master specification reorganizes those elements into
a software-development baseline; it does not establish final model weights, legal policy,
or operational authority that was not specified in the source material.
