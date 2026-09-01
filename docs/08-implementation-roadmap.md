# IMPLEMENTATION ROADMAP — PREDIKSI PRESISI

Dokumen ini menjadi urutan pengerjaan proyek bersama Claude.

## Prinsip

Satu task = satu perubahan terukur.

Setelah setiap task:
1. jalankan test;
2. jalankan aplikasi;
3. periksa hasil;
4. commit perubahan;
5. baru lanjut task berikutnya.

---

# PHASE 0 — AUDIT & LOCK SPECIFICATION

## TASK 000 — Specification Audit

Tujuan:
- membaca seluruh dokumen;
- memeriksa konflik;
- membuat daftar keputusan yang belum ditentukan;
- tidak coding.

Output:
```text
docs/implementation-notes/
├── 000-specification-audit.md          # temuan audit
├── 000b-specification-decision-log.md  # jawaban gate + decision log
└── 000c-specification-lock.md          # status kunci spesifikasi + blocker
```

**STATUS: SELESAI.** Keputusan teknis sudah diambil dan dokumen `docs/01`–`docs/07` diperbarui.
Butir yang masih menunggu keputusan pengguna terdaftar pada `000c-specification-lock.md` —
butir tersebut memblokir task tertentu, bukan seluruh roadmap.

**Penomoran fase:** dokumen ini adalah penomoran kanonik (selaras dengan CLAUDE.md §38).
`docs/01` §16 memakai tahapan konseptual Phase 0–8 dengan tabel pemetaan ke PHASE di sini.

---

# PHASE 1 — PROJECT BOOTSTRAP

## TASK 001 — Initialize Repository

Claude:
- membaca `CLAUDE.md`;
- membaca project structure;
- memilih/menjalankan stack yang sudah disepakati;
- membuat skeleton aplikasi;
- tidak membuat feature bisnis.

Acceptance:
- project dapat dijalankan;
- folder sesuai structure;
- environment example tersedia.

## TASK 002 — Development Environment

Buat:
- local development configuration;
- database connection placeholder;
- lint;
- formatter;
- test runner.

Acceptance:
```text
install
run
lint
test
```
berhasil.

---

# PHASE 2 — DATABASE

## URUTAN EKSEKUSI PHASE 2

`TECHNICAL DECISION` (2026-09-01, atas persetujuan pemilik proyek untuk memperbaiki alur task).
Nomor task **tidak berubah**, hanya urutan pengerjaannya:

```text
010  PostgreSQL/PostGIS + Alembic
 ↓
011  Tabel inti
 ↓
012  Tabel publik
 ↓
015  Tabel administrasi        ← dinaikkan
 ↓
013  Tabel intelijen
 ↓
014  Tabel operasional
 ↓
016  Constraint & index
```

Alasan: `early_warnings` (013) memerlukan FK ke `users` untuk `acknowledged_by`/`resolved_by`,
dan `commander_decisions.decision_by`, `operational_actions.created_by`, serta `audit_logs.user_id`
(014, 015) juga. Bila `users` dibuat terakhir, empat foreign key harus ditunda dan dipasang lewat
migration susulan — pola yang sudah terlanjur terjadi pada `public_alerts.warning_id`.
Dengan menaikkan TASK 015, seluruh FK dapat dipasang langsung.

## TASK 010 — PostgreSQL/PostGIS

Tujuan:
- database development;
- PostGIS;
- migration system.

Acceptance:
- database dapat dibuat;
- migration dapat dijalankan dari kondisi kosong.

## TASK 011 — Core Tables

Implement:
```text
locations
police_units
crime_incidents
intelligence_reports
patrol_activity
```

Gunakan data dictionary.

## TASK 012 — Public Tables

Implement:
```text
citizen_reports
public_alerts
community_feedback
```

## TASK 013 — Intelligence Tables

Implement:
```text
risk_scores
predictions
early_warnings
recommendations
```

## TASK 014 — Operational Tables

Implement:
```text
commander_decisions
operational_actions
prediction_actual
```

## TASK 015 — Administration

Implement:
```text
users
roles
permissions
role_permissions
audit_logs
```

Catatan hasil PHASE 0:
- `users` memuat `password_hash`, `polsek`, `function`, `last_login_at`, `must_change_password` (docs/02 §17);
- `role_permissions` memuat kolom `scope` (`ALL`/`OWN_JURISDICTION`/`OWN_FUNCTION`);
- `audit_logs.result` memakai enum `SUCCESS`/`DENIED`/`FAILED` dan bersifat append-only.

## TASK 016 — Database Constraints & Index

Tambahkan:
- FK;
- unique constraint;
- score constraint;
- timestamp indexes;
- spatial indexes;
- query indexes yang dibutuhkan.

