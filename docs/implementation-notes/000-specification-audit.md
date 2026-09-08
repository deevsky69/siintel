# TASK 000 — SPECIFICATION AUDIT

Status: **SELESAI — MENUNGGU KEPUTUSAN PEMILIK PROYEK**
Tanggal audit: 2026-08-31
Auditor: Claude Code
Ruang lingkup: dokumentasi + dataset dummy. **Tidak ada kode, tidak ada database, tidak ada perubahan schema.**

---

## 1. RINGKASAN EKSEKUTIF

Dokumentasi PREDIKSI PRESISI sudah cukup kuat sebagai baseline konseptual: visi produk, governance AI, human-in-the-loop, daftar entitas, dan roadmap sudah konsisten pada level prinsip. Yang belum siap adalah **level kontrak implementasi**: model referensi lokasi, penomoran fase, urutan risk score vs prediction, matriks RBAC, dan kontrak API masih saling bertabrakan; sementara dataset dummy pada `data/sample/` mengandung sejumlah pelanggaran integritas yang akan gagal saat di-seed ke PostgreSQL dengan foreign key aktif (TASK 020–023).

Hasil audit:

| Kategori | Jumlah | Blocker untuk TASK 001–016 |
|---|---:|---:|
| Konflik antar dokumen (C) | 14 | 7 |
| Requirement belum ditentukan (U) | 21 | 8 |
| Keputusan teknis perlu konfirmasi (D) | 14 | 9 |
| Temuan kualitas data dummy (S) | 18 | 6 |
| Risiko utama (R) | 7 | — |

**Tiga hal yang paling perlu diputuskan sebelum TASK 001:**

1. **Model lokasi** — dokumen memakai `location_id`, seluruh dataset dummy memakai `grid_id` + kolom `kecamatan`/`kelurahan` yang diduplikasi. Ini menentukan seluruh schema (C-02, D-08).
2. **Urutan Risk Score vs Prediction** — CLAUDE.md menempatkan risk score *setelah* prediction; roadmap dan master spec menempatkannya *sebelum* prediction; ERD tidak menghubungkan keduanya sama sekali (C-01).
3. **Lokasi paket di repository** — semua dokumen mengasumsikan paket berada di root repository, faktanya berada di `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/` (C-10, D-01).

**Peringatan governance:** dataset dummy secara de facto sudah mengandung threshold risk/warning (Low <45, Moderate 45–69, High 70–84, Critical ≥85; warning terbit pada skor ≥70). Angka ini **BUKAN requirement final** — nilainya hanya hasil generator data sintetis. Sesuai CLAUDE.md §9, §10 dan §26 angka tersebut ditandai `PROPOSED — REQUIRES USER APPROVAL` dan tidak boleh di-hardcode.

---

## 2. METODE AUDIT

1. Membaca `CLAUDE.md`, `README.md`, `.env.example`, `.gitignore`, dan `docs/01` s.d. `docs/08`.
2. Membandingkan setiap entitas pada `docs/02-data-dictionary.md` dengan `docs/04-erd.md`, `docs/06-database-schema.md`, dan CLAUDE.md §14.
3. Memvalidasi 19 file pada `data/sample/` secara programatik: header vs data dictionary, integritas referensial antar file, rentang nilai, konsistensi enum, konsistensi lintas tabel (prediction ↔ risk score ↔ warning ↔ recommendation ↔ decision ↔ action ↔ evaluation), dan konsistensi audit log terhadap `role_permissions`.
4. Menelusuri setiap modul MVP (`docs/01` §3) sampai ke entitas, endpoint, dan task roadmap untuk mencari fitur yang tidak punya penopang data/API/task.

Semua angka pada bagian 5 adalah hasil perhitungan langsung atas file CSV, bukan estimasi.

---

## 3. KONFLIK ANTAR DOKUMEN

### C-01 — Urutan Risk Score vs Prediction bertentangan (BLOCKER)

| Sumber | Urutan yang dinyatakan |
|---|---|
| `CLAUDE.md` §6 | Analysis → **Prediction → Risk Score** → Early Warning |
| `docs/01` §1 & §5 | Analysis → Prediction → Early Warning (tanpa langkah risk score) |
| `docs/01` §20 | butir 7 Risk score → butir 8 **Sample prediction** (risk lebih dulu) |
| `docs/08` PHASE 10 | TASK 102 Risk Score → TASK 103 Prediction (risk lebih dulu) |
| `docs/06` closed-loop | Data → Analysis → Prediction → Early Warning (tanpa risk score) |

