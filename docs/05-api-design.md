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
| GET | `/users` | `user:read` — ✅ **ADA** |
| PATCH | `/users/{code}` | `user:manage` — ✅ **ADA** |
| GET | `/roles` | `role:read` — ✅ **ADA** |
| POST | `/users` | `user:manage` — **belum**, dan sengaja: membuat pengguna menuntut penetapan password, yang jalurnya terpisah (CLI di server) |
| PUT | `/roles/{id}/permissions` | `role:manage` — **belum**, dan sebaiknya tidak dibuat: daftar permission berasal dari `config/rbac/permissions.yaml` dan diselaraskan seed. Menyuntingnya lewat API membuat berkas itu berhenti menjadi sumber kebenaran |
| GET | `/audit-logs` | `audit:read` — ✅ **ADA** |
| GET | `/audit-logs/summary` | `audit:read` — ✅ **ADA** |

Tidak ada `POST`, `PATCH`, maupun `DELETE` pada jejak audit, dan **ketiadaannya adalah
sifat yang dijaga**, bukan pekerjaan yang belum sempat: catatan yang dapat disunting bukan
bukti (CLAUDE.md §29). `test_the_audit_trail_offers_no_way_to_write` memeriksanya terhadap
skema OpenAPI aplikasi yang benar-benar berjalan.
| GET | `/permissions` | `role:read` |
| GET | `/audit-logs` | `audit:read` |
| GET/PUT | `/config/risk-weights`, `/config/warning-thresholds`, `/config/taxonomy` | `config:read` / `config:manage` — **belum dibuat** |
| GET | `/risk-scores/config` | `config:read` — ✅ **ADA** |
| POST | `/risk-scores/run` | `risk_score:run` — ✅ **ADA** |
| POST | `/predictions/run` | `prediction:run` — ✅ **ADA** |
| POST | `/predictions/{code}/publish` | `prediction:publish` — ✅ **ADA** |
| POST | `/crimes` | `crime:write` — ✅ **ADA** |
| POST | `/crimes/{code}/status` | `crime:write` — ✅ **ADA** |
| POST | `/citizen-reports/{code}/status` | `citizen_report:write` — ✅ **ADA** |
| GET | `/police-units` | `police_unit:read` — ✅ **ADA** |

Dua endpoint konfigurasi di atas **sengaja berbeda**, bukan duplikasi. `/config/risk-weights`
adalah **pengelolaan** berkas konfigurasi, lengkap dengan `PUT` dan `config:manage` — belum
dibuat, dan menyuntingnya lewat API berarti mengubah bobot yang sedang dirujuk baris
`risk_scores`, yang justru dilarang oleh mekanisme versi.

`/risk-scores/config` menyajikan konfigurasi **sebagaimana dipakai mesin penilaian**: versi
aktif, profil beserta bobotnya, jenis ancaman yang dicakup, dan faktor mana yang benar-benar
dapat disimpan pada tabel. Yang terakhir itu tidak ada di berkas konfigurasi — ia sifat
schema — sehingga tidak dapat dijawab oleh endpoint pengelolaan config.

Audit: `CREATE_USER`, `UPDATE_USER`, `CHANGE_ROLE_PERMISSION`, `CHANGE_CONFIGURATION` (menyimpan nilai sebelum/sesudah pada `detail`).
Tidak ada endpoint tulis/hapus untuk `/audit-logs`.

### 2.3 Data Kamtibmas

| Method | Path | Permission |
|---|---|---|
| GET | `/locations`, `/locations/{id}` | `location:read` |
| GET | `/police-units` | `police_unit:read` |
| POST/PATCH | `/locations`, `/locations/{id}` | `location:write` |
| GET | `/crimes`, `/crimes/{id}` | `crime:read` |
| POST/PATCH | `/crimes`, `/crimes/{id}` | `crime:write` |
| GET | `/crimes/export` | `crime:export` |
| GET/POST | `/intelligence-reports` | `intelligence:read` / `intelligence:write` — ✅ **ADA** |
| GET/POST | `/patrol-activities` | `patrol:read` / `patrol:write` |
| GET/POST | `/police-units` | `police_unit:read` / `police_unit:write` |

Audit: `VIEW_SENSITIVE_DATA` untuk detail kejadian, `IMPORT_DATA` untuk impor.

### 2.4 Peta