**Jangan membuat index secara membabi buta.**

Constraint yang **sengaja ditunda** (docs/06 §3): hubungan `risk_score` dengan bobot faktor, dan batas
`risk_class` terhadap `risk_score` — keduanya menunggu bobot/threshold disetujui (U-01, U-02).
Constraint bersyarat `prediction_actual` (HIT/FALSE_POSITIVE wajib `prediction_id`;
FALSE_NEGATIVE wajib `actual_incident_id`) **dipasang** pada task ini.

---

# PHASE 3 — DUMMY DATA

## TASK 020 — Seed Master Data

Load:
- lokasi/grid;
- police units;
- roles;
- permissions.

## TASK 021 — Seed Crime Data

Load dummy:
- crime incidents;
- intelligence reports;
- patrol activity.

## TASK 022 — Seed Prediction Data

Load:
- risk scores;
- predictions;
- early warnings;
- recommendations.

## TASK 023 — Seed Operational Data

Load:
- commander decisions;
- operational actions;
- prediction actual.

## TASK 024 — Seed Public & Administration Data

Load:
- users (password hash dibuat saat seed, tidak pernah ada di CSV);
- role_permissions (+ kolom `scope`);
- citizen reports;
- public alerts;
- community feedback;
- audit logs.

Task ini ditambahkan karena keenam tabel tersebut tidak tercakup TASK 020–023,
padahal tabelnya dibuat pada TASK 015 dan datanya tersedia di `data/sample/`.

---

## ACCEPTANCE CRITERIA PHASE 3 — KUALITAS DATA DUMMY

Dasar: CLAUDE.md §17 (dummy data wajib punya FK valid, tanggal masuk akal, relasi valid).
Perbaikan dilakukan pada **generator/seed script** (`scripts/seed/`, `scripts/validation/`), bukan dengan menyunting CSV satu per satu.

Seed **gagal (fail-fast)** bila salah satu tidak terpenuhi — tidak boleh ada koersi diam-diam:

| # | Kriteria | Temuan audit yang ditutup |
|---|---|---|
| A-1 | 0 orphan foreign key. `commander_decisions.decision_by` harus menunjuk user yang ada (dataset memakai `USER-DEMO-PIMPINAN` yang tidak terdaftar pada 63/63 baris). | S-01 |
| A-2 | Setiap `grid_id` pada CSV terpetakan ke `locations.location_id`. | C-02 |
| A-3 | Untuk setiap baris `risk_scores`: `risk_score = round(Σ(bobot × faktor))` memakai bobot dari `config/risk/`. Dataset saat ini menyimpang pada 1.822 dari 1.848 baris. | S-04 |
| A-4 | `predictions.forecast_horizon` mencakup kelima horizon `6H,12H,24H,3D,7D` (dataset saat ini hanya `24h`). | S-06 |
| A-5 | `dominant_factors` berbentuk `jsonb` per baris dengan `source` (`RULE`/`MODEL`); tidak boleh satu kalimat identik untuk seluruh prediksi (saat ini identik pada 180/180). | S-07 |
| A-6 | Setiap prediksi memiliki `risk_scores` pendamping pada lokasi/ancaman/jendela yang sama untuk tanggal penilaian sebelumnya (koherensi demo, bukan FK). | S-05 |
| A-7 | `prediction_actual` hanya mengevaluasi prediksi `PUBLISHED`/`VALIDATED`, dan **memuat baris `FALSE_NEGATIVE`** sehingga recall dapat dihitung. | S-08, S-09 |
| A-8 | Setiap keputusan `APPROVED`/`MODIFIED` memiliki `operational_actions` (saat ini 3 action untuk 33 keputusan approved). | S-10 |
| A-9 | Setiap baris `audit_logs` memakai pasangan `action`/`resource_type` yang sah, dan pelakunya benar-benar memiliki permission tersebut. Dataset saat ini memuat ±190 baris `SUCCESS` untuk aksi yang rolenya tidak berwenang. | S-02, S-03 |
| A-10 | `audit_logs` memuat minimal satu kasus `DENIED` per role agar pengujian RBAC punya data. | S-03 |
| A-11 | Seluruh timestamp ternormalisasi ke `timestamptz`; importer menerima format `T` maupun spasi. | S-14 |
| A-12 | Enum tersimpan mengikuti pemetaan `config/taxonomy/` (docs/02 §22). | C-13 |

**Waktu data demo (`TECHNICAL DECISION`, SDL-16).** Dataset berhenti 2025-12-31.
Tanggal historis **tidak digeser**, karena akan merusak split training 2023–2024 / validasi Jan–Sep 2025 / holdout Okt–Des 2025 (`docs/01` §8).
Sebagai gantinya aplikasi memakai **waktu acuan** (`DEMO_REFERENCE_TIME`); bila diisi, "24 jam terakhir" dan "warning aktif" dihitung relatif terhadapnya.

