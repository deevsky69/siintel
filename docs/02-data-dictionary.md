# DATA DICTIONARY — PREDIKSI PRESISI

> Status dokumen: **BASELINE TEKNIS TERKUNCI SEBAGIAN**
> Butir bertanda `TECHNICAL DECISION` diputuskan mandiri (CLAUDE.md §2A/§2B, §6) dan berlaku sebagai baseline kerja.
> Butir bertanda `PROPOSED` / `NOT SPECIFIED` **belum** menjadi requirement dan tidak boleh diasumsikan final.
> Riwayat keputusan: `docs/implementation-notes/000b-specification-decision-log.md`.

---

## 0. KONVENSI

| # | Konvensi | Status |
|---|---|---|
| K-1 | Primary key internal: `uuid` (default `gen_random_uuid()`). | FINAL (konvensi awal dokumen) |
| K-2 | Setiap entitas yang punya ID pada dataset dummy menyimpan ID tersebut pada kolom **`code`** (`text`, `UNIQUE NOT NULL`), mis. `INC-00001`, `LOC-001`. Tujuan: seed dan lampiran Taskap tetap dapat ditelusuri tanpa melanggar K-1. | `TECHNICAL DECISION` (SDL-21) |
| K-3 | Waktu disimpan sebagai `timestamptz` (UTC); ditampilkan dalam WIB (`Asia/Jakarta`) di UI. Format pertukaran: ISO-8601. Importer wajib menerima `YYYY-MM-DDTHH:MM` dan `YYYY-MM-DD HH:MM` lalu menormalkannya. | `TECHNICAL DECISION` (SDL-22) |
| K-4 | Skor (`risk_score`, `confidence`, `urgency*`, `verification_score`, faktor risiko): `smallint`, `CHECK (0..100)`. | FINAL (docs/06) |
| K-5 | Geospasial: PostGIS `geometry(Point,4326)`. Kolom `latitude`/`longitude` dipertahankan untuk import/API. | FINAL |
| K-6 | Semua tabel memiliki `created_at timestamptz NOT NULL DEFAULT now()`; tabel yang dapat berubah state juga memiliki `updated_at`. | `TECHNICAL DECISION` |
| K-7 | **Bahasa:** nama tabel/kolom dan **nilai enum yang disimpan** memakai Inggris `snake_case`/`UPPER_SNAKE`. Label yang dilihat pengguna memakai Bahasa Indonesia melalui lapisan label (`config/taxonomy/`). Nomenklatur kedinasan (Polsek, Kecamatan, Kelurahan, Samapta, Binmas, Intelkam, Reskrim, Lantas, Curanmor, Curat, Curas) **tidak diterjemahkan** dan dipakai apa adanya sebagai nilai taksonomi. | `TECHNICAL DECISION` (SDL-07) |
| K-8 | Referensi lokasi memakai `location_id` (FK ke `locations`). Data import yang hanya memiliki `grid_id` dipetakan melalui `locations.grid_id`. Kolom `kecamatan`/`kelurahan` **tidak diduplikasi** pada tabel transaksi; diperoleh lewat join. | FINAL — CLAUDE.md §19 |
| K-9 | Penanda data sintetis **tidak** disimpan sebagai kolom per tabel. Seluruh isi `data/sample/` sudah sintetis menurut definisi; penandaan dilakukan pada tingkat dataset/README dan `model_version` (`dummy-v*`). | `TECHNICAL DECISION` (menggantikan kolom `is_synthetic` yang hanya ada di 6 dari 19 file) |
| K-10 | Tidak ada identitas korban/pelaku/saksi pada PoC. Penambahan data pribadi mengikuti CLAUDE.md §16 dan memerlukan persetujuan. | FINAL |

**Enum tersimpan ditulis `UPPER_SNAKE`.** Nilai Bahasa Indonesia pada `data/sample/` dipetakan saat seed melalui tabel pemetaan di `config/taxonomy/` (lihat §22).

---

## 1. `locations` — master wilayah/grid