| Method | Path | Permission | Keterangan |
|---|---|---|---|
| GET | `/map/historical` | `map:read`, `crime:read` | ✅ **ADA** — layer historis: cacah per kecamatan **dan** titik lokasi; parameter `months` |
| GET | `/map/incidents` | `map:read` | ~~Titik kejadian (GeoJSON)~~ — digabung ke `/map/historical` |
| GET | `/map/historical-heatmap` | `map:read` | ~~Agregasi historis per grid~~ — digabung ke `/map/historical` |
| GET | `/map/current-risk` | `map:read`, `risk_score:read` | Layer risiko berjalan |
| GET | `/map/predictive-heatmap` | `map:read`, `prediction:read` | Layer prediktif; parameter `horizon` |
| GET | `/map/area/{kecamatan}` | `map:read` | Rincian wilayah: ancaman berperingkat, jam rawan, riwayat kejadian, peringatan aktif, prediksi + WHY |
| GET | `/map/grid/{location_id}` | `map:read` | Detail satu sel grid — **belum dibuat** |

`/map/current-risk` dan `/map/predictive-heatmap` dipisah karena keduanya layer berbeda (docs/04).

**TECHNICAL DECISION — dua endpoint historis digabung menjadi satu.** Rancangan awal
memisahkan `/map/incidents` (titik, GeoJSON) dari `/map/historical-heatmap` (agregasi per
grid). Keduanya digabung menjadi `GET /map/historical` dengan dua alasan:

1. **Keduanya selalu digambar bersamaan, pada jendela waktu yang sama.** Dipisah, keduanya
   dapat menjawab jendela yang berbeda — titik untuk 12 bulan di atas bidang warna untuk 3
   bulan — dan tidak ada di layar yang akan menunjukkan bahwa itu terjadi. Satu endpoint
   membuat ketidakcocokan itu mustahil, bukan sekadar tidak mungkin terjadi.
2. **Satuan "per grid" salah untuk layer ini**, dengan alasan yang sama yang membuat
   `/map/area` memakai kecamatan: sel grid terlalu sempit untuk membawa cacah yang bermakna.
   Bidang warna karena itu per kecamatan, dan titiknya per **lokasi**.

Titik berada di koordinat `locations`, **bukan** di tempat kejadian sebenarnya:
`crime_incidents` menyimpan `location_id` dan tidak menyimpan koordinatnya sendiri, sehingga
seluruh kejadian pada satu lokasi menumpuk di satu titik. Respons menyatakan ini pada
`aggregation_basis`; menyembunyikannya akan membuat titik terbaca sebagai TKP.

Bentuk GeoJSON tidak dipakai — tidak ada consumer yang membutuhkannya, dan peta digambar
sebagai SVG tanpa pustaka peta.

Responsnya **tidak pernah membawa `risk_class` maupun `risk_score`.** Yang dicacah adalah
kejadian, bukan risiko; memberi kelas pada cacah mentah akan menyatakan wilayah dengan
kejadian terbanyak sebagai wilayah paling rawan, dan itu tidak dapat disimpulkan tanpa
pembobotan maupun normalisasi terhadap luas dan penduduk. `test_historical_never_reports_a_risk_class`
menjaganya.

**Perubahan setelah implementasi (TASK 082–084):** satuan rincian yang benar-benar dipakai
layar adalah **kecamatan**, bukan sel grid. Pengguna bertanya "apa ancaman di Tebet",
bukan "apa ancaman di sel GRD-017"; satu sel juga terlalu sempit untuk membawa riwayat
yang bermakna. `/map/grid/{location_id}` tetap dicantumkan untuk kebutuhan analitik lanjutan.

`/map/predictive-heatmap` **tidak membawa `risk_class` sama sekali.** `predictions` tidak
menyimpan kelas, dan memberinya kelas berarti menerapkan ambang `config/risk/warning-thresholds.yaml`
yang masih berstatus `DEMO / PROPOSED` (U-01). Layer prediktif karena itu menyajikan skor
mentah dan menyatakannya terbuka lewat `basis`.

### 2.5 Analitik

| Method | Path | Permission | Status |
|---|---|---|---|
| GET | `/analytics/crime-pattern-dna` | `analytics:read` | ✅ **ADA** |
| GET | `/analytics/trend` | `analytics:read` | ✅ **ADA** |
| GET | `/analytics/time-pattern` | `analytics:read` | ✅ **ADA** — matriks hari × jam |
| GET | `/analytics/spatial-pattern` | `analytics:read` | ✅ **ADA** — perbandingan antarkecamatan |
| GET | `/analytics/location-profile/{location_id}` | `analytics:read` | belum |
| GET | `/analytics/export` | `analytics:export` | belum |

Setiap respons analitik menyertakan `source` (rentang data & jumlah baris) agar dapat ditelusuri
kembali ke data sumber (TASK 090–094).