Acceptance akhir Phase 3: dashboard dapat berjalan tanpa data resmi.

---

# PHASE 4 — BACKEND API

## URUTAN EKSEKUSI PHASE 4 ↔ PHASE 5

`TECHNICAL DECISION` (SDL-10). Nomor task **tidak berubah**, tetapi urutan pengerjaannya:

```text
030  API foundation
 ↓
050  Authentication
051  Role & permission
052  Authorization middleware
053  Audit logging
 ↓
031 … 040  API domain
```

Alasan: PHASE 4 mensyaratkan setiap endpoint memiliki authorization, sedangkan mekanismenya baru dibuat pada PHASE 5.
CLAUDE.md §21 mewajibkan endpoint sensitif memiliki authorization sejak awal, sehingga API domain tidak boleh lahir tanpa middleware.
Dengan urutan ini, setiap API domain sejak awal dapat diuji untuk kasus **allowed / denied / unauthenticated** (CLAUDE.md §30).
CHECKPOINT C tetap utuh karena memang menggabungkan API + Authentication + RBAC.

## TASK 030 — API Foundation

Buat:
- server;
- config;
- error handling;
- request validation;
- logging;
- health endpoint.

## TASK 031 — Locations API

## TASK 032 — Crime API

## TASK 033 — Intelligence API

## TASK 034 — Patrol API

## TASK 035 — Analytics API

## TASK 036 — Prediction API

## TASK 037 — Warning API

## TASK 038 — Recommendation API

## TASK 039 — Operations API

## TASK 040 — Evaluation API

Setiap endpoint:
- validation;
- authorization;
- test.

---

# PHASE 5 — AUTHENTICATION & RBAC

## TASK 050 — Authentication

Implement:
- login;
- session/token;
- password hashing;
- logout;
- protected endpoint.

## TASK 051 — Role Permission

Implement role:
```text
Pimpinan
Command Center
Analyst
Fungsi
Polsek
Administrator
```

Gunakan katalog permission `resource:action` dan matriks pada `docs/03` §2–§3.
Pemberian permission per role masih `PROPOSED` — jangan diperlakukan sebagai kewenangan resmi
sampai pertanyaan P-1…P-7 (`docs/03` §4) dijawab pemilik proyek.

## TASK 052 — Authorization Middleware

Middleware memeriksa permission **dan** `scope` (jurisdiksi/fungsi) sebelum handler dijalankan.
Resource di luar scope dijawab `404`, bukan `403` (docs/05 §1).

Test:
- allowed;
- denied;
- unauthenticated;
- out-of-scope.

## TASK 053 — Audit Logging

Audit aktivitas sensitif.

---

# PHASE 6 — WEB SHELL

## TASK 060 — Application Layout

Buat:
- login;
- sidebar;
- topbar;
- user menu;
- responsive shell;
- route protection.

Belum membuat seluruh dashboard.

## TASK 061 — Design System

Implement:
- typography;
- spacing;
- cards;
- buttons;
- tables;
- badges;
- alerts;
- modal;
- form;
- map container.

Gunakan desain website yang diberikan pengguna sebagai referensi visual.

---

# PHASE 7 — EXECUTIVE DASHBOARD

## TASK 070 — Executive Dashboard

Tampilkan:
- ringkasan kondisi;
- risk summary;
- prediction summary;
- early warning;
- trend;
- map summary.

Gunakan API.

## TASK 071 — Dashboard Filtering

Filter:
- waktu;
- wilayah;
- threat type;
- risk level.

---

# PHASE 8 — GIS

## TASK 080 — Base Map

Implement map.

## TASK 081 — Historical Heatmap

Gunakan `crime_incidents`.

## TASK 082 — Current Risk Layer

Gunakan `risk_scores`.

## TASK 083 — Predictive Heatmap

Gunakan `predictions`.

## TASK 084 — Map Detail

Klik grid → tampilkan:
```text
WHAT
WHERE
WHEN
RISK
CONFIDENCE
WHY
```

---

# PHASE 9 — ANALYTICS

## TASK 090 — Crime Trend

## TASK 091 — Time Pattern

## TASK 092 — Spatial Pattern

## TASK 093 — Location Profile

## TASK 094 — Crime Pattern DNA

Semua analytics harus dapat ditelusuri kembali ke data sumber.

---

# PHASE 10 — PREDICTIVE PROTOTYPE

## TASK 100 — Feature Dataset

Buat feature pipeline dari data dummy.

## TASK 101 — Baseline Model

Mulai dari baseline sederhana yang dapat dijelaskan.

**Jangan langsung mengejar model kompleks.**

## TASK 102 — Risk Score