| Field | Type | Req | Key | Keterangan |
|---|---|---|---|---|
| location_id | uuid | Ya | PK | |
| code | text | Ya | UQ | `LOC-001` |
| grid_id | text | Ya | UQ | `JKS-001`; kunci alami untuk import |
| polsek | text | Ya | | |
| kecamatan | text | Ya | | |
| kelurahan | text | Tidak | | |
| grid_size_m | integer | Ya | | Nilai pada dataset: 500. Ukuran final `NOT SPECIFIED` (U-04) |
| latitude | numeric(9,6) | Ya | | |
| longitude | numeric(9,6) | Ya | | |
| geom | geometry(Point,4326) | Ya | | Diturunkan dari lat/long |
| location_type | text | Tidak | | Kategori TKP |

> **NOT SPECIFIED (U-04):** ukuran grid final, sumber batas administratif, dan apakah diperlukan geometri poligon per grid.
> Pada dataset dummy 1 grid = 1 kelurahan (33 grid, 9 kecamatan), sehingga drill-down *area → sub-area → grid* belum terwakili.
> Kolom poligon dan/atau tabel batas wilayah **tidak ditambahkan sekarang** (CLAUDE.md §37) dan menunggu keputusan pemilik data.

## 2. `police_units`

`unit_id` uuid PK · `code` UQ · `function` (SAMAPTA/BINMAS/INTELKAM/RESKRIM/LANTAS) · `unit_name` · `jurisdiction` · `status`.

## 3. `crime_incidents`

| Field | Type | Req | Key | Keterangan |
|---|---|---|---|---|
| incident_id | uuid | Ya | PK | |
| code | text | Ya | UQ | `INC-00001` (ID anonim) |
| incident_type | text/enum | Ya | | Lihat §22 |
| occurred_at | timestamptz | Ya | | Gabungan `incident_date` + `incident_time` saat import |
| incident_date | date | Ya | | Dipertahankan untuk agregasi harian |
| incident_time | time | Ya | | Dipertahankan untuk analisis jam rawan |
| location_id | uuid | Ya | FK → locations | K-8 |
| location_type | text | Tidak | | Kategori TKP |
| modus | text | Tidak | | |
| target_type | text | Tidak | | |
| status | text/enum | Tidak | | Lihat §22 |

`polsek`, `kecamatan`, `kelurahan`, `grid_id`, `latitude`, `longitude` **tidak lagi disimpan di tabel ini** (K-8) — tersedia lewat join ke `locations`.

## 4. `intelligence_reports`

`intelligence_id` uuid PK · `code` UQ · `report_date` · `category` · `location_id` FK · `reliability` (A/B/C — skala kepercayaan sumber) · `confidence` 0–100 · `urgency` 0–100 · `impact` · `status`.

## 5. `patrol_activity`

`patrol_id` uuid PK · `code` UQ · `unit_id` FK · `patrol_date` · `start_time` · `end_time` · `location_id` FK · `activity_type` · `result`.

## 6. `citizen_reports`

`report_id` uuid PK · `code` UQ · `reported_at` · `incident_time` · `category` · `description` · `latitude` · `longitude` · `geom` · **`location_id` FK nullable** · `location_text` · `urgency_score` 0–100 · `verification_score` 0–100 · `status`.

> `location_id` ditambahkan untuk menutup C-03 (ERD sudah menyatakan relasi ini; CLAUDE.md §19 mencantumkan `citizen_reports` sebagai pemakai `location_id`).
> Nullable karena laporan masyarakat masuk dengan koordinat bebas dan baru dipetakan ke grid setelah geo-processing.
> Laporan masyarakat **tidak otomatis dianggap fakta**; wajib melewati verifikasi.
> **NOT SPECIFIED (U-13):** identitas/kontak pelapor, lampiran bukti (foto/video/audio), dan cara pelapor melihat status. Tidak ada tabel lampiran pada PoC.

## 7. `public_alerts`

`public_alert_id` uuid PK · `code` UQ · `warning_id` FK nullable · `created_at` · `severity` · `threat_type` · `area_text` · `time_window` · `window_start` · `window_end` · `status` · `public_message`.

Memakai `area_text` (teks wilayah untuk publik), bukan `location_id`, agar tidak mengekspos grid internal.
> **NOT SPECIFIED (U-10):** siapa berwenang mempublikasikan dan severity minimum yang boleh dipublikasikan. `REQUIRES HUMAN / POLICY APPROVAL`.

## 8. `community_feedback`