**Crime Analytics dan Crime Pattern DNA sengaja tidak digabung**, meskipun keduanya membaca
`crime_incidents` dan berbagi pembantu agregasi yang sama (`api/analysis.py`). Sudut pandangnya
berbeda: DNA memprofilkan **satu jenis gangguan** pada lima dimensinya, sedangkan Analytics
**membandingkan lintas jenis dan lintas waktu**. `/analytics/time-pattern` menghasilkan matriks
hari × jam — perkalian dua sebaran yang pada DNA hanya tersedia terpisah — dan
`/analytics/spatial-pattern` **menolak** parameter `threat_type`, sebab menyaringnya ke satu
jenis akan mengubahnya menjadi dimensi WHERE milik DNA.

Angka keduanya wajib sama untuk pertanyaan yang sama; dijaga
`test_analytics_agrees_with_crime_pattern_dna_on_the_same_numbers`.

**Catatan path (TASK 090).** Implementasi Crime Pattern DNA sempat dibangun pada `/patterns/dna`
— nama yang saya sebut keliru pada instruksi, bukan yang tertulis di kontrak ini. Kode
disesuaikan ke kontrak, bukan sebaliknya: pengelompokan di bawah `/analytics` sejalan dengan
permission yang dipakainya (`analytics:read`), dan kontrak di sini tidak sedang keliru.
Ini berbeda dari perubahan `/map/area/{kecamatan}` pada §2.4, yang mengubah kontrak justru
karena premis kontraknya yang terbukti tidak tepat setelah dibangun.

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

**Setelah implementasi (TASK 130):** rekomendasi yang sudah diputus **tidak dapat diputus
ulang** — permintaan kedua dijawab `409 CONFLICT`. Memutus dua kali mengaburkan siapa yang
memutuskan apa; perubahan pendirian adalah keputusan baru atas rekomendasi baru, bukan
penimpaan. `MODIFIED` tanpa `modified_text` dijawab `422 BUSINESS_RULE_VIOLATION`, dan
`recommendations.recommendation_text` **tidak pernah** ditimpa (U-07): respons membawa
`original_recommendation` bersama `modified_text` agar layar dapat menyandingkannya.
Rekomendasi di luar cakupan wilayah pengguna dijawab `404`, bukan `403`.

`GET /recommendations/{id}/decisions` belum dibuat; riwayat diambil lewat
`GET /commander-decisions`, yang sudah menegakkan cakupan wilayah dan fungsi.

> **`GET /police-units` (TASK 131).** `police_units.jurisdiction` berisi nama polsek **atau**
> nama Polres untuk satuan yang bertugas lintas polsek. Menyaring dengan pencocokan tepat akan
> menyembunyikan satuan tingkat Polres dari pengguna polsek — padahal satuan itu justru
> bertugas di wilayahnya juga, dan menyembunyikannya membuat petugas mengira satuan itu tidak
> ada. Karena itu satuan tingkat Polres dikenali dari datanya sendiri: `jurisdiction` yang
> bukan salah satu polsek pada tabel `locations`. Tidak ada nama Polres yang ditanam di kode.
> Aturannya dinyatakan pada `scope_basis` di respons, bukan disembunyikan.
>
> Pada data berjalan: Command Center 6 satuan, Polsek Tebet 4 (miliknya + tiga tingkat Polres),
> Fungsi RESKRIM 1.

### 2.9 Operasi

| Method | Path | Permission |
|---|---|---|
| GET | `/operations`, `/operations/{id}` | `operation:read` |
| POST | `/operations` | `operation:write` |
| GET | `/operations/pending-decisions` | `operation:read` |
| POST | `/operations/{code}/result` | `operation:write` |
| PATCH | `/operations/{id}` | `operation:write` — **belum dibuat** |

`POST /operations` menolak keputusan yang tidak berstatus `APPROVED`/`MODIFIED` → `422 BUSINESS_RULE_VIOLATION`.

**Setelah implementasi (TASK 131):**

Badan permintaan memakai **kode**, bukan UUID: `{decision_code, unit_code, start_at?, notes?}`.
Seluruh API lain juga memakai kode pada permukaannya, dan kode dapat dibaca manusia saat paparan.

`location_id` **tidak** diterima dari klien. Lokasi penugasan diambil dari prediksi yang
mendasari rekomendasi, agar tindakan tetap dapat ditelusuri ke wilayah yang diprediksi dan tidak
dapat diarahkan ke wilayah lain lewat permintaan.

Satu keputusan menghasilkan **paling banyak satu** tindakan; permintaan kedua dijawab `409`.