Dampak model data: `predictions` memiliki kolom `risk_score` sendiri, `risk_scores` adalah tabel terpisah, dan **ERD tidak memiliki relasi apa pun antara `risk_scores` dan `predictions`**. Akibatnya tidak jelas: apakah `risk_scores` adalah input prediksi, output prediksi, atau perhitungan paralel yang independen. Early warning saat ini digantung ke `predictions`, bukan ke `risk_scores`, padahal CLAUDE.md §10 menyatakan warning dipicu oleh threshold risk.

**Perlu keputusan:** tetapkan satu rantai kanonik dan tetapkan apakah `predictions.risk_score` adalah FK ke `risk_scores` atau kolom nilai independen.

### C-02 — Referensi lokasi: `location_id` vs `grid_id` (BLOCKER)

- `docs/02` mendefinisikan `location_id uuid FK` pada `crime_incidents`, `patrol_activity`, `intelligence_reports`, `risk_scores`, `predictions`, `operational_actions`, `prediction_actual`.
- `docs/04` dan `docs/06` menegaskan `location_id` sebagai referensi master wilayah/grid.
- **Tidak satu pun file di `data/sample/` memiliki kolom `location_id`.** Semuanya memakai `grid_id` (string, mis. `JKS-001`) ditambah duplikasi `kecamatan`/`kelurahan`.

Konsekuensi: seed TASK 020–023 tidak dapat mengisi FK apa pun tanpa lapisan mapping `grid_id → location_id`, dan aturan normalisasi (apakah `kecamatan` boleh diduplikasi di tabel transaksi) belum ditetapkan.

### C-03 — ERD vs Data Dictionary tidak sinkron pada 3 relasi

