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
└── 000-specification-audit.md
```

**STOP setelah selesai.**

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

## TASK 016 — Database Constraints & Index

Tambahkan:
- FK;
- unique constraint;
- score constraint;
- timestamp indexes;
- spatial indexes;
- query indexes yang dibutuhkan.

**Jangan membuat index secara membabi buta.**

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

Acceptance:
Dashboard nantinya dapat berjalan tanpa data resmi.

---

# PHASE 4 — BACKEND API

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

## TASK 052 — Authorization Middleware

Test:
- allowed;
- denied;
- unauthenticated.

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