`POST /operations/{code}/result` menerima `{status, result, end_at?}` dengan `status` berupa
`COMPLETED` atau `CANCELLED`. Bila `end_at` tidak lebih akhir daripada `start_at`, permintaan
dijawab `422` — bukan diperbaiki diam-diam. Keadaan ini lazim saat demo karena jam acuan beku
(SDL-16), dan menambahkan durasi karangan agar constraint lolos akan memasukkan angka palsu ke
dalam data yang kelak dipakai evaluasi. Tindakan yang sudah berstatus akhir dijawab `409`.

`GET /operations/pending-decisions` menampilkan keputusan `APPROVED`/`MODIFIED` yang belum
memiliki tindakan — keadaan "sudah diputus tetapi tidak pernah dijalankan", yang sebelumnya
tidak dapat dilihat dari mana pun.

Audit: `CREATE_OPERATION`, `RECORD_OPERATION_RESULT` (termasuk `result = FAILED` untuk transisi
yang ditolak), resource `operation`.
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

### 2.11b Kanal publik LAPOR PRESISI — **tanpa autentikasi**

| Method | Path | Permission |
|---|---|---|
| GET | `/public/report-options` | — ✅ **ADA** |
| POST | `/public/citizen-reports` | — ✅ **ADA** |

**Keputusan pemilik proyek, 2 September 2026.** Bentuknya mengikuti `docs/14` §3:
pengiriman **tanpa akun**, dan nomor tiket sebagai satu-satunya penanda yang dipegang
pelapor. Ini satu-satunya bagian API yang dilayani tanpa autentikasi, sehingga batasnya
ditulis di sini secara lengkap:

| Batas | Alasannya |
|---|---|
| **Field tak dikenal ditolak** (`extra="forbid"`), bukan diabaikan | Pengirim yang menyertakan nama atau nomor telepon menerima penolakan yang menyebut fieldnya. Membuang diam-diam terasa lebih ramah tetapi menyesatkan orang yang menyerahkan datanya: ia menerima keberhasilan dan mengira namanya tersimpan |
| **`status` selalu `RECEIVED`; `urgency_score` dan `verification_score` tidak diterima** | Keduanya penilaian petugas. Membiarkan pelapor mengisinya berarti membiarkan siapa pun menaikkan prioritas laporannya sendiri |
| **Kategori dari daftar tertutup** `citizen_report_categories` | Isian bebas memecah analisis pola dengan dua ejaan untuk satu hal, dan pada kanal publik ejaannya pasti bermacam-macam |
| **Koordinat dari master lokasi**, pelapor hanya memilih kecamatan | Meminta koordinat kepada pelapor berarti menerima titik yang tidak dapat diperiksa siapa pun. Ketepatannya sebatas kecamatan, dan respons menyatakannya pada `coordinate_basis` |
| **Pembatas laju 10 kiriman/jam/alamat IP** → `429` | Kolom teks yang dapat diisi tanpa akun adalah tempat paling mudah membanjiri basis data. Angkanya longgar: satu kantor dapat berbagi satu IP |
| **Waktu kejadian ≤ 30 hari** | Laporan yang lebih lama bukan laporan kamtibmas yang dapat ditindak; pesan penolakannya mengarahkan ke Polsek setempat |
| **`GET /public/report-options` hanya mengembalikan pilihan isian** | Kanal publik tidak boleh menjadi jendela ke dalam sistem. Ada test yang mengunci daftar field responsnya |

Jejak auditnya dicatat dengan **`user_id` kosong** — memang tidak ada pengguna di balik
peristiwa ini, dan mengisinya dengan akun sistem akan membuat audit menyatakan sesuatu yang
tidak terjadi.

> **Masih `NOT SPECIFIED` (U-13):** identitas pelapor, lampiran bukti (foto/video/audio),
> dan cara pelapor memantau status laporannya sendiri. Kanal di atas sengaja dirancang agar
> **tidak menuntut** satu pun dari ketiganya, sehingga keputusan kebijakannya tetap utuh di
> tangan pemilik proyek. Aplikasi Android LAPOR PRESISI (PHASE 17) tetap direncanakan
> terpisah.

### 2.12 Dashboard & Executive Brief

| Method | Path | Permission |
|---|---|---|
| GET | `/dashboard/summary` | `dashboard:read` |
| GET | `/dashboard/trends` | `dashboard:read` |
| GET | `/dashboard/active-warnings` | `dashboard:read`, `warning:read` |
| GET | `/dashboard/leadership` | `dashboard:read` — ✅ **ADA** |