Generate risk score.

## TASK 103 — Prediction

Generate:
```text
WHAT
WHERE
WHEN
RISK
CONFIDENCE
WHY
```

## TASK 104 — Model Evaluation

Hitung:
```text
precision
recall
false positive
false negative
```

Simpan `model_version`.

False negative memakai baris `prediction_actual` dengan `match_type = FALSE_NEGATIVE`
(`prediction_id` NULL, `actual_incident_id` terisi) — docs/02 §15, CLAUDE.md §26.

**BLOCKER (U-03):** aturan pencocokan spasial/temporal antara kejadian aktual dan prediksi belum
ditetapkan. Sampai ditetapkan, hasil evaluasi ditandai `PROPOSED` dan tidak boleh disajikan
sebagai validasi model.

---

# PHASE 11 — EARLY WARNING

## TASK 110 — Warning Engine

Gunakan configurable threshold.

## TASK 111 — Warning Center

Dashboard:
- active;
- acknowledged;
- resolved.

## TASK 112 — Warning Explainability

Tampilkan:
- risk;
- confidence;
- factors;
- prediction source.

---

# PHASE 12 — AI RECOMMENDATION

## TASK 120 — Recommendation Engine

Recommendation berdasarkan prediction + context.

## TASK 121 — Recommendation UI

Tampilkan:
```text
Prediction
WHY
Recommendation
Priority
Target Function
```

---

# PHASE 13 — COMMANDER APPROVAL

## TASK 130 — Approval Workflow

```text
Pending
 ↓
Approve
Modify
Reject
```

## TASK 131 — Approval Audit

Catat:
- siapa;
- kapan;
- keputusan;
- alasan.

---

# PHASE 14 — OPERATION CENTER

## TASK 140 — Operational Task

Buat action berdasarkan approved decision.

## TASK 141 — Assignment

Assign:
- unit;
- location;
- start/end;
- status.

## TASK 142 — Result

Masukkan hasil kegiatan.

---

# PHASE 15 — EVALUATION CENTER

## TASK 150 — Prediction vs Actual

Bandingkan prediction dengan actual event.

## TASK 151 — Model Metrics

Dashboard:
```text
Precision
Recall
False Positive
False Negative
```

## TASK 152 — Feedback Loop

Hasil evaluasi menjadi input untuk perbaikan model.

---

# PHASE 16 — HARDENING

## TASK 160 — Security Review

## TASK 161 — API Security

## TASK 162 — Database Security

## TASK 163 — Audit Review

## TASK 164 — Performance

## TASK 165 — E2E Test

---

# PHASE 17 — ANDROID / LAPOR PRESISI

Mobile dibuat setelah core system stabil.

## TASK 170 — Mobile Bootstrap

## TASK 171 — Citizen Report

## TASK 172 — Location

## TASK 173 — Evidence Upload

## TASK 174 — Report Status

## TASK 175 — Feedback

---

# GATE RULE

Claude **tidak boleh melompat fase** jika acceptance criteria fase sebelumnya belum terpenuhi.

Contoh:

Jangan mengerjakan ML sebelum:
```text
database
+
dummy data
+
analytics
```
berjalan.

Jangan mengerjakan mobile sebelum core web/API stabil.

---

# TASK PROMPT TEMPLATE

Gunakan template berikut setiap kali memberi task kepada Claude:

```text
Kerjakan TASK XXX — [NAMA TASK].

Baca terlebih dahulu:
- CLAUDE.md
- dokumen terkait di docs/
- source code yang relevan.

Sebelum coding:
1. jelaskan pemahaman task;
2. sebutkan file yang akan dibuat/diubah;
3. sebutkan risiko atau requirement yang belum jelas.

Kemudian implementasikan task tersebut.

Jangan mengerjakan task berikutnya.

Setelah selesai:
1. jalankan test;
2. jelaskan hasil test;
3. jelaskan file yang berubah;
4. jelaskan command untuk menjalankan;
5. sebutkan masalah yang tersisa.

STOP.
```

---

# CHECKPOINT

Checkpoint penting:

```text
CHECKPOINT A
Specification ✓
Project bootstrap ✓

CHECKPOINT B
Database ✓
Dummy data ✓

CHECKPOINT C
API ✓
Authentication ✓
RBAC ✓

CHECKPOINT D
Web shell ✓
Dashboard ✓

CHECKPOINT E
GIS ✓
Analytics ✓

CHECKPOINT F
Prediction ✓
Evaluation ✓

CHECKPOINT G
Warning ✓
Recommendation ✓
Commander ✓
Operations ✓

CHECKPOINT H
Security ✓
E2E ✓

CHECKPOINT I
Mobile ✓
```

Setelah setiap checkpoint, buat Git commit/tag.