| Relasi di `docs/04` | Kondisi di `docs/02` |
|---|---|
| `LOCATIONS ||--o{ CITIZEN_REPORTS` | `citizen_reports` (#6) tidak punya `location_id`; hanya `latitude/longitude/location_text` |
| `USERS ||--o{ OPERATIONAL_ACTIONS : creates` | `operational_actions` (#14) tidak punya kolom user/`created_by` |
| `LOCATIONS ||--o{ INTELLIGENCE_REPORTS` | konsisten di dictionary, tetapi CSV memakai `kecamatan/kelurahan/grid_id` |

### C-04 — Tipe primary key: UUID vs string berprefix

`docs/02` §Konvensi: "PK/FK utama: UUID". Dataset dummy memakai ID string bermakna (`INC-00001`, `LOC-001`, `PRD-00001`, `ROLE-01`). Belum diputuskan apakah ID dummy dipetakan ke UUID saat seed, disimpan sebagai kolom `code`/`external_ref`, atau konvensi UUID dilonggarkan.

### C-05 — Tiga skema penomoran fase yang saling menimpa (BLOCKER OPERASIONAL)

| Nomor | `CLAUDE.md` §27 | `docs/01` §16 | `docs/08` |
|---|---|---|---|
| Phase 3 | Seed / dummy data | GIS | Dummy data |
| Phase 4 | Backend API | Analytics | Backend API |
| Phase 5 | Authentication + RBAC | Risk & prediction | Authentication & RBAC |
| Phase 8 | GIS | Delivery | GIS |

Kalimat "kerjakan Phase 5" punya tiga arti berbeda. Perlu satu penomoran kanonik (rekomendasi: `docs/08` sebagai satu-satunya sumber penomoran, dua dokumen lain merujuk ke sana).

### C-06 — Metode pengembangan: vertical slice vs layered (BLOCKER METODOLOGIS)

`docs/01` §15 tegas: "Build vertical slices, not all frontend first and backend later", dan §20 menetapkan slice pertama Login → … → Prediction vs Actual.
`docs/08` justru horizontal murni: seluruh tabel (TASK 011–016) → seluruh API (TASK 031–040) → autentikasi → UI. Slice end-to-end pertama baru selesai sekitar TASK 150.

Kedua pendekatan sah, tetapi tidak bisa dijalankan bersamaan. CLAUDE.md §27 memerintahkan mengikuti roadmap, sehingga secara de facto §15 master spec terabaikan tanpa keputusan eksplisit.

### C-07 — Authorization diminta sebelum RBAC dibangun

`docs/08` PHASE 4 menutup daftar API dengan "Setiap endpoint: validation; **authorization**; test", padahal autentikasi dan RBAC baru dibangun pada PHASE 5 (TASK 050–052). `docs/01` §16 Phase 1 justru menempatkan authentication + RBAC bersamaan dengan database, sebelum API domain. Urutan roadmap saat ini menghasilkan dependensi melingkar atau API yang lahir tanpa proteksi.

### C-08 — Matriks RBAC vs katalog permission dummy tidak cocok

`docs/03` mendefinisikan 12 modul × 6 role dengan simbol R/W/A/L. `data/sample/permissions.csv` hanya berisi 12 permission `resource:action` dan `role_permissions.csv` 28 pemetaan. Contoh ketidaksesuaian:

| Role | Matriks `docs/03` | Seed `role_permissions.csv` |
|---|---|---|
| Analyst | RW pada Crime, Map, Analytics, Prediction, Risk, Warning, Recommendation, Evaluation | hanya read + `prediction:run`; tidak ada `crime:write` |
| Command Center | RW Map, RW Early Warning, RW Recommendation, R Analytics/Prediction/Risk/Evaluation | 5 permission read saja; tanpa analytics/prediction/evaluation |
| Administrator | R hampir semua modul, RW User Management, RW Audit Logs | hanya `dashboard:read` + `users:manage` |
| Pimpinan | RA Recommendation, A Commander Decision, R Audit | tidak ada permission audit |

Selain itu katalog permission tidak memiliki resource untuk `risk_score`, `audit`, `locations`, `operations`, `citizen_reports`, `public_alerts`, `intelligence`, `patrol`, dan tidak memiliki action `write`/`publish`/`acknowledge`/`export`.

### C-09 — Kontrak API tidak menutupi kebutuhan spesifikasi dan roadmap

`docs/01` §14 menyebut 14 area API; `docs/05` hanya mendefinisikan 8 kelompok. Yang hilang: `/api/users`, `/api/roles`, `/api/locations`, `/api/analytics`, `/api/executive-brief`. Roadmap juga meminta Intelligence API (TASK 033), Patrol API (TASK 034), dan Operations API (TASK 039) yang tidak ada di `docs/05`. Tidak ada pula endpoint untuk `citizen_reports`, `public_alerts`, `community_feedback`, dan `audit_logs`.

Ketidaklengkapan lain pada `docs/05`:
- ada `POST /api/warnings/{id}/acknowledge`, tidak ada transisi `resolve` padahal status `Resolved` dipakai dataset;
- keputusan komandan diekspos sebagai aksi pada resource `recommendations`, sementara `commander_decisions` adalah entitas tersendiri — konvensi resource belum disepakati;
- format error, pagination, filter, versioning, dan skema autentikasi hanya disebut sebagai prinsip, belum sebagai kontrak.

### C-10 — Struktur folder tidak sesuai kondisi repository nyata

1. `docs/07` mencantumkan `docs/01` s.d. `docs/07`, **tidak mencantumkan `08-implementation-roadmap.md`** (padahal README dan CLAUDE.md §27 mewajibkannya) dan tidak mencantumkan `docs/implementation-notes/` (output TASK 000).
2. Terdapat **`docs/CLAUDE.md` yang identik byte-per-byte dengan `CLAUDE.md`** di root paket. Dua salinan aturan kerja = dua sumber kebenaran yang akan menyimpang.
3. Struktur mengasumsikan paket berada di root repository. Faktanya root repository (`siintel`) berisi `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/` sebagai subfolder, ditambah `README.md` ("siintel"), `GAMBARAN WEBSITE.png`, tiga PDF sumber, dan `.DS_Store` yang **sudah ter-commit**. `.gitignore` hanya berlaku di dalam subfolder sehingga tidak melindungi root.

### C-11 — Tiga versi pipeline data

| Sumber | Pipeline |
|---|---|
| `CLAUDE.md` §7 | RAW → VALIDATION → MAPPING → ANONYMIZATION → GEO/GRID → PROCESSED → DATABASE |
| `docs/01` §7 | RAW → CLEAN → VALIDATE → ANONYMIZE → GEO/GRID → FEATURE ENGINEERING → ANALYSIS → MODEL → PREDICTION → VALIDATION → EVALUATION |
| `docs/07` aturan 5 | validation → mapping → anonymization → geo/grid → processed → database |

Tahap `CLEAN`, `MAPPING`, dan `FEATURE ENGINEERING` muncul/hilang tanpa penjelasan. Perlu satu definisi tahap beserta artefak keluaran tiap tahap.

### C-12 — Stack backend Python di dalam struktur monorepo bergaya JavaScript

`docs/01` §10 menetapkan backend Python + FastAPI. `docs/07` menyediakan `packages/shared/{types,schemas,constants}` dan `.gitignore` memuat `node_modules/`, `.venv/`, `dist/`, `build/`, `coverage/`. Belum ditentukan: tool monorepo (pnpm/npm workspaces? Turborepo? tidak ada?), package manager Python (uv/poetry/pip-tools), dan **bagaimana tipe dibagikan antara backend Python dan frontend TypeScript** (generate dari OpenAPI, atau ditulis dua kali).

### C-13 — Bahasa nilai enum campur Indonesia/Inggris dalam satu tabel

Contoh nyata pada `recommendations.csv`: `priority` = `Sedang`/`Tinggi` (Indonesia) sementara `status` = `Approved`/`Pending Review`/`Modified`/`Rejected` (Inggris). `crime_incidents.status` Indonesia (`Dilaporkan`, `Penyelidikan`, `Penyidikan`, `Selesai`), `predictions.status` Inggris (`Draft`, `Published`, `Validated`). Tidak ada aturan bahasa untuk enum, nama kolom, pesan API, maupun label UI.

### C-14 — README paket tidak konsisten dengan daftar dokumen

Bagian "Isi" pada `README.md` hanya menyebut `01`, `02`, `03`, `05`; bagian "Baseline arsitektur" menyebut `01`–`07`; bagian "Claude Implementation Guide" menyebut `08`. `docs/04` dan `docs/06` tidak pernah muncul di bagian "Isi".

---

## 4. REQUIREMENT YANG BELUM DITENTUKAN (`NOT SPECIFIED`)

Semua butir di bawah ini **tidak boleh diasumsikan** oleh implementasi (CLAUDE.md §26).

| ID | Requirement | Status | Blocker task |
|---|---|---|---|
| U-01 | Threshold kelas risiko & level early warning | NOT SPECIFIED — dataset dummy memakai Low <45 / Moderate 45–69 / High 70–84 / Critical ≥85, warning terbit ≥70. Nilai ini **PROPOSED**, bukan requirement. Level `Watch` tidak pernah muncul di data. | TASK 102, 110 |
| U-02 | Bobot dan definisi 5 faktor risk score (`historical/recent_trend/temporal/spatial/context`) | NOT SPECIFIED — dan pada data dummy jumlah kelima faktor tidak sama dengan `risk_score` (lihat S-04) | TASK 102 |
| U-03 | Definisi target prediksi: unit spasial, panjang jendela waktu, dan definisi "kejadian" | NOT SPECIFIED — dataset memakai 4 bin 6 jam (`00:00-06:00`, `06:00-12:00`, `12:00-18:00`, `18:00-23:59`) yang tidak tercantum di dokumen mana pun | TASK 100–103 |
| U-04 | Ukuran grid final & sumber batas administratif | NOT SPECIFIED — `docs/02` menyebut 250–500 m sebagai opsi; dataset memakai 500 m untuk semua tetapi 1 grid = 1 kelurahan (S-09) | TASK 011, 080–084 |
| U-05 | Skema autentikasi (JWT vs session), kebijakan password, penyimpanan `password_hash` | NOT SPECIFIED — `.env.example` menyiratkan JWT, `docs/08` TASK 050 menulis "session/token", `docs/02` #17 tidak punya kolom password | TASK 050 |
| U-06 | Scoping jurisdiksi dan fungsi (simbol `L` pada `docs/03`) | NOT SPECIFIED — tabel `users` tidak punya `polsek`/`unit_id`/`function`, sehingga akses terbatas per wilayah tidak dapat ditegakkan | TASK 051, 052 |
| U-07 | Perilaku keputusan `Modify` | NOT SPECIFIED — tidak ada tempat menyimpan isi rekomendasi hasil modifikasi dan tidak ada versioning | TASK 130 |
| U-08 | State machine setiap entitas (warning, recommendation, action, citizen report, intelligence, crime) | NOT SPECIFIED — nilai status hanya ada di data dummy, transisi yang sah tidak didefinisikan | TASK 013–014, 110–142 |
| U-09 | Cara menghitung **recall** dan **false negative** | NOT SPECIFIED — `prediction_actual` selalu menunjuk `prediction_id`, sehingga kejadian aktual yang **tidak** diprediksi tidak dapat direpresentasikan. Data dummy hanya berisi `Hit` dan `False Positive`. Padahal CLAUDE.md §19, `docs/01` §5.10, TASK 104 dan TASK 151 mewajibkan recall & FN | TASK 104, 150, 151 |
| U-10 | Kewenangan & kriteria publikasi `public_alerts` | NOT SPECIFIED — data dummy mempublikasikan 84 dari 84 warning secara 1:1 | TASK 111 |
| U-11 | Sumber konten Executive Brief & AI Assistant | NOT SPECIFIED — tidak ada entitas, tidak ada endpoint di `docs/05`, tidak ada penyedia LLM dalam stack, tidak ada task di roadmap | modul MVP #12 |
| U-12 | Penempatan modul Patrol Optimization, Community Intelligence, AI Assistant | NOT SPECIFIED — disebut di `docs/01` §3 tetapi tidak ada task apa pun di `docs/08` | — |
| U-13 | LAPOR PRESISI: identitas/autentikasi pelapor, penyimpanan bukti, cara pelapor melihat status | NOT SPECIFIED — tidak ada tabel attachment/evidence, `citizen_reports` tidak punya identitas atau token klaim, sehingga TASK 173–174 tidak dapat dirancang | TASK 171–175 |
| U-14 | Retensi data, klasifikasi kerahasiaan, aturan masking, aturan ekspor | NOT SPECIFIED (`docs/01` §19, `docs/06`) | TASK 162, 163 |
| U-15 | Lingkungan deployment dan sumber basemap/tile | NOT SPECIFIED — MapLibre memerlukan tile server; jika jaringan tertutup diperlukan tile mandiri/offline | TASK 080 |
| U-16 | Taxonomy final (5 `incident_type`, 16 `modus`, 11 `target_type`, 6 `location_type`) | NOT SPECIFIED — nilai hanya hidup di data dummy; `config/taxonomy/` masih kosong | TASK 011, 020 |
| U-17 | SLA, target performa, volume data nyata, jumlah pengguna | NOT SPECIFIED | TASK 164 |
| U-18 | Timezone & format waktu kanonik | NOT SPECIFIED — `docs/02` meminta `timestamptz`, seluruh data dummy tanpa offset dan format campur (lihat S-12) | TASK 011 |
| U-19 | Sumber, legalitas, dan lisensi data eksternal (cuaca, populasi, POI) | NOT SPECIFIED (`docs/01` §6.3) | fase analytics/ML |
| U-20 | Kontrak API: format error, pagination, filter, versioning, rate limit | NOT SPECIFIED — hanya disebut sebagai prinsip di `docs/05` | TASK 030 |
| U-21 | Detail audit: field tambahan (IP, user agent, before/after konfigurasi), sifat append-only, dan kejadian DENIED | NOT SPECIFIED — dan `docs/03` memberi Admin hak `RW` atas audit logs yang bertentangan dengan integritas audit | TASK 053, 163 |

---

## 5. TEMUAN KUALITAS DATASET DUMMY (`data/sample/`)

Seluruh angka di bawah adalah hasil verifikasi langsung atas file CSV.

| ID | Temuan | Bukti | Dampak |
|---|---|---|---|
| S-01 | `commander_decisions.decision_by` selalu bernilai `USER-DEMO-PIMPINAN`, yang tidak ada di `users.csv` (`USER-001`…`USER-006`) | 63 dari 63 baris | FK gagal pada TASK 023 |
| S-02 | Pasangan `action`/`resource_type` pada `audit_logs.csv` acak dan tidak bermakna: `LOGIN`→`evaluation` (14×), `RUN_PREDICTION`→`recommendation` (13×), `ACK_WARNING`→`dashboard` (15×) | 400 baris | Audit tidak dapat dipakai sebagai contoh jejak governance |
| S-03 | Audit mencatat aksi yang tidak dimiliki role pelaku, semuanya `SUCCESS`: `Polsek`→`APPROVE_RECOMMENDATION` (12×), `Polsek`→`RUN_PREDICTION` (13×), `Administrator`→`APPROVE_RECOMMENDATION` (12×) | ±190 baris melanggar `role_permissions.csv` | Bertentangan langsung dengan model RBAC |
| S-04 | Jumlah 5 kolom faktor ≠ `risk_score` | 1.822 dari 1.848 baris; contoh `RS-00001`: 21+16+15+14+3 = 69 vs `risk_score` = 27 | Explainability tidak dapat direkonstruksi dari data |
| S-05 | `predictions` tidak dapat di-join ke `risk_scores` pada kunci (tanggal, grid, threat, time_window) | 171 dari 180 tanpa pasangan; 9 sisanya berpasangan tetapi skornya berbeda | Memperkuat C-01: relasi risk ↔ prediction memang belum terdefinisi |
| S-06 | `forecast_horizon` hanya berisi `24h` | 180 dari 180 | Predictive heatmap NOW→+6H→+12H→+24H→+3D→+7D (`docs/01` §5.6) tidak dapat didemokan |
| S-07 | `dominant_factors` identik untuk seluruh prediksi: `"Historical hotspot; recent incidents; temporal pattern; nearby activity"`; `model_version` selalu `dummy-v1` | 180 dari 180 | WHY/explainability adalah placeholder — harus dinyatakan eksplisit di UI (CLAUDE.md §20) |
| S-08 | `prediction_actual` mengevaluasi prediksi berstatus `Draft` | 29 dari 180 | Semantik evaluasi belum ditetapkan |
| S-09 | Hanya `Hit` (73) dan `False Positive` (107); tidak ada representasi false negative | 180 baris | Recall tidak dapat dihitung (lihat U-09) |
| S-10 | `operational_actions` hanya 3 baris padahal terdapat 33 keputusan `Approved` | 3 vs 33 | Fase Operation Center (TASK 140–142) nyaris tanpa data uji |
| S-11 | 33 lokasi = 33 kelurahan, semua `grid_size_m` = 500 → "grid 500 m" sebenarnya adalah centroid kelurahan | 1 grid per kelurahan | Konsep grid (drill-down area → sub-area → grid) tidak terwakili |
| S-12 | ~~Cakupan wilayah 9 kecamatan / 9 polsek; kecamatan Pesanggrahan tidak ada~~ **SELESAI 8 Sep 2026** | 33 → 37 baris `locations.csv` | Pemilik proyek memutuskan melengkapinya. Pesanggrahan ditambahkan beserta rantai datanya oleh `scripts/tambah-pesanggrahan.py`; cakupan kini 10 kecamatan / 10 polsek |
| S-13 | Kolom `is_synthetic` hanya ada pada 6 dari 19 file dan tidak terdaftar di data dictionary | `audit_logs`, `citizen_reports`, `community_feedback`, `crime_incidents`, `predictions`, `risk_scores` | Konvensi penandaan data sintetis belum konsisten |
| S-14 | Format datetime campur: `2025-10-03T19:06` (ISO-T) pada `audit_logs`/`citizen_reports` vs `2025-12-26 16:00` (spasi) pada `commander_decisions`, `early_warnings`, `public_alerts`, `recommendations`, `operational_actions`; semuanya tanpa timezone | 9 kolom | Parser import perlu aturan tunggal (lihat U-18) |
| S-15 | `recommendations.status` menduplikasi `commander_decisions.decision` (Approved 33 / Modified 19 / Rejected 11 di kedua tabel) tanpa aturan sinkronisasi | 84 vs 63 baris (21 `Pending Review` belum berkeputusan — konsisten) | Risiko status ganda yang menyimpang |
| S-16 | `public_alerts` 1:1 dengan `early_warnings` termasuk severity `Warning`, semuanya terpublikasi | 84 vs 84 | Menyiratkan kebijakan publikasi otomatis yang belum disetujui (U-10) |
| S-17 | Satu baris `prediction_actual` dengan `actual_grid_id` kosong | 1 dari 180 | Nullable perlu dinyatakan eksplisit di schema |
| S-18 | `.DS_Store` ter-commit di root repository; `.gitignore` hanya berada di dalam subfolder paket | `git ls-files` | Kebersihan repo (bukan kebocoran data) |

**Catatan positif:** referensi `grid_id` antar file konsisten penuh (0 orphan pada crime_incidents, predictions, risk_scores, early_warnings, intelligence_reports, patrol_activity, operational_actions); rantai `prediction → warning → recommendation → decision` konsisten (0 orphan, atribut warning cocok 84/84 dengan prediksi sumbernya); rentang koordinat berada di wilayah Jakarta Selatan; distribusi jenis kejadian dan tahun (2023: 413, 2024: 369, 2025: 418) sesuai rencana split data pada `docs/01` §8.

---

## 6. KEPUTUSAN TEKNIS YANG PERLU DIKONFIRMASI

Setiap butir menyertakan rekomendasi. **Rekomendasi bukan keputusan** — semua berstatus `PROPOSED — REQUIRES USER APPROVAL`.

| ID | Keputusan | Rekomendasi | Diperlukan sebelum |
|---|---|---|---|
| D-01 | Posisi paket dalam repository | Pindahkan isi `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/` ke root repo, dan pindahkan `.gitignore` ke root; simpan PDF/gambar sumber di `docs/source/` atau `design/` | TASK 001 |
| D-02 | Duplikasi `docs/CLAUDE.md` | Hapus salinan di `docs/`, sisakan satu di root | TASK 001 |
| D-03 | Backend & migration tooling | FastAPI + SQLAlchemy 2.x + Alembic + GeoAlchemy2; package manager `uv` | TASK 001, 010 |
| D-04 | Tooling monorepo & berbagi tipe | pnpm workspaces untuk sisi TypeScript; tipe frontend digenerate dari OpenAPI FastAPI (bukan ditulis manual di `packages/shared/types`) | TASK 001 |
| D-05 | Frontend & peta | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui; MapLibre GL JS — **sumber tile perlu ditentukan pengguna** (U-15) | TASK 060, 080 |
| D-06 | Mekanisme sesi | JWT access token pendek + refresh token pada httpOnly cookie; `password_hash` memakai Argon2id | TASK 050 |
| D-07 | Strategi identitas | PK internal UUID; simpan ID dummy pada kolom `code` unik agar seed dan lampiran Taskap tetap dapat ditelusuri | TASK 011 |
| D-08 | Model lokasi | `locations` sebagai master grid dengan `geometry(Point,4326)` **dan** `geometry(Polygon,4326)` untuk sel grid; tabel transaksi menyimpan `location_id` (FK) dan boleh menyimpan `grid_id` sebagai kolom denormalisasi hanya untuk import | TASK 011 |
| D-09 | Model permission | `resource:action` + dimensi `scope` (`all` / `own_jurisdiction` / `own_function`) untuk mewujudkan simbol `L`; tambahkan atribut jurisdiksi & fungsi pada `users` | TASK 015, 051 |
| D-10 | Tempat konfigurasi threshold/bobot | File YAML pada `config/risk/` dan `config/model/` + tabel konfigurasi versioned di database; setiap perubahan tercatat di audit log | TASK 102, 110 |
| D-11 | Penanganan waktu data demo | Data dummy berhenti 2025-12-31 sedangkan tanggal sekarang 2026-08-31 — dashboard "24 jam terakhir" dan "warning aktif" akan kosong. Rekomendasi: seeder dengan opsi *date-rebase* (menggeser seluruh tanggal relatif terhadap tanggal seed) + `DEMO_CLOCK` opsional pada environment | TASK 020–023, 070 |
| D-12 | Tabel tambahan yang kemungkinan diperlukan | `attachments` (bukti LAPOR PRESISI), `boundaries` (batas administratif/grid polygon), `system_config`, dan entitas kejadian aktual untuk false negative (U-09). CLAUDE.md §14 melarang penambahan tabel tanpa persetujuan → **butuh persetujuan eksplisit** sebelum TASK 011 | TASK 011–016 |
| D-13 | Testing & CI | pytest + httpx (API), Vitest + Testing Library (web), Playwright (E2E), GitHub Actions | TASK 002 |
| D-14 | Perlakuan atas dataset dummy | Perbaiki S-01…S-08 melalui script regenerasi/normalisasi di `scripts/seed/` sebelum TASK 020, bukan menambal saat import | TASK 020 |

---

## 7. RISIKO UTAMA

| ID | Risiko | Mitigasi yang diusulkan |
|---|---|---|
| R-01 | Threshold dan bobot dari data dummy ikut mengeras menjadi "requirement" | Simpan semua angka di configuration layer (D-10); beri label `PROPOSED` di UI dan dokumen |
| R-02 | Explainability palsu — `dominant_factors` identik untuk 180 prediksi | Tandai eksplisit sebagai rule/dummy di UI sesuai CLAUDE.md §20; jangan sebut "AI menemukan pola" |
| R-03 | Klaim evaluasi model tidak sahih karena recall/FN tak terhitung (U-09) | Tetapkan definisi kejadian aktual dan struktur datanya sebelum TASK 104; sampai itu, laporkan hanya precision dan nyatakan batasannya |
| R-04 | Kebocoran data antar wilayah karena RBAC hanya berbasis role tanpa scope (U-06) | Rancang scope sejak TASK 015/051, bukan sebagai tambalan |
| R-05 | Dashboard kosong saat demo karena data dummy kadaluarsa (D-11) | Putuskan strategi waktu demo sebelum TASK 020 |
| R-06 | Audit log tidak dapat dipakai sebagai bukti governance karena seed-nya tidak koheren (S-02, S-03) | Regenerasi audit dummy dari aksi yang benar-benar sah menurut `role_permissions`, sertakan kasus `DENIED` |
| R-07 | Roadmap horizontal menunda slice end-to-end sampai sangat jauh (C-06), sehingga risiko integrasi baru terlihat terlambat | Sisipkan slice tipis (login → dashboard → crime list → map) setelah PHASE 5, sebelum melanjutkan API/UI lengkap |

---

## 8. PERTANYAAN YANG PERLU DIJAWAB PEMILIK PROYEK

Diurutkan sesuai kebutuhan. Delapan pertanyaan pertama adalah gate untuk TASK 001.

**Gate TASK 001 (bootstrap):**
1. Apakah isi paket dipindahkan ke root repository? (D-01)
2. Konfirmasi stack: Next.js + FastAPI + PostgreSQL/PostGIS + MapLibre? (D-03, D-04, D-05)
3. Mekanisme autentikasi: JWT atau session? (U-05, D-06)
4. Bahasa kanonik untuk nama kolom, nilai enum, dan label UI? (C-13)
5. Penomoran fase mana yang berlaku — `docs/08`? (C-05)
6. Metode: tetap horizontal sesuai `docs/08`, atau disisipi slice vertikal tipis? (C-06, R-07)
7. Apakah autentikasi/RBAC dinaikkan ke sebelum PHASE 4? (C-07)
8. Lingkungan deployment dan sumber tile peta? (U-15)

**Gate TASK 010–016 (database):**
9. `location_id` atau `grid_id` sebagai referensi kanonik, dan bagaimana mapping-nya? (C-02, D-08)
10. Apakah `risk_scores` menjadi input atau output prediksi? Apakah `predictions.risk_score` adalah FK? (C-01)
11. UUID atau ID string berprefix sebagai PK? (C-04, D-07)
12. Persetujuan untuk tabel tambahan `attachments`, `boundaries`, `system_config`, dan entitas kejadian aktual? (D-12)
13. Atribut jurisdiksi/fungsi pada `users` untuk mewujudkan akses `L`? (U-06, D-09)
14. Ukuran grid final dan sumber batas wilayah? (U-04)
15. Timezone kanonik (WIB/UTC) dan format waktu? (U-18)

**Gate TASK 020–023 (seed):**
16. Apakah dataset dummy diperbaiki lebih dulu (S-01…S-08)? (D-14)
17. Strategi waktu data demo? (D-11)

**Gate fase prediksi/warning/evaluasi:**
18. Threshold risk & warning definitif, atau tetap `PROPOSED` di configuration layer? (U-01, U-02)
19. Definisi target prediksi, jendela waktu, dan horizon yang wajib didukung? (U-03)
20. Bagaimana false negative direpresentasikan agar recall dapat dihitung? (U-09)
21. Siapa berwenang mempublikasikan `public_alerts` dan pada severity berapa? (U-10)
22. Bagaimana keputusan `Modify` disimpan? (U-07)
23. Sumber konten Executive Brief — LLM atau template rule? (U-11)

---

## 9. KESIMPULAN & LANGKAH BERIKUTNYA

Dokumentasi **belum layak dikunci (locked)**. Prinsip dan arah produk sudah solid, tetapi 7 konflik blocker dan 8 requirement blocker harus dijawab sebelum implementasi dimulai, agar tidak ada requirement yang diasumsikan diam-diam (CLAUDE.md §28).

Rekomendasi urutan tindakan:

1. Pemilik proyek menjawab pertanyaan **1–8** (gate TASK 001).
2. Setelah dijawab, dokumen yang terdampak diperbarui — bukan kode: `docs/03` (matriks vs katalog permission), `docs/05` (kelompok endpoint yang hilang + konvensi), `docs/07` (daftar dokumen + posisi repo), dan penyelarasan penomoran fase pada `CLAUDE.md` §27 / `docs/01` §16 / `docs/08`.
3. Baru kemudian TASK 001 — Initialize Repository dijalankan.

**Tidak ada kode, schema, migration, atau database yang dibuat pada task ini. Pekerjaan dihentikan di sini sesuai instruksi TASK 000.**