**`/dashboard/leadership` (TASK 150).** Permintaan pemilik proyek, 2 September 2026: layar
beranda yang tersusun mengikuti urutan pertanyaan seorang pimpinan, bukan urutan
ketersediaan data. Satu endpoint membawa tujuh blok karena ketujuhnya dibaca bersamaan pada
satu layar, dan blok yang dipisah dapat menjawab jendela waktu yang berbeda tanpa apa pun di
layar yang menunjukkannya.

Empat hal pada kontraknya yang menentukan cara membacanya:

1. **`reports_24h` mencacah tiga jenis catatan terpisah** — `crime_incidents`,
   `intelligence_reports`, `citizen_reports` — beserta totalnya. Menyajikan total saja akan
   membuat pembaca menyimpulkan hal yang berbeda dari yang dihitung. `intelligence_reports`
   dicacah per **hari** karena tabelnya hanya menyimpan `report_date` tanpa jam; responsnya
   membawa `intelligence_date` dan menyatakan hal itu pada `basis`.

2. **`citizen_reports` tanpa `location_id` tidak dibuang.** Sebagian laporan masyarakat
   tidak punya lokasi yang cocok dengan master lokasi. Bagi pengguna tanpa batas wilayah
   laporan itu tetap dicacah dan jumlahnya disebut terpisah
   (`citizen_reports_without_location`, `unattributed_reports`); bagi pengguna ber-cakupan
   wilayah ia tidak ditampilkan, karena tidak dapat dipastikan berada di wilayahnya.
   `JOIN` biasa akan membuangnya untuk semua orang, dan selisihnya tidak akan terlihat.

3. **`area_status` memetakan EMPAT kelas risiko ke TIGA nama status** (Aman/Waspada/Siaga),
   dan pemetaannya dibaca dari `config/risk/warning-thresholds.yaml` blok
   `leadership_display`. Responsnya selalu membawa `mapping` dan
   `mapping_status: PROPOSED`. **REQUIRES USER APPROVAL (U-22)** — lihat catatan di bawah.
   Skor kecamatan memakai definisi yang sama dengan `/map/current-risk`, yaitu sel
   tertinggi, dijaga `test_area_status_follows_the_same_definition_the_map_uses`.

4. **`top_report_areas` memeringkat volume laporan, bukan risiko.** Responsnya tidak
   membawa `risk_score` maupun `risk_class` sama sekali, dan tingkatnya
   (Kritis/Sedang/Rendah) relatif terhadap wilayah dengan laporan terbanyak pada jendela
   yang tampil. `policy.recommendations` seluruhnya berlabel `source: RULE`.

> **REQUIRES USER APPROVAL (U-22): pemetaan status wilayah.** Nama Aman/Waspada/Siaga
> diminta pemilik proyek; sistem memiliki empat kelas risiko sedangkan namanya tiga, jadi
> dua kelas harus digabung dan penggabungan itu mengubah makna. Yang dipakai sekarang
> `HIGH + CRITICAL -> SIAGA`, dipilih karena kesalahan kedua arah tidak sepadan:
> menggabungkan dari bawah akan menyebut wilayah `MODERATE` sebagai "Aman". Belum
> disetujui, dan layar menyatakannya.

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


---

## 8. CATATAN PENEGAKAN PADA `PATCH /users/{code}`

Empat penolakan ditegakkan endpoint ini, dan ketiganya diperiksa **terhadap keadaan basis
data**, bukan terhadap nama peran — sehingga tetap benar bila nama peran berubah atau
`config/rbac/permissions.yaml` disesuaikan.

| Keadaan | Jawaban | Alasan |
|---|---|---|
| Badan memuat bidang kredensial | `400` | Password hanya ditetapkan lewat CLI di server (TASK 050). Bidang lain yang tak dikenal diabaikan diam-diam; yang menyerupai kredensial **ditolak dengan tegas** supaya kekeliruannya terlihat |
| Pengguna mengubah perannya sendiri | `409` | Tanpa ini, seorang Administrator dapat mengangkat dirinya menjadi Pimpinan dan seluruh pemisahan kewenangan runtuh |
| Perubahan menghabiskan pemegang `commander_decision:approve` yang masih aktif | `409` | Berlaku untuk pemindahan peran **maupun** penonaktifan akun: keduanya mematikan rantai persetujuan dengan cara yang sama persis |
| Peran ber-cakupan diberikan tanpa atributnya | `400` | Akun `OWN_JURISDICTION` tanpa `polsek` akan ditolak setiap endpoint ber-cakupan dan tampak seperti sistem rusak |

Audit `UPDATE_USER` memuat nilai sebelum dan sesudah untuk keempat bidang yang boleh
berubah. **Nilai bidang kredensial tidak pernah masuk ke sana** — hanya namanya, dan hanya
pada catatan penolakan.
