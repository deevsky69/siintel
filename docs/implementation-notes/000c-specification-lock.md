# SPECIFICATION LOCK — HASIL PHASE 0

Tanggal: 2026-08-31
Dasar mandat: instruksi pengguna (*autonomous technical lead*) + `CLAUDE.md` §40:

```text
Audit → Resolve technical decisions → Update documentation → Lock specification → TASK 001
```

Dokumen ini menyatakan **apa yang sudah terkunci**, **apa yang masih terbuka**, dan **task mana yang terblokir**.

---

## 1. RINGKASAN

| | Jumlah |
|---|---|
| Konflik antar dokumen dari audit (C-01…C-14) | 14 → **13 selesai**, 1 sebagian (C-08) |
| Keputusan teknis dieksekusi (`TECHNICAL DECISION`) | 21 dari 22 SDL |
| Terblokir keputusan bisnis/kebijakan | 1 SDL + 17 butir requirement |
| Dokumen diperbarui | 8 (`docs/01`–`docs/08`) + README + `.env.example` + struktur repo |
| Source code dibuat | **0** — PHASE 0 tidak menulis kode |

**Status: PHASE 0 selesai. TASK 001 dapat dimulai.** Blocker yang tersisa memblokir task tertentu di
PHASE 3, 8, 10, 11, 13, 16, dan 17 — bukan bootstrap.

---

## 2. YANG SUDAH TERKUNCI

### 2.1 Struktur & tooling

| Keputusan | Hasil |
|---|---|
| Posisi paket | Dipindahkan ke root repository dengan `git mv` (riwayat terjaga). Folder `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/` dihapus setelah kosong. |
| Duplikat aturan kerja | `docs/CLAUDE.md` dihapus — isinya identik dengan `CLAUDE.md` root (keduanya sudah versi baru 1399 baris). Satu sumber kebenaran. |
| Dokumen sumber | PDF → `docs/source/`; `GAMBARAN WEBSITE.png` → `design/gambaran-website.png`. |
| Kebersihan repo | `.DS_Store` dikeluarkan dari indeks; `.gitignore` dipindah ke root dan diperluas (Next.js, pytest, ruff, playwright). |
| Stack | Dikonfirmasi apa adanya dari `docs/01` §10. |
| Toolchain | SQLAlchemy 2.x + Alembic + GeoAlchemy2, `uv`, pnpm workspaces, pytest/Vitest/Playwright. |
| Berbagi tipe | Tipe TS digenerate dari OpenAPI backend; `packages/shared/types` bukan tulisan tangan. |

### 2.2 Model data

| Konflik | Penyelesaian |
|---|---|
| **C-02** `location_id` vs `grid_id` | `locations` jadi master; `grid_id` kunci alami `UNIQUE`; tabel transaksi memakai FK `location_id`; kecamatan/kelurahan tidak diduplikasi. Sesuai `CLAUDE.md` §19. |
| **C-01** risk vs prediction | Dua layer berbeda horizon: `risk_scores` = risiko berjalan (layer *Current Risk*), `predictions` = perkiraan ke depan dan satu-satunya sumber warning/recommendation. Penelusuran opsional lewat `baseline_risk_score_id`. |
| **C-03** ERD vs dictionary | `citizen_reports.location_id` (nullable) dan `operational_actions.created_by` ditambahkan. |
| **C-04** tipe PK | UUID sebagai PK + kolom `code` unik menyimpan ID dummy (`INC-00001`) untuk traceability Taskap. |
| U-09 false negative | `prediction_actual.prediction_id` nullable + `actual_incident_id` + `match_type = FALSE_NEGATIVE`, dengan CHECK bersyarat. Recall menjadi dapat dihitung (`CLAUDE.md` §26). |
| U-07 keputusan `Modify` | `commander_decisions.modified_text`; rekomendasi asli tidak ditimpa sehingga jejak AI vs manusia utuh. |
| S-15 status ganda | `recommendations.status` adalah cerminan; sumber kebenaran tetap `commander_decisions`. |
| S-04 faktor risiko | Faktor = sub-skor 0–100; `risk_score = round(Σ(bobot × faktor))` dengan bobot dari `config/risk/` dan `weights_version` tercatat. |
| S-07 explainability | `dominant_factors` menjadi `jsonb` `{factor, contribution, source}` dengan `source ∈ {RULE, MODEL}`; UI wajib menampilkan sumbernya. |
| U-18 waktu | Simpan `timestamptz` (UTC), tampilkan WIB; jendela waktu half-open `[start, end)`; `window_start`/`window_end` menemani label `time_window`. |
| S-06 horizon | Enum `6H,12H,24H,3D,7D`. |
| C-13 bahasa | Identifier & enum tersimpan Inggris `UPPER_SNAKE`; label UI Bahasa Indonesia; nomenklatur kedinasan tidak diterjemahkan; pemetaan di `config/taxonomy/`. |
| audit | `result ∈ {SUCCESS, DENIED, FAILED}`, `detail jsonb`, append-only. |