`feedback_id` uuid PK · `code` UQ · `report_id` FK → citizen_reports · `feedback_type` · `submitted_at` · `status`.

## 9. `risk_scores` — **layer risiko berjalan (current risk)**

| Field | Type | Req | Keterangan |
|---|---|---|---|
| risk_score_id | uuid | Ya | PK |
| code | text | Ya | UQ |
| assessment_date | date | Ya | Tanggal penilaian |
| location_id | uuid | Ya | FK |
| threat_type | text | Ya | |
| time_window | text | Ya | Label jendela waktu (§21) |
| window_start / window_end | timestamptz | Ya | Batas jendela yang dapat di-query |
| risk_score | smallint | Ya | 0–100 |
| risk_class | text/enum | Ya | `LOW`/`MODERATE`/`HIGH`/`CRITICAL` |
| historical_factor | smallint | Ya | Sub-skor 0–100 |
| recent_trend_factor | smallint | Ya | Sub-skor 0–100 |
| temporal_factor | smallint | Ya | Sub-skor 0–100 |
| spatial_factor | smallint | Ya | Sub-skor 0–100 |
| context_factor | smallint | Ya | Sub-skor 0–100 |
| weights_version | text | Ya | Versi bobot yang dipakai (`config/risk/risk-weights.yaml`) |
| model_version | text | Ya | |

**Kontrak faktor (`TECHNICAL DECISION`, SDL-18).** Kelima kolom faktor adalah **sub-skor 0–100**, bukan kontribusi yang menjumlah ke total. Hubungannya:

```text
risk_score = round( Σ ( bobot_i × faktor_i ) )    dengan Σ bobot_i = 1
```

Bobot **tidak** disimpan di kode maupun di baris data; berasal dari `config/risk/risk-weights.yaml` dan versinya dicatat pada `weights_version`.
`CHECK` constraint atas hubungan ini **baru dipasang setelah bobot disetujui** (lihat docs/06).

> **DITETAPKAN (U-02), 9 September 2026:** bobot versi `dummy-v1` pada `config/risk/risk-weights.yaml` berlaku sebagai ketentuan. Nilainya tidak berubah saat ditetapkan, sehingga seluruh baris lama tetap sah. Ketetapan ini **bukan** pernyataan bahwa bobotnya terbukti secara empiris; itu tetap menunggu penelitian/model/evaluasi.
> **DITETAPKAN (U-01), 9 September 2026:** batas kelas `risk_class` — LOW <45, MODERATE 45–69, HIGH 70–84, CRITICAL ≥85 — berlaku sebagai ketentuan, versi `dummy-v1`. Angkanya semula tertanam diam-diam di dataset dummy; kini ia berlaku karena diputus, bukan karena kebetulan ada di data.

**Peran tabel ini (`TECHNICAL DECISION`, SDL-13):** `risk_scores` adalah penilaian risiko **kondisi berjalan** per (lokasi × jendela waktu × jenis ancaman × tanggal penilaian). Menjadi sumber layer *Current Risk* pada peta (CLAUDE.md §24, TASK 082) dan dapat menjadi fitur masukan model. **Bukan** tahap antara antara prediction dan early warning.

## 10. `predictions` — **layer risiko prediktif**

| Field | Type | Req | Keterangan |
|---|---|---|---|
| prediction_id | uuid | Ya | PK |
| code | text | Ya | UQ |
| prediction_date | date | Ya | Kapan prediksi dibuat |
| forecast_horizon | text/enum | Ya | `6H`,`12H`,`24H`,`3D`,`7D` (docs/01 §5.5) |
| threat_type | text | Ya | |
| location_id | uuid | Ya | FK |
| time_window | text | Ya | Label jendela (§21) |
| window_start / window_end | timestamptz | Ya | Jendela waktu yang diprediksi |
| risk_score | smallint | Ya | 0–100 |
| confidence | smallint | Ya | 0–100 |
| dominant_factors | jsonb | Ya | WHY — lihat kontrak di bawah |
| model_version | text | Ya | |
| baseline_risk_score_id | uuid | Tidak | FK nullable → risk_scores, untuk penelusuran |
| status | text/enum | Ya | `DRAFT`/`PUBLISHED`/`VALIDATED` |

