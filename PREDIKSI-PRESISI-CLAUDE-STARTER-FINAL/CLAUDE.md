# PREDIKSI PRESISI — Claude Project Instructions

## 1. Project Identity
PREDIKSI PRESISI is a Predictive Policing & Spatial Intelligence System intended as a
decision-support platform for early detection of Kamtibmas vulnerabilities.

Core principle:
DATA → ANALYSIS → PREDICTION → EARLY WARNING → RECOMMENDATION → DECISION → ACTION → EVALUATION

## 2. Non-Negotiable Principles
1. AI output is NOT a police decision.
2. Every operational recommendation requires human review and authorization.
3. The prediction unit is area + time, not an individual.
4. Use anonymized/synthetic data during development unless explicitly authorized otherwise.
5. Minimize sensitive personal data.
6. Important actions must be auditable.
7. Do not introduce autonomous operational deployment.
8. Do not invent business rules that are not documented.
9. Do not change database schema, API contracts, or architecture silently.
10. Preserve explainability: every prediction/risk result should expose the factors used where technically possible.

## 3. Development Behavior
Before coding:
- inspect the repository;
- read this file;
- read the relevant files under /docs;
- state your understanding and identify ambiguities;
- propose a small implementation plan.

While coding:
- make small, reviewable changes;
- follow the existing architecture;
- validate inputs;
- handle errors explicitly;
- add/update tests for meaningful behavior;
- do not rewrite unrelated files.

After coding:
- run relevant tests/lint/type checks;
- summarize files changed;
- summarize tests performed;
- list remaining risks or TODOs.

## 4. Scope Control
The current MVP focuses on:
- Login + RBAC
- Executive Dashboard
- Live Crime Map
- Historical Heatmap
- Predictive Heatmap
- AI Risk Scoring
- Prediction Center
- Early Warning
- AI Recommendation
- Crime Analytics
- Prediction vs Actual Evaluation
- Executive Brief

Advanced integrations such as real-time CCTV/sensor integration, advanced NLP,
and large-scale institutional integration are roadmap items, not MVP requirements.

## 5. Suggested Technical Direction
Use a modular-monolith architecture unless the technical lead explicitly changes it.

Initial direction:
- Frontend: Next.js + TypeScript
- UI: Tailwind CSS + shadcn/ui
- Backend/API: Python + FastAPI
- Database: PostgreSQL + PostGIS
- Analytics/ML: Python ecosystem
- Map: MapLibre GL JS or another approved GIS library
- Git for version control

Do not install or add dependencies merely because they are fashionable. Explain why a dependency is needed.

## 6. AI/ML Rules
Do not claim that the system "predicts crime with certainty."
Use language such as:
- estimated risk
- relative risk
- predicted hotspot
- confidence
- dominant factors

Model evaluation must include, where applicable:
precision, recall, false positive, false negative, and prediction-vs-actual analysis.

Do not use individual characteristics as a prediction target.

## 7. Security
Never hard-code:
- passwords
- API keys
- tokens
- database credentials
- secrets

Use environment variables/secrets management.

Important operations should produce audit logs.

## 8. UI
Treat design reference files in /design as visual references.
Do not replace the approved visual language without discussion.

The UI should communicate:
- situation
- risk
- location
- time window
- prediction
- confidence
- explanation
- warning
- recommendation
- human decision

## 9. Working Rule for Ambiguity
If a requirement is unclear and the ambiguity can materially affect data, security,
architecture, or user workflow:
STOP and ask/flag the ambiguity before implementing it.

If the ambiguity is cosmetic and low-risk:
choose a reasonable default and document it.

## 10. Never Do This
- Do not expose sensitive internal data in public endpoints.
- Do not let an AI recommendation directly trigger police deployment.
- Do not silently add features outside the MVP.
- Do not delete data to make tests pass.
- Do not bypass authentication/authorization for convenience.
- Do not fabricate model accuracy.
