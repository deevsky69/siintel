# DATABASE SCHEMA IMPLEMENTATION GUIDE

Baseline: **PostgreSQL + PostGIS**.
Definisi field: `docs/02-data-dictionary.md`. Relasi: `docs/04-erd.md`.

---

## 1. TOOLING

`TECHNICAL DECISION` (SDL-05):

| Kebutuhan | Keputusan |
|---|---|
| ORM | SQLAlchemy 2.x |
| Geospasial | GeoAlchemy2 (`geometry(Point,4326)`) |
| Migration | Alembic — **satu-satunya** cara mengubah schema (CLAUDE.md §20) |
| Ekstensi wajib | `postgis`, `pgcrypto` (untuk `gen_random_uuid()`) |

Migration harus reproducible dari database kosong. Tidak ada perubahan manual pada database sebagai bagian workflow normal.

---

## 2. CLOSED LOOP

```text
DATA
 ↓
ANALYSIS ──────────────► RISK SCORES (layer risiko berjalan)
 ↓
PREDICTION (risk_score + confidence + WHY)
 ↓
EARLY WARNING
 ↓
RECOMMENDATION
 ↓
COMMANDER DECISION
 ↓
OPERATIONAL ACTION
 ↓
ACTUAL RESULT
 ↓
EVALUATION (precision, recall, FP, FN)
 ↓
MODEL UPDATE
```

`risk_scores` adalah cabang layer, bukan tahap antara prediction dan warning (docs/04).

---

## 3. CONSTRAINT

### Foreign key

```text
crime_incidents.location_id        → locations
intelligence_reports.location_id   → locations
patrol_activity.location_id        → locations
patrol_activity.unit_id            → police_units
citizen_reports.location_id        → locations            (nullable)
community_feedback.report_id       → citizen_reports
risk_scores.location_id            → locations
predictions.location_id            → locations
predictions.baseline_risk_score_id → risk_scores          (nullable)
early_warnings.prediction_id       → predictions
early_warnings.location_id         → locations
early_warnings.acknowledged_by     → users                (nullable)
early_warnings.resolved_by         → users                (nullable)
public_alerts.warning_id           → early_warnings       (nullable)
recommendations.prediction_id      → predictions
recommendations.warning_id         → early_warnings       (nullable)
commander_decisions.recommendation_id → recommendations
commander_decisions.decision_by    → users                (NOT NULL)
operational_actions.decision_id    → commander_decisions
operational_actions.unit_id        → police_units
operational_actions.location_id    → locations
operational_actions.created_by     → users
prediction_actual.prediction_id    → predictions          (nullable — false negative)
prediction_actual.actual_incident_id → crime_incidents    (nullable)
prediction_actual.actual_location_id → locations          (nullable)
users.role_id                      → roles
role_permissions.role_id           → roles
role_permissions.permission_id     → permissions
audit_logs.user_id                 → users                (nullable — system event)
```

`ON DELETE`: seluruh FK memakai `RESTRICT` kecuali `role_permissions` (`CASCADE` mengikuti role/permission). Data operasional tidak dihapus; gunakan status.

### Unique

- `locations.code`, `locations.grid_id`
- `users.username`, `users.code`
- `permissions(resource, action)`
- `role_permissions(role_id, permission_id)`
- kolom `code` pada setiap entitas yang memilikinya
- `risk_scores(location_id, threat_type, window_start, assessment_date)`
- `predictions(location_id, threat_type, window_start, forecast_horizon, model_version, prediction_date)`

### Check

```sql
risk_score      BETWEEN 0 AND 100
confidence      BETWEEN 0 AND 100
urgency_score, verification_score, urgency BETWEEN 0 AND 100
historical_factor, recent_trend_factor, temporal_factor,
spatial_factor, context_factor            BETWEEN 0 AND 100
window_end > window_start
roles.level     BETWEEN 1 AND 6
```

Aturan bersyarat pada `prediction_actual` (CLAUDE.md §26):

```sql
CHECK (
  (match_type IN ('HIT','FALSE_POSITIVE') AND prediction_id IS NOT NULL)
  OR
  (match_type = 'FALSE_NEGATIVE' AND prediction_id IS NULL AND actual_incident_id IS NOT NULL)
)
```

`operational_actions` hanya boleh menunjuk keputusan `APPROVED`/`MODIFIED` — ditegakkan di service layer dan diuji (constraint lintas tabel tidak dipaksakan di database agar tetap sederhana).

### Constraint yang SENGAJA DITUNDA

| Constraint | Alasan |
|---|---|
| `risk_score = round(Σ(bobot × faktor))` | Bobot belum ditetapkan (U-02). Memasang constraint sekarang berarti mengunci angka yang belum disetujui (CLAUDE.md §11). Dipasang setelah bobot disetujui. |
| Batas `risk_class` terhadap `risk_score` | Threshold belum ditetapkan (U-01). Sampai itu, `risk_class` divalidasi terhadap daftar nilai saja. |
| Geometri poligon per grid | Ukuran grid & sumber batas belum ditetapkan (U-04). |

---

## 4. INDEX

Dibuat hanya yang jelas diperlukan (CLAUDE.md §37, docs/08 TASK 016):

```text
crime_incidents  (occurred_at), (location_id, occurred_at), (incident_type)
risk_scores      (assessment_date), (location_id, window_start)
predictions      (prediction_date), (location_id, window_start), (status)
early_warnings   (status, created_at), (location_id)
recommendations  (status), (prediction_id)
audit_logs       (timestamp), (user_id, timestamp), (resource_type, resource_id)
locations        GIST (geom)
crime_incidents  GIST (geom) — jika kolom geom titik kejadian dipakai
```

Index tambahan hanya ditambahkan bila ada query nyata yang membutuhkannya.

---

## 5. TIMEZONE

Seluruh kolom waktu memakai `timestamptz` (UTC). Konversi ke WIB dilakukan pada lapisan tampilan (`APP_TIMEZONE`).
Jendela waktu memakai interval half-open `[window_start, window_end)`.

---

## 6. BELUM FINAL — JANGAN DIKUNCI

Jangan mengarang atau mengunci di schema maupun kode:

- bobot risk score (U-02);
- threshold warning & batas kelas risiko (U-01);
- algoritma ML;
- taksonomi final (U-16);
- ukuran grid & batas wilayah (U-04);
- retensi data (U-14);
- SLA;
- integrasi eksternal (U-19).

Nilai yang dapat dikonfigurasi berada di `config/risk/`, `config/model/`, dan `config/taxonomy/`; versinya dicatat pada baris data (`weights_version`, `threshold_version`, `model_version`) agar hasil dapat direproduksi.
