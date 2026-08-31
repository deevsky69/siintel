# API DESIGN — PREDIKSI PRESISI

> Status: **Konvensi & bentuk kontrak = `TECHNICAL DECISION`.**
> Skema payload rinci per endpoint ditetapkan pada TASK 030–040 bersama implementasi dan OpenAPI.
> Aturan kewenangan yang bersifat organisasi masih `PROPOSED` (lihat docs/03 §4).

Kontrak ini menjadi batas antara web frontend, backend, dan aplikasi Android di kemudian hari.
Klien tidak pernah mengakses database secara langsung (CLAUDE.md §8).

---

## 1. KONVENSI

| # | Ketentuan |
|---|---|
| 1 | REST + JSON. Base path berversi: **`/api/v1`**. Perubahan tidak kompatibel menaikkan versi (CLAUDE.md §22). |
| 2 | Waktu pada payload: ISO-8601 dengan offset (`2025-12-26T18:00:00+07:00`). Penyimpanan UTC (docs/02 K-3). |
| 3 | Penamaan field: `snake_case`. Nilai enum: `UPPER_SNAKE` (docs/02 K-7). |
| 4 | Otorisasi selalu di server. Setiap endpoint mencantumkan permission yang dibutuhkan. |
| 5 | Semua input divalidasi; data dari klien tidak dipercaya. |
| 6 | Endpoint daftar wajib mendukung pagination, filter, dan sort. |
| 7 | Sumber kebenaran skema: OpenAPI yang digenerate backend; tipe TypeScript frontend digenerate dari sana (docs/07). |

### Autentikasi

`TECHNICAL DECISION` (SDL-06):

- `POST /api/v1/auth/login` mengembalikan **access token (JWT, umur pendek)** pada body dan **refresh token** pada cookie `httpOnly; Secure; SameSite=Lax`.
- Permintaan terproteksi memakai header `Authorization: Bearer <access_token>`.
- `POST /api/v1/auth/refresh` menukar refresh token dengan access token baru.
- Password di-hash Argon2id. Frontend tidak pernah menyimpan secret.

> `NOT SPECIFIED` (U-05): umur token, kebijakan password, MFA, ketersediaan SSO Polri. Nilai pada `.env.example` adalah default pengembangan.

### Format daftar & pagination

```json
{
  "data": [ ... ],
  "pagination": { "page": 1, "page_size": 50, "total_items": 1200, "total_pages": 24 }
}
```

Query standar: `page`, `page_size` (default 50, maks 200), `sort` (mis. `-occurred_at`),
`date_from`, `date_to`, `location_id`, `grid_id`, `polsek`, `kecamatan`, `threat_type`, `status`.

