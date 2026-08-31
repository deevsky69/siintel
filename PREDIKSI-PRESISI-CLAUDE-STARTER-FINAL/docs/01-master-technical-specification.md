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

Target pipeline:

RAW
→ CLEAN
→ VALIDATE
→ ANONYMIZE
→ GEO / GRID
→ FEATURE ENGINEERING
→ ANALYSIS
→ MODEL
→ PREDICTION
→ VALIDATION
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
MapLibre GL JS or approved GIS alternative

Version control:
Git

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

Exact endpoints, schemas, authentication, pagination, filtering, and error contracts
must be defined in docs/05-api-design.md before large-scale implementation.

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

---

# 16. DEVELOPMENT PHASES

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

# 19. OPEN ITEMS BEFORE FULL IMPLEMENTATION

The following must be finalized from the project owner/data owner:

- final field names and data types
- exact data dictionary
- final risk formula/weights
- early warning thresholds
- prediction target definition
- grid size
- exact GIS boundaries
- final role-permission matrix
- exact operational workflows
- final API contracts
- final UI screens
- model evaluation methodology
- deployment environment
- data retention policy
- approved external data sources

These are intentionally not invented in this specification.

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
