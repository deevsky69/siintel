# DATA DICTIONARY — PREDIKSI PRESISI

## Konvensi
- PK/FK utama: UUID.
- Timestamp: `timestamptz`.
- Score: `smallint` dengan constraint 0–100 bila berlaku.
- Geospasial: PostGIS `geometry(Point,4326)`; latitude/longitude dipertahankan untuk import/API.
- Tambahkan `created_at`/`updated_at` di database bila dibutuhkan audit teknis.
- Jangan masukkan identitas pribadi pada PoC tanpa persetujuan.

Spesifikasi meminta data per kejadian, terutama jenis kejadian, tanggal, jam, Polsek, kecamatan, kelurahan, lokasi/grid, koordinat, kategori TKP, modus, objek sasaran, dan status. fileciteturn2file11

## 1. `crime_incidents`

| Field | Type | Req | Key | Keterangan |
|---|---|---:|---|---|
| incident_id | uuid | Ya | PK | ID anonim |
| incident_type | string/enum | Ya | | Curanmor/Curat/Curas/Tawuran/Kejahatan Jalanan |
| incident_date | date | Ya | | Tanggal kejadian |
| incident_time | time | Ya | | Jam kejadian |
| location_id | uuid | Ya | FK | Lokasi/grid |
| polsek | string | Ya | | Wilayah |
| kecamatan | string | Ya | | Kecamatan |
| kelurahan | string | Dianjurkan | | Kelurahan |
| grid_id | string | Dianjurkan | | Grid 250–500 m |
| latitude | decimal | Ideal | | Latitude |
| longitude | decimal | Ideal | | Longitude |
| location_type | string | Penting | | Kategori TKP |
| modus | string | Penting | | Modus |
| target_type | string | Penting | | Objek sasaran |
| status | string | Pendukung | | Status penanganan |

## 2. `locations`

`location_id` PK, `polsek`, `kecamatan`, `kelurahan`, `grid_id`, `grid_size_m`, `latitude`, `longitude`, `location_type`.

Grid 250–500 m disebut sebagai opsi untuk menjaga sensitivitas lokasi. fileciteturn2file11

## 3. `police_units`

`unit_id` PK, `function`, `unit_name`, `jurisdiction`, `status`.

## 4. `patrol_activity`

`patrol_id` PK, `unit_id` FK, `patrol_date`, `start_time`, `end_time`, `location_id` FK, `activity_type`, `result`.

Data Samapta mencakup patroli, rute, waktu, dan hasil kegiatan. fileciteturn2file11

## 5. `intelligence_reports`

`intelligence_id` PK, `report_date`, `category`, `location_id` FK, `reliability`, `confidence` 0–100, `urgency` 0–100, `impact`, `status`.

Atribut reliability/confidence/urgency/impact disebut dalam spesifikasi. fileciteturn2file17

## 6. `citizen_reports`

`report_id` PK, `reported_at`, `incident_time`, `category`, `description`, `latitude`, `longitude`, `location_text`, `urgency_score`, `verification_score`, `status`.

Laporan masyarakat harus divalidasi; tidak langsung dianggap fakta. Foto/video/audio serta identitas/kontak bersifat opsional dan perlu perlindungan data. fileciteturn2file8

## 7. `public_alerts`

`public_alert_id` PK, `warning_id` FK nullable, `created_at`, `severity`, `threat_type`, `location_text`, `time_window`, `status`, `public_message`.

Jangan mengekspos detail internal/sensitif melalui alert publik.

## 8. `community_feedback`

`feedback_id` PK, `report_id` FK, `feedback_type`, `submitted_at`, `status`.

## 9. `risk_scores`

`risk_score_id` PK, `assessment_date`, `location_id` FK, `threat_type`, `time_window`, `risk_score` 0–100, `risk_class`, `historical_factor`, `recent_trend_factor`, `temporal_factor`, `spatial_factor`, `context_factor`, `model_version`.

Risk score 0–100 dan kelas Low/Moderate/High/Critical disebut dalam spesifikasi. Bobot ditentukan melalui penelitian/model. fileciteturn2file18

## 10. `predictions`

`prediction_id` PK, `prediction_date`, `forecast_horizon`, `threat_type`, `location_id` FK, `time_window`, `risk_score`, `confidence`, `dominant_factors`, `model_version`, `status`.

Output prediction: WHAT, WHERE, WHEN, RISK, CONFIDENCE, WHY. Horizon yang dirancang: 6 jam, 12 jam, 24 jam, 3 hari, 7 hari. fileciteturn2file18

## 11. `early_warnings`

`warning_id` PK, `prediction_id` FK, `created_at`, `severity`, `threat_type`, `location_id` FK, `time_window`, `risk_score`, `confidence`, `status`.

Level yang dirancang: Low, Watch, Warning, Critical. Threshold final belum ditetapkan. fileciteturn2file18

## 12. `recommendations`

`recommendation_id` PK, `prediction_id` FK, `warning_id` nullable FK, `recommended_function`, `recommendation_text`, `priority`, `status`, `created_at`.

Fungsi sasaran dapat mencakup Samapta, Binmas, Intelkam, Reskrim, Lantas. fileciteturn2file15

## 13. `commander_decisions`

`decision_id` PK, `recommendation_id` FK, `decision_by` FK users, `decision`, `decision_at`, `reason`.

Decision: Approve/Modify/Reject. Human-in-the-loop wajib. fileciteturn2file2

## 14. `operational_actions`

`action_id` PK, `decision_id` FK, `unit_id` FK, `location_id` FK, `start_at`, `end_at`, `status`, `result`.

Mewakili tasking, assignment unit, waktu, area, deployment, hasil, dan dokumentasi. fileciteturn2file17

## 15. `prediction_actual`

`evaluation_id` PK, `prediction_id` FK, `evaluation_date`, `actual_event`, `actual_threat_type`, `actual_location_id` FK nullable, `actual_time_window`, `match_type`, `notes`.

Dipakai untuk precision, recall, false positive, false negative, dan evaluasi model. fileciteturn2file17

## 16. `roles`

`role_id` PK, `role_name`, `level`.

Role: Pimpinan, Command Center, Analyst, Fungsi, Polsek, Administrator. fileciteturn2file15

## 17. `users`

`user_id` PK, `username` UQ, `role_id` FK, `status`.

Password tidak disimpan pada dataset dummy; gunakan password hash/identity provider.

## 18. `permissions`

`permission_id` PK, `resource`, `action`.

## 19. `role_permissions`

`role_id` PK/FK, `permission_id` PK/FK. Tabel penghubung many-to-many RBAC; tambahan arsitektur.

## 20. `audit_logs`

`audit_id` PK, `timestamp`, `user_id` FK nullable, `action`, `resource_type`, `resource_id`, `result`.

Audit trail merupakan persyaratan governance. fileciteturn2file2

## Master value yang belum final

Jangan mengunci taxonomy/bobot/threshold secara permanen. Contoh yang sudah disebut sumber:
- Incident: Curanmor, Curat, Curas, Tawuran, Kejahatan Jalanan.
- Risk: Low, Moderate, High, Critical.
- Warning: Low, Watch, Warning, Critical.
- Decision: Approve, Modify, Reject.

Nilai final harus ditetapkan melalui penelitian/model/SOP.