Output prediction wajib menjawab WHAT · WHERE · WHEN · RISK · CONFIDENCE · WHY (CLAUDE.md §10).

**Kontrak `dominant_factors` (`TECHNICAL DECISION`).** Disimpan sebagai `jsonb` berisi daftar objek `{factor, contribution, source}` dengan `source ∈ {RULE, MODEL}` — bukan kalimat bebas. Alasan: CLAUDE.md §27 mewajibkan WHY berasal dari mekanisme yang benar-benar dipakai; teks bebas membuat penjelasan fiktif tidak terdeteksi. UI wajib menampilkan `source` sehingga prototipe berbasis rule tidak terbaca sebagai temuan model.

**Hubungan `forecast_horizon` ↔ jendela waktu (`TECHNICAL DECISION`, SDL-14).** `forecast_horizon` menyatakan jarak dari `prediction_date` ke awal jendela; `window_start`/`window_end` menyatakan jendela yang diprediksi. Untuk horizon ≤24H jendela mengikuti bin 6 jam (§21); untuk 3D/7D jendela adalah rentang tanggal.
> **NOT SPECIFIED (U-03):** definisi resmi target prediksi (apa yang dihitung sebagai "kejadian" pada satu grid × jendela). `REQUIRES USER APPROVAL`.

## 11. `early_warnings`

`warning_id` uuid PK · `code` UQ · `prediction_id` FK **NOT NULL** · `created_at` · `severity` (`LOW`/`WATCH`/`WARNING`/`CRITICAL`) · `threat_type` · `location_id` FK · `time_window` · `window_start`/`window_end` · `risk_score` · `confidence` · `status` (`ACTIVE`/`ACKNOWLEDGED`/`RESOLVED`) · `acknowledged_by` FK users nullable · `acknowledged_at` nullable · `resolved_by` FK users nullable · `resolved_at` nullable · `threshold_version`.

`acknowledged_*`/`resolved_*` ditambahkan karena docs/05 menyediakan transisi acknowledge/resolve tetapi tidak ada tempat menyimpan pelakunya (`TECHNICAL DECISION`).
`severity`, `risk_score`, `threat_type`, dan `location_id` disalin dari prediksi sumber pada saat warning dibuat (snapshot) agar riwayat peringatan tidak berubah ketika prediksi diperbarui.

> **DITETAPKAN (U-01), 9 September 2026:** threshold pemicu dan batas antar level — warning ≥70, critical ≥85 — berlaku sebagai ketentuan, versi `dummy-v1`. Level `LOW` dan `WATCH` tetap tidak pernah muncul pada dataset karena peringatan hanya dibuat pada skor ≥70; itu sifat datanya, bukan cacat ambangnya. Threshold tetap configurable (CLAUDE.md §12) melalui `config/risk/warning-thresholds.yaml`, versinya dicatat pada `threshold_version`.

## 12. `recommendations`

`recommendation_id` uuid PK · `code` UQ · `prediction_id` FK · `warning_id` FK nullable · `recommended_function` (SAMAPTA/BINMAS/INTELKAM/RESKRIM/LANTAS) · `recommendation_text` · `priority` · `status` (`PENDING_REVIEW`/`APPROVED`/`MODIFIED`/`REJECTED`) · `created_at`.

**Aturan status (`TECHNICAL DECISION`, S-15).** `recommendations.status` adalah **cerminan** dari keputusan terakhir pada `commander_decisions` dan hanya boleh diubah oleh proses yang menulis keputusan tersebut. Sumber kebenaran keputusan tetap `commander_decisions`. Rekomendasi tanpa keputusan berstatus `PENDING_REVIEW`.

## 13. `commander_decisions`

`decision_id` uuid PK · `code` UQ · `recommendation_id` FK · `decision_by` FK → users **NOT NULL** · `decision` (`APPROVED`/`MODIFIED`/`REJECTED`) · `decision_at` · `reason` · `modified_text` nullable.

`modified_text` menyimpan isi rekomendasi hasil modifikasi (`TECHNICAL DECISION`, U-07). Rekomendasi asli **tidak ditimpa**, sehingga jejak "apa yang diusulkan AI" vs "apa yang diputuskan manusia" tetap utuh — syarat human-in-the-loop CLAUDE.md §13.
> **NOT SPECIFIED (U-06/U-10):** role/jabatan mana yang berwenang memutuskan untuk tiap tingkat. `REQUIRES HUMAN / POLICY APPROVAL`.