### Format error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Permintaan tidak valid.",
    "details": [ { "field": "date_from", "issue": "must be <= date_to" } ],
    "request_id": "01JD..."
  }
}
```

| HTTP | `code` | Dipakai untuk |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Input tidak valid |
| 401 | `UNAUTHENTICATED` | Token tidak ada/kedaluwarsa |
| 403 | `FORBIDDEN` | Permission/scope tidak mencukupi → audit `DENIED` |
| 404 | `NOT_FOUND` | Resource tidak ada, atau ada tetapi di luar scope pengguna |
| 409 | `CONFLICT` | Transisi status tidak sah (mis. approve rekomendasi yang sudah diputus) |
| 422 | `BUSINESS_RULE_VIOLATION` | Aturan bisnis dilanggar |
| 429 | `RATE_LIMITED` | Melebihi batas permintaan |
| 500 | `INTERNAL_ERROR` | Kesalahan tak terduga (detail tidak dibocorkan) |

`TECHNICAL DECISION`: resource di luar scope pengguna dijawab **404**, bukan 403, agar keberadaan data di wilayah lain tidak bocor.

### Scope

Endpoint daftar otomatis difilter sesuai `scope` pada `role_permissions` (`ALL` / `OWN_JURISDICTION` / `OWN_FUNCTION`). Klien tidak dapat melewati filter ini dengan parameter query.

---

## 2. KELOMPOK ENDPOINT

Kolom **Permission** merujuk katalog `docs/03` §2. Semua endpoint memerlukan autentikasi kecuali `login`.

### 2.1 Authentication

| Method | Path | Permission | Audit |
|---|---|---|---|
| POST | `/auth/login` | — | `LOGIN` |
| POST | `/auth/refresh` | — | — |
| POST | `/auth/logout` | terautentikasi | `LOGOUT` |
| GET | `/auth/me` | terautentikasi | — |

`/auth/me` mengembalikan profil, role, daftar permission efektif, dan scope — dipakai frontend hanya untuk tampilan, bukan sebagai penentu izin.

### 2.2 Administrasi

| Method | Path | Permission |
|---|---|---|
| GET/POST | `/users`, `/users/{id}` | `user:read` / `user:manage` |
| PATCH | `/users/{id}` | `user:manage` |
| GET | `/roles`, `/roles/{id}` | `role:read` |
| PUT | `/roles/{id}/permissions` | `role:manage` |
| GET | `/permissions` | `role:read` |
| GET | `/audit-logs` | `audit:read` |
| GET/PUT | `/config/risk-weights`, `/config/warning-thresholds`, `/config/taxonomy` | `config:read` / `config:manage` |

Audit: `CREATE_USER`, `UPDATE_USER`, `CHANGE_ROLE_PERMISSION`, `CHANGE_CONFIGURATION` (menyimpan nilai sebelum/sesudah pada `detail`).
Tidak ada endpoint tulis/hapus untuk `/audit-logs`.

### 2.3 Data Kamtibmas

| Method | Path | Permission |
|---|---|---|
| GET | `/locations`, `/locations/{id}` | `location:read` |
| POST/PATCH | `/locations`, `/locations/{id}` | `location:write` |
| GET | `/crimes`, `/crimes/{id}` | `crime:read` |
| POST/PATCH | `/crimes`, `/crimes/{id}` | `crime:write` |
| GET | `/crimes/export` | `crime:export` |
| GET/POST | `/intelligence-reports` | `intelligence:read` / `intelligence:write` |
| GET/POST | `/patrol-activities` | `patrol:read` / `patrol:write` |
| GET/POST | `/police-units` | `police_unit:read` / `police_unit:write` |

Audit: `VIEW_SENSITIVE_DATA` untuk detail kejadian, `IMPORT_DATA` untuk impor.

### 2.4 Peta

| Method | Path | Permission | Keterangan |
|---|---|---|---|
| GET | `/map/incidents` | `map:read` | Titik kejadian (GeoJSON) |
| GET | `/map/historical-heatmap` | `map:read` | Agregasi historis per grid |
| GET | `/map/current-risk` | `map:read`, `risk_score:read` | Layer risiko berjalan |
| GET | `/map/predictive-heatmap` | `map:read`, `prediction:read` | Layer prediktif; parameter `horizon` |
| GET | `/map/grid/{location_id}` | `map:read` | Detail grid: WHAT/WHERE/WHEN/RISK/CONFIDENCE/WHY (TASK 084) |

`/map/current-risk` dan `/map/predictive-heatmap` dipisah karena keduanya layer berbeda (docs/04).

### 2.5 Analitik

| Method | Path | Permission |
|---|---|---|
| GET | `/analytics/trend` | `analytics:read` |
| GET | `/analytics/time-pattern` | `analytics:read` |
| GET | `/analytics/spatial-pattern` | `analytics:read` |
| GET | `/analytics/location-profile/{location_id}` | `analytics:read` |
| GET | `/analytics/crime-pattern-dna` | `analytics:read` |
| GET | `/analytics/export` | `analytics:export` |

Setiap respons analitik menyertakan `source` (rentang data & jumlah baris) agar dapat ditelusuri kembali ke data sumber (TASK 090–094).

### 2.6 Risiko & Prediksi

| Method | Path | Permission |
|---|---|---|
| GET | `/risk-scores`, `/risk-scores/{id}` | `risk_score:read` |
| POST | `/risk-scores/run` | `risk_score:run` |
| GET | `/predictions`, `/predictions/{id}` | `prediction:read` |
| POST | `/predictions/run` | `prediction:run` |
| POST | `/predictions/{id}/publish` | `prediction:publish` |

Respons prediksi memuat `dominant_factors` beserta `source` (`RULE`/`MODEL`) — CLAUDE.md §27.
Audit: `RUN_RISK_SCORING` (resource `risk_score`), `RUN_PREDICTION` (resource `prediction`), `PUBLISH_PREDICTION`.

### 2.7 Early Warning & Alert Publik

| Method | Path | Permission |
|---|---|---|
| GET | `/warnings`, `/warnings/{id}` | `warning:read` |
| POST | `/warnings/{id}/acknowledge` | `warning:acknowledge` |
| POST | `/warnings/{id}/resolve` | `warning:resolve` |
| GET | `/public-alerts` | `public_alert:read` |
| POST | `/public-alerts` | `public_alert:publish` |

`resolve` ditambahkan karena status `RESOLVED` sudah dipakai tetapi sebelumnya tidak punya endpoint.
Audit: `ACK_WARNING`, `RESOLVE_WARNING`, `PUBLISH_PUBLIC_ALERT` (resource sesuai).
> `PROPOSED`: kewenangan `public_alert:publish` menunggu jawaban P-2 (docs/03 §4).

### 2.8 Rekomendasi & Keputusan Komandan

| Method | Path | Permission |
|---|---|---|
| GET | `/recommendations`, `/recommendations/{id}` | `recommendation:read` |
| POST | `/recommendations` | `recommendation:write` |
| GET | `/recommendations/{id}/decisions` | `commander_decision:read` |
| POST | `/recommendations/{id}/decisions` | `commander_decision:approve` |
| GET | `/commander-decisions`, `/commander-decisions/{id}` | `commander_decision:read` |

`TECHNICAL DECISION`: keputusan dibuat lewat **satu** endpoint `POST /recommendations/{id}/decisions` dengan body `{ "decision": "APPROVED" | "MODIFIED" | "REJECTED", "reason": "...", "modified_text": "..." }`, menggantikan tiga endpoint aksi terpisah (`/approve`, `/modify`, `/reject`).
Alasan: keputusan adalah **entitas** (`commander_decisions`), bukan tiga aksi berbeda; satu endpoint membuat validasi, audit, dan aturan transisi berada di satu tempat. `modified_text` wajib ketika `decision = MODIFIED`.
Audit: `APPROVE_RECOMMENDATION` / `MODIFY_RECOMMENDATION` / `REJECT_RECOMMENDATION`, resource `recommendation`.

### 2.9 Operasi

| Method | Path | Permission |
|---|---|---|
| GET | `/operations`, `/operations/{id}` | `operation:read` |
| POST | `/operations` | `operation:write` |
| PATCH | `/operations/{id}` | `operation:write` |
| POST | `/operations/{id}/result` | `operation:write` |

`POST /operations` menolak `decision_id` yang tidak berstatus `APPROVED`/`MODIFIED` → `422 BUSINESS_RULE_VIOLATION`.
Audit: `CREATE_OPERATIONAL_ACTION`, `UPDATE_OPERATIONAL_ACTION`.

### 2.10 Evaluasi

| Method | Path | Permission |
|---|---|---|
| GET | `/evaluation/summary` | `evaluation:read` |
| GET | `/evaluation/prediction-vs-actual` | `evaluation:read` |
| GET | `/evaluation/metrics` | `evaluation:read` |
| POST | `/evaluation/run` | `evaluation:run` |

`/evaluation/metrics` mengembalikan precision, recall, false positive, false negative (CLAUDE.md §26) beserta `model_version`, rentang evaluasi, dan **aturan pencocokan yang dipakai**.
> Selama aturan pencocokan belum ditetapkan (U-03), respons wajib menandai hasil sebagai `PROPOSED` dan tidak boleh disajikan sebagai validasi model final.

### 2.11 Partisipasi Masyarakat

| Method | Path | Permission |
|---|---|---|
| GET | `/citizen-reports`, `/citizen-reports/{id}` | `citizen_report:read` |
| POST | `/citizen-reports` | `citizen_report:write` |
| PATCH | `/citizen-reports/{id}` | `citizen_report:write` |
| GET | `/community-feedback` | `community_feedback:read` |

> `NOT SPECIFIED` (U-13): kanal publik/mobile untuk mengirim laporan, identitas pelapor, lampiran bukti, dan cara pelapor memantau status. Endpoint di atas adalah kanal **internal**; kanal publik menunggu keputusan kebijakan.

### 2.12 Dashboard & Executive Brief

| Method | Path | Permission |
|---|---|---|
| GET | `/dashboard/summary` | `dashboard:read` |
| GET | `/dashboard/trends` | `dashboard:read` |
| GET | `/dashboard/active-warnings` | `dashboard:read`, `warning:read` |

> `NOT SPECIFIED` (U-11): sumber konten **Executive Brief**. Belum ada entitas, penyedia, maupun task di roadmap. Endpoint `/executive-brief` **tidak didefinisikan** sampai diputuskan apakah kontennya dihasilkan template rule atau model bahasa (keputusan bisnis + kebijakan).

### 2.13 Sistem

| Method | Path | Permission |
|---|---|---|
| GET | `/health` | — |
| GET | `/openapi.json` | — (non-produksi) |

---

## 3. KEAMANAN

- Rate limiting pada `/auth/login` dan endpoint `run`/`export` (CLAUDE.md §28).
- Secure headers dan CORS terbatas pada origin yang dikonfigurasi.
- Setiap respons membawa `request_id` untuk korelasi dengan audit dan log.
- Endpoint `export` dan detail data sensitif mencatat audit `VIEW_SENSITIVE_DATA` / `EXPORT_DATA`.
- Pesan error tidak memuat query, stack trace, atau struktur internal.

## 4. YANG DITETAPKAN PADA TASK BERIKUTNYA

Skema request/response per endpoint, contoh payload, dan aturan validasi rinci ditulis bersama implementasi (TASK 030–040) dan diverifikasi lewat OpenAPI + test. Dokumen ini menetapkan bentuk kontrak, bukan menggantikan OpenAPI.