**Tidak ada tabel baru** yang ditambahkan (`CLAUDE.md` §37). Kebutuhan attachment, batas wilayah poligon,
dan tabel konfigurasi runtime sengaja ditunda sampai requirement-nya jelas.

### 2.3 Keamanan & API

| Keputusan | Hasil |
|---|---|
| Autentikasi | JWT access token + refresh token pada cookie `httpOnly`; Argon2id; `users.password_hash` ditambahkan. |
| Otorisasi | Katalog `resource:action` (22 resource) + `role_permissions.scope` (`ALL`/`OWN_JURISDICTION`/`OWN_FUNCTION`). |
| Urutan pembangunan | `030 → 050–053 → 031–040`: middleware otorisasi & audit ada sebelum API domain (`CLAUDE.md` §21). |
| Kontrak API | Versi `/api/v1`, format error baku + `request_id`, pagination baku, filter baku, permission per endpoint. |
| Kebocoran keberadaan data | Resource di luar scope dijawab `404`, bukan `403`. |
| Keputusan komandan | Satu endpoint `POST /recommendations/{id}/decisions` menggantikan tiga endpoint aksi. |
| Warning | Endpoint `resolve` ditambahkan; `acknowledged_by/at` dan `resolved_by/at` masuk schema. |
| Audit | Tidak ada endpoint tulis/hapus audit di kontrak API. |

### 2.4 Metodologi

| Konflik | Penyelesaian |
|---|---|
| **C-05** penomoran fase | `docs/08` (= `CLAUDE.md` §38) kanonik; `docs/01` §16 menjadi tahapan konseptual + tabel pemetaan. |
| **C-06** vertical vs horizontal | Urutan fase `docs/08` dipertahankan; intent vertical slice dipenuhi lewat aturan CHECKPOINT (checkpoint hanya boleh diklaim bila slice benar-benar berjalan end-to-end). |
| **C-07** authz sebelum RBAC | Urutan eksekusi PHASE 4/5 disesuaikan tanpa mengubah nomor task. |
| **C-11** pipeline data | Dipisah menjadi pipeline ingestion (canonical `CLAUDE.md` §18) dan pipeline analitik. |
| **C-09/C-10/C-12/C-14** | Kontrak API dilengkapi; struktur folder, README, dan peran `packages/shared` diperbaiki. |

### 2.5 Kualitas data dummy

Tidak diperbaiki sekarang (PHASE 0 bukan tempatnya), tetapi **12 acceptance criteria (A-1…A-12)**
sudah ditulis ke `docs/08` PHASE 3 dan seed bersifat *fail-fast*. Temuan yang ditutup: orphan FK
`decision_by` (63/63), faktor risiko menyimpang (1.822/1.848), audit `SUCCESS` tanpa permission (±190),
horizon tunggal, WHY identik 180/180, action 3 vs 33 keputusan approved, dan evaluasi atas prediksi `DRAFT`.

Tanggal historis **tidak digeser** (akan merusak split ML `docs/01` §8); dipakai waktu acuan `DEMO_REFERENCE_TIME`.

---

## 3. YANG MASIH TERBLOKIR — BUTUH KEPUTUSAN PENGGUNA

Sesuai `CLAUDE.md` §2C/§2D dan §35, butir berikut **tidak** diputuskan sendiri.

### 3.0 B-1 — KEPUTUSAN PENGGUNA: OPSI C (hybrid)

Ditetapkan pemilik proyek pada 2026-08-31. Status: **FINAL untuk pengembangan, target produksi masih terbuka.**

Konsekuensi yang berlaku sejak sekarang:

1. **Pengembangan** memakai tile server lokal yang dijalankan dari `infra/docker` — tidak bergantung pada internet.
2. Sumber peta **selalu** dibaca dari environment (`MAP_STYLE_URL`, `MAP_TILE_URL`, `NEXT_PUBLIC_MAP_STYLE_URL`).
   Tidak boleh ada URL peta yang di-hardcode di source code, agar target produksi dapat diganti tanpa mengubah kode.
3. Frontend tidak memuat aset peta dari CDN eksternal; seluruh dependensi peta di-*bundle* atau dilayani lokal.
4. **Masih terbuka (`NOT SPECIFIED`):** lingkungan produksi final (on-premise/jaringan tertutup vs cloud),
   sumber tile produksi, dan kewajiban atribusi/lisensi data peta. Diputuskan paling lambat sebelum PHASE 16.