## 14. `operational_actions`

`action_id` uuid PK · `code` UQ · `decision_id` FK · `unit_id` FK · `location_id` FK · `created_by` FK → users · `start_at` · `end_at` · `status` (`PLANNED`/`ACTIVE`/`COMPLETED`/`CANCELLED`) · `result`.

`created_by` ditambahkan untuk menutup C-03 (ERD menyatakan `USERS ||--o{ OPERATIONAL_ACTIONS : creates`).
Action hanya boleh dibuat dari keputusan berstatus `APPROVED` atau `MODIFIED`.

## 15. `prediction_actual` — evaluasi prediksi vs kejadian nyata

| Field | Type | Req | Keterangan |
|---|---|---|---|
| evaluation_id | uuid | Ya | PK |
| code | text | Ya | UQ |
| evaluation_date | date | Ya | |
| prediction_id | uuid | **Tidak** | FK nullable → predictions |
| actual_incident_id | uuid | Tidak | FK nullable → crime_incidents |
| actual_event | boolean | Ya | Apakah kejadian benar terjadi pada jendela dievaluasi |
| actual_threat_type | text | Tidak | |
| actual_location_id | uuid | Tidak | FK nullable |
| actual_window_start / actual_window_end | timestamptz | Tidak | |
| match_type | text/enum | Ya | `HIT` / `FALSE_POSITIVE` / `FALSE_NEGATIVE` |
| notes | text | Tidak | |

**Perubahan penting (`TECHNICAL DECISION`, SDL-15 revisi).** `prediction_id` dijadikan **nullable** dan `match_type` menerima `FALSE_NEGATIVE`, sehingga **kejadian aktual yang tidak diprediksi dapat direpresentasikan** — diwajibkan oleh CLAUDE.md §26 ("Actual event yang tidak diprediksi harus tetap dapat direpresentasikan… jangan mendesain evaluation hanya sebagai prediction → actual").

Aturan integritas:
- `HIT` dan `FALSE_POSITIVE` → `prediction_id` wajib terisi;
- `FALSE_NEGATIVE` → `actual_incident_id` wajib terisi dan `prediction_id` NULL;
- hanya prediksi berstatus `PUBLISHED`/`VALIDATED` yang boleh dievaluasi.

Dengan ini precision **dan** recall dapat dihitung (CLAUDE.md §26; TASK 104/151).
> **NOT SPECIFIED (U-03):** aturan pencocokan spasial/temporal antara kejadian aktual dan prediksi (toleransi jarak/waktu). `REQUIRES USER APPROVAL` sebelum angka evaluasi dipublikasikan.

## 16. `roles`

`role_id` uuid PK · `code` UQ (`ROLE-01`) · `role_name` · `level` smallint (1–6).

Role: Pimpinan (1), Command Center (2), Analyst (3), Fungsi (4), Polsek (5), Administrator (6).
`level` disimpan sebagai angka, bukan teks `"Level 1"` (`TECHNICAL DECISION`).

## 17. `users`

| Field | Type | Req | Keterangan |
|---|---|---|---|
| user_id | uuid | Ya | PK |
| code | text | Ya | UQ (`USER-001`) |
| username | text | Ya | UQ |
| full_name | text | Tidak | |
| password_hash | text | Ya | Argon2id (SDL-06) |
| role_id | uuid | Ya | FK |
| polsek | text | Tidak | Jurisdiksi untuk scope `OWN_JURISDICTION` |
| function | text | Tidak | Fungsi untuk scope `OWN_FUNCTION` (Intelkam/Reskrim/…) |
| status | text/enum | Ya | `ACTIVE`/`INACTIVE` |
| last_login_at | timestamptz | Tidak | |
| must_change_password | boolean | Ya | default true untuk akun seed |

