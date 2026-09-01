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
| Penamaan constraint | Naming convention pada `Base.metadata` (lihat §1.2) |

### 1.2 Naming convention

`TECHNICAL DECISION` — nama constraint dibuat deterministik agar model dan migration tidak pernah
memakai nama berbeda untuk objek yang sama, dan agar `alembic revision --autogenerate` konsisten:

```python
{
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}
```

Karena `ck` **menyusun** nama dari `constraint_name`, `CheckConstraint` ditulis dengan nama pendek
(`name="confidence_range"`) baik di model maupun di migration; prefix `ck_<tabel>_` ditambahkan
otomatis. Menulis nama lengkap akan menghasilkan prefix ganda.
Nama index ditulis eksplisit karena sebagian index gabungan tidak mengikuti pola kolom.

Migration harus reproducible dari database kosong. Tidak ada perubahan manual pada database sebagai bagian workflow normal.

## 1.1 Letak dan perintah migration (TASK 010)

| Berkas | Peran |
|---|---|
| `apps/api/alembic.ini` | Konfigurasi Alembic. **Tidak memuat URL database.** |
| `database/migrations/env.py` | Membaca `DATABASE_URL` dari environment (CLAUDE.md §28) |
| `database/migrations/versions/` | Berkas migration |
| `apps/api/src/prediksi_presisi_api/db.py` | Engine, session factory, dan `Base` untuk model |

```bash
pnpm db:up         # jalankan PostGIS lewat docker compose
pnpm db:migrate    # alembic upgrade head
pnpm db:current    # revisi yang sedang terpasang
pnpm db:history    # rangkaian migration
pnpm db:sql        # render SQL tanpa menyentuh database (mode offline)
pnpm db:rollback   # alembic downgrade -1
```

Baseline `0001` hanya mengaktifkan ekstensi `postgis` dan `pgcrypto`; belum ada tabel.
Tabel inti dibuat mulai TASK 011. Engine dibuat secara *lazy* sehingga mengimpor modul aplikasi
tidak membuka koneksi — test dan build tidak memerlukan database yang hidup.

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

### Trigger — invarian human-in-the-loop

`operational_actions` hanya boleh menunjuk keputusan `APPROVED`/`MODIFIED`.

Aturan ini **ditegakkan di database** lewat trigger
`trg_operational_actions_require_approved_decision` (migration `0006`), bukan hanya di
lapisan aplikasi seperti rencana semula.

Alasan perubahan: ini invarian inti produk — jaminan bahwa AI tidak pernah langsung
memerintahkan tindakan operasional (CLAUDE.md §13). Aturan sepenting itu tidak boleh bergantung
pada satu jalur kode; script seed, perbaikan data manual, atau endpoint baru bisa melewatinya.
CHECK constraint tidak dapat dipakai karena tidak boleh merujuk tabel lain, sehingga trigger
adalah satu-satunya cara deklaratif di PostgreSQL.

Trigger ini adalah **pengecualian yang disengaja** terhadap prinsip "business rule berada di
service layer". Aturan bisnis lain tetap di service layer.

### Constraint yang SENGAJA DITUNDA

| Constraint | Alasan |
|---|---|
| `risk_score = round(Σ(bobot × faktor))` | Bobot belum ditetapkan (U-02). Memasang constraint sekarang berarti mengunci angka yang belum disetujui (CLAUDE.md §11). Dipasang setelah bobot disetujui. |
| Batas `risk_class` terhadap `risk_score` | Threshold belum ditetapkan (U-01). Sampai itu, `risk_class` divalidasi terhadap daftar nilai saja. |
| Geometri poligon per grid | Ukuran grid & sumber batas belum ditetapkan (U-04). |
| ~~`public_alerts.warning_id → early_warnings`~~ | **Lunas** pada migration `0005` (TASK 013), setelah tabel `early_warnings` ada. |

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