5. PHASE 8 (TASK 080–084) **tidak lagi terblokir**.

### 3.1 Blocker berdampak dekat

| # | Keputusan | Memblokir | Opsi | Rekomendasi teknis |
|---|---|---|---|---|
| ~~**B-1**~~ | ~~Lingkungan deployment & sumber tile peta~~ (U-15) | — | — | **DIPUTUSKAN PENGGUNA 2026-08-31: opsi C (hybrid).** Lihat §3.0 |
| **B-2** | **Kewenangan approve & publikasi** (U-06, U-10) — pertanyaan P-1…P-7 `docs/03` §4 | TASK 051, 111, 130 | Matriks `PROPOSED` di `docs/03` §3 dapat disetujui apa adanya, direvisi, atau diganti | Setujui sebagai baseline pengembangan, tandai final setelah SOP terbit |
| **B-3** | **Taksonomi final** (U-16) | TASK 011, 020 | Kunci daftar nilai sekarang, atau biarkan configurable sampai data resmi masuk | Biarkan configurable di `config/taxonomy/`; kunci hanya `incident_type` |
| **B-4** | **Ukuran grid & batas wilayah** (U-04) | TASK 011, 080–084 | (A) tetap 1 grid = 1 kelurahan; (B) grid 250–500 m sesungguhnya + sumber batas resmi | (B) untuk PoC hanya bila sumber batas tersedia; bila tidak, (A) dengan penamaan yang jujur ("kelurahan", bukan "grid") |

### 3.2 Blocker fase analitik

| # | Keputusan | Memblokir |
|---|---|---|
| **B-5** | Bobot risk score final (U-02) | TASK 102 + constraint bobot |
| **B-6** | Threshold early warning & batas kelas risiko (U-01) | TASK 110 |
| **B-7** | Definisi target prediksi + aturan pencocokan evaluasi (U-03) | TASK 100–104, 150–151 |
| **B-8** | State machine operasional resmi (U-08) | TASK 110–142 |

Sampai B-5…B-7 dijawab, seluruh angka risiko/prediksi/evaluasi wajib ditandai `DEMO / PROPOSED`
dan tidak boleh disajikan sebagai validasi model (`CLAUDE.md` §11, §26).

### 3.3 Blocker kebijakan/legal

| # | Keputusan | Memblokir |
|---|---|---|
| **B-9** | Kebijakan kredensial: panjang/rotasi password, MFA, ketersediaan SSO Polri (U-05) | TASK 050 (default teknis sudah tersedia) |
| **B-10** | Retensi & klasifikasi data, aturan masking/ekspor (U-14) | TASK 162–163 |
| **B-11** | Identitas pelapor, penyimpanan bukti, dan cara pelapor melihat status LAPOR PRESISI (U-13) | PHASE 17 |
| **B-12** | Sumber konten Executive Brief — template rule atau model bahasa (U-11) | modul MVP #12 |
| **B-13** | Sumber data eksternal yang disetujui: cuaca, populasi, POI (U-19) | fase analytics/ML |
| **B-14** | SLA, volume data, jumlah pengguna (U-17) | TASK 164 |
| **B-15** | Penempatan modul Patrol Optimization & AI Assistant (U-12) | — |

---

## 4. PERTANYAAN YANG PERLU DIJAWAB SEKARANG

**B-1 sudah dijawab (opsi C).** Tidak ada keputusan pengguna yang tertunda untuk pekerjaan saat ini.

Jadwal keputusan berikutnya:

| Butir | Perlu dijawab sebelum |
|---|---|
| B-2 kewenangan approve/publish, B-3 taksonomi final | PHASE 2 (TASK 011/015) — agar enum & permission tidak perlu dimigrasikan ulang |
| B-4 ukuran grid & batas wilayah | TASK 080 |
| B-5 bobot risiko, B-6 threshold warning, B-7 definisi target prediksi, B-8 state machine | PHASE 10 |
| B-9 kebijakan kredensial | TASK 050 |
| B-10 retensi/klasifikasi, B-14 SLA | PHASE 16 |
| B-11 LAPOR PRESISI | PHASE 17 |
| Target produksi & sumber tile final (sisa B-1) | PHASE 16 |

TASK 001 (bootstrap) dan TASK 002 (development environment) **tidak menunggu satu pun** dari butir di atas.

---

## 5. VERIFIKASI

- Tidak ada file source code, migration, atau database yang dibuat pada PHASE 0.
- Perubahan tercatat sebagai rename di Git sehingga riwayat file dokumentasi dan dataset terjaga.
- Tidak ada secret yang ditambahkan; `.env.example` hanya berisi placeholder dan `JWT_SECRET` dibiarkan kosong.
- `data/sample/` tidak diubah sama sekali pada fase ini.