`password_hash`, `polsek`, `function`, `last_login_at`, `must_change_password` ditambahkan (`TECHNICAL DECISION`): tanpa `password_hash` TASK 050 tidak dapat berjalan, dan tanpa `polsek`/`function` simbol `L` (limited/jurisdiction-scoped) pada docs/03 tidak dapat ditegakkan di backend.
**Password tidak pernah masuk ke dataset dummy.** Akun seed memakai hash yang dibuat saat seed dari environment lokal.
> **NOT SPECIFIED (U-05):** kebijakan panjang/rotasi password, MFA, dan ketersediaan SSO Polri. `REQUIRES HUMAN / POLICY APPROVAL`.

## 18. `permissions`

`permission_id` uuid PK · `code` UQ (`PERM-01`) · `resource` · `action` · `description`.
Katalog lengkap: `docs/03-role-permission-matrix.md` §2.

## 19. `role_permissions`

`role_id` + `permission_id` PK gabungan · `scope` (`ALL` / `OWN_JURISDICTION` / `OWN_FUNCTION`).

Kolom `scope` ditambahkan (`TECHNICAL DECISION`, SDL-09/D-09) sebagai cara menegakkan simbol `L` pada matriks RBAC di backend, bukan sekadar menyembunyikan tombol (CLAUDE.md §15).

## 20. `audit_logs`

`audit_id` uuid PK · `timestamp` timestamptz · `user_id` FK nullable (NULL untuk system event) · `action` · `resource_type` · `resource_id` · `result` (`SUCCESS`/`DENIED`/`FAILED`) · `detail` jsonb nullable.

`result` dibakukan menjadi tiga nilai (`TECHNICAL DECISION`): tanpa `DENIED`, penolakan otorisasi tidak terekam padahal itu justru bukti utama RBAC bekerja.
`detail` menyimpan konteks tambahan (mis. nilai konfigurasi sebelum/sesudah pada `CHANGE_CONFIGURATION`).
`action` harus konsisten dengan `resource_type` — lihat aturan seed pada docs/08 TASK 024.
Audit bersifat **append-only**: tidak ada endpoint update/delete.
> **NOT SPECIFIED (U-14):** retensi dan klasifikasi log. `REQUIRES HUMAN / POLICY APPROVAL`.

---

## 21. JENDELA WAKTU (TIME WINDOW)

Dataset dummy memakai empat bin 6 jam: `00:00-06:00`, `06:00-12:00`, `12:00-18:00`, `18:00-23:59`.

`TECHNICAL DECISION`: bin disimpan sebagai **`window_start`/`window_end` (`timestamptz`, half-open `[start, end)`)**; kolom `time_window` dipertahankan sebagai **label tampilan** sesuai daftar field wajib CLAUDE.md §10 dan diturunkan dari batas tersebut. Bin keempat dinormalkan menjadi `[18:00, 24:00)` sehingga tidak ada celah 23:59–24:00.

> **NOT SPECIFIED (U-03):** apakah empat bin 6 jam adalah granularitas operasional final.

---

## 22. TAKSONOMI & PEMETAAN NILAI

**DITETAPKAN (U-16), 9 September 2026.** Nilai berikut berlaku sebagai taksonomi sistem, versi `taksonomi-2026-09-01`. Tidak ada satu nilai pun yang berubah saat penetapan, sehingga seluruh baris yang sudah tersimpan tetap sah. Pemetaan Indonesia→enum disimpan di `config/taxonomy/` dan diterapkan saat seed/import — canonical schema tidak diubah mengikuti file sumber (CLAUDE.md §18). Menambah nilai baru kini menuntut versi baru, bukan penyuntingan versi ini.

> **Tiga baris terakhir tabel di bawah TIDAK ikut ditetapkan** dan memang tidak dipetakan sama sekali. `modus`, `target_type`, dan `location_type` dipertahankan apa adanya sebagai istilah lapangan — keputusan teknis yang mendahului penetapan ini. Akibatnya nyata: `incident_type` yang tidak dikenal **menghentikan** seed, sedangkan `modus` yang tidak dikenal diterima apa adanya. Menutup ketiga daftar itu adalah keputusan tersendiri, dan konsekuensinya seed menolak istilah lapangan yang belum terdaftar.

| Domain | Nilai pada dataset dummy | Enum tersimpan (K-7) |
|---|---|---|
| `incident_type` | CURANMOR, CURAT, CURAS, TAWURAN, KEJAHATAN_JALANAN | sama (sudah UPPER_SNAKE) |
| `crime_incidents.status` | Dilaporkan, Penyelidikan, Penyidikan, Selesai | REPORTED, PRELIMINARY_INVESTIGATION, INVESTIGATION, CLOSED |
| `risk_class` | Low, Moderate, High, Critical | LOW, MODERATE, HIGH, CRITICAL |
| `early_warnings.severity` | Warning, Critical (Low/Watch tidak muncul) | LOW, WATCH, WARNING, CRITICAL |
| `early_warnings.status` | Active, Acknowledged, Resolved | ACTIVE, ACKNOWLEDGED, RESOLVED |
| `predictions.status` | Draft, Published, Validated | DRAFT, PUBLISHED, VALIDATED |
| `recommendations.priority` | Sedang, Tinggi | LOW, MEDIUM, HIGH, URGENT (nilai dummy → MEDIUM, HIGH) |
| `recommendations.status` | Pending Review, Approved, Modified, Rejected | PENDING_REVIEW, APPROVED, MODIFIED, REJECTED |
| `commander_decisions.decision` | Approved, Modified, Rejected | APPROVED, MODIFIED, REJECTED |
| `operational_actions.status` | Planned, Active, Completed | PLANNED, ACTIVE, COMPLETED, CANCELLED |
| `citizen_reports.status` | Diterima, Diverifikasi, Diteruskan, Ditangani, Selesai | RECEIVED, VERIFIED, FORWARDED, IN_PROGRESS, CLOSED |
| `intelligence_reports.status` | Baru, Diverifikasi, Ditindaklanjuti, Selesai | NEW, VERIFIED, FOLLOWED_UP, CLOSED |
| `community_feedback.status` | Baru, Ditinjau, Selesai | NEW, REVIEWED, CLOSED |
| `police_units.status` / `users.status` | Aktif, Standby | ACTIVE, STANDBY / ACTIVE, INACTIVE |
| `intelligence_reports.impact` | Rendah, Sedang, Tinggi, Kritis | LOW, MEDIUM, HIGH, CRITICAL |
| `function` | Samapta, Binmas, Intelkam, Reskrim, Lantas | SAMAPTA, BINMAS, INTELKAM, RESKRIM, LANTAS |
| `modus` | 16 nilai (`kunci_t`, `congkel`, `pecah_kaca`, …) | dipertahankan apa adanya (istilah lapangan) |
| `target_type` | 11 nilai (`motor`, `mobil`, `toko`, …) | dipertahankan apa adanya |
| `location_type` | Permukiman, Parkiran, Jalan, Pertokoan, Pusat Aktivitas, Fasilitas Publik | dipertahankan apa adanya (kategori TKP) |

**State machine antar status (`PROPOSED`, U-08).** Transisi yang diusulkan — final mengikuti SOP:

```text
early_warnings      ACTIVE → ACKNOWLEDGED → RESOLVED
recommendations     PENDING_REVIEW → APPROVED | MODIFIED | REJECTED     (final)
operational_actions PLANNED → ACTIVE → COMPLETED ;  PLANNED|ACTIVE → CANCELLED
citizen_reports     RECEIVED → VERIFIED → FORWARDED → IN_PROGRESS → CLOSED
predictions         DRAFT → PUBLISHED → VALIDATED
```

---

## 23. YANG MASIH MENUNGGU KEPUTUSAN PENGGUNA

~~U-01 threshold risiko/warning~~ dan ~~U-02 bobot faktor~~ ditetapkan 9 September 2026 · U-03 definisi target prediksi & aturan pencocokan evaluasi · U-04 ukuran grid & batas wilayah · U-05 kebijakan kredensial · U-06 aturan scope jurisdiksi/fungsi · U-08 state machine final · U-10 kewenangan publikasi alert · U-13 identitas & bukti LAPOR PRESISI · U-14 retensi/klasifikasi · ~~U-16 taksonomi final~~ ditetapkan 9 September 2026.

Rincian dan opsi: `docs/implementation-notes/000c-specification-lock.md`.

---

*Sumber konsep: dokumen PREDIKSI PRESISI pada `docs/source/` (Resume Spesifikasi Aplikasi, Resume Taskap, Paparan Rencana Taskap).*
