# TASK 000 — TINDAK LANJUT: GATE ANSWERS & SPECIFICATION DECISION LOG

> ## STATUS UPDATE — dokumen ini sudah dieksekusi
>
> Pengguna memberi mandat: *"selesaikan seluruh konflik/keputusan teknis yang dapat diputuskan secara
> teknis; hanya berhenti jika membutuhkan keputusan bisnis/pengguna"*, sejalan dengan `CLAUDE.md` §40
> (Audit → Resolve technical decisions → Update documentation → Lock specification → TASK 001).
>
> **SDL-01 s.d. SDL-14 dan SDL-17 s.d. SDL-22 sudah diputuskan dan diterapkan ke dokumen**, dengan
> status `TECHNICAL DECISION` (`CLAUDE.md` §6). **SDL-11 (deployment & sumber tile) tetap terblokir**
> karena merupakan keputusan bisnis/infrastruktur.
>
> Dua keputusan **direvisi** setelah `CLAUDE.md` versi baru (Autonomous Technical Lead) dibaca:
>
> | ID | Revisi | Alasan |
> |---|---|---|
> | SDL-09 | Usulan penyisipan SLICE-1 lintas fase **dibatalkan**. Urutan fase `docs/08` dipertahankan; hanya urutan di dalam PHASE 4/5 yang disesuaikan. | `CLAUDE.md` §7/§38/§39 melarang melompati fase dan mengunci urutan + checkpoint. Intent vertical slice dipenuhi lewat aturan checkpoint (`docs/01` §15.1). |
> | SDL-15 | False negative **tidak** dihitung ulang dari `crime_incidents` saat evaluasi; sebagai gantinya `prediction_actual.prediction_id` dijadikan nullable + `match_type = FALSE_NEGATIVE`. | `CLAUDE.md` §26 mewajibkan kejadian aktual yang tidak diprediksi *dapat direpresentasikan*, bukan sekadar dihitung. |
>
> Selain itu, `CLAUDE.md` versi baru menaikkan tiga butir dari usulan menjadi **requirement**:
> §19 (location model → SDL-12), §26 (evaluasi false negative → SDL-15), §18 (canonical pipeline → C-11).
>
> Rekap akhir dan daftar blocker: `docs/implementation-notes/000c-specification-lock.md`.

Status awal dokumen: **USULAN — MENUNGGU PERSETUJUAN PENGGUNA**
Tanggal: 2026-08-31
Dokumen induk: `docs/implementation-notes/000-specification-audit.md`
Ruang lingkup: menjawab pertanyaan gate 1–8, menyusun decision log, dan menyiapkan daftar perubahan dokumentasi.

**Tidak ada source code, database, migration, atau perubahan dokumen yang dibuat pada task ini.** Seluruh isi dokumen ini bersifat usulan sampai disetujui pemilik proyek (CLAUDE.md §26).

---

## 1. CARA MEMBACA STATUS KEPUTUSAN

Setiap keputusan diberi dua penanda.

**Dasar keputusan:**

| Kode | Arti |
|---|---|
| **A — DIDUKUNG REQUIREMENT** | Sudah dinyatakan dalam dokumen proyek; yang diperlukan hanya konfirmasi/penegasan, bukan requirement baru |
| **B — USULAN TEKNIS** | Tidak dinyatakan dalam dokumen; diusulkan Claude berdasarkan praktik teknis dan konsistensi dengan requirement yang ada |
| **C — BUTUH KEPUTUSAN PENGGUNA** | Tidak dapat diturunkan dari dokumen mana pun; hanya pemilik proyek/data owner yang berwenang menetapkan |

**Status approval:** seluruh baris berstatus `MENUNGGU PERSETUJUAN`. Tidak ada satu pun butir yang boleh diperlakukan sebagai `FINAL REQUIREMENT` sebelum pemilik proyek menyetujuinya secara eksplisit.

---

## 2. KOREKSI ATAS LAPORAN AUDIT (C-05)

Verifikasi ulang menunjukkan **`CLAUDE.md` §27 dan `docs/08` identik fase-per-fase** (0 Audit, 1 Bootstrap, 2 Database, 3 Seed, 4 Backend API, 5 Auth+RBAC, 6 Web Shell, 7 Dashboard, 8 GIS, 9 Analytics, 10 Prediction, 11 Early Warning, 12 Recommendation, 13 Commander Approval, 14 Operations, 15 Evaluation, 16 Hardening, 17 Android).

Jadi konflik penomoran fase **hanya melibatkan `docs/01` §16** (Phase 0–8), bukan tiga dokumen seperti tergambar pada tabel C-05 laporan audit. Ini memperkecil ruang lingkup perbaikan: cukup satu dokumen yang diselaraskan, bukan tiga.

Temuan baru selama verifikasi: **TASK 020–023 tidak mencakup seed untuk `users`, `role_permissions`, `citizen_reports`, `public_alerts`, `community_feedback`, dan `audit_logs`** — 6 dari 19 file dummy tidak punya task seed (lihat SDL-19).

---

## 3. JAWABAN GATE 1–8

### GATE 1 — Apakah isi paket dipindahkan ke root repository?

**Masalah.** `docs/07` mendefinisikan struktur yang berakar di root repository (`PREDIKSI-PRESISI/CLAUDE.md`, `docs/`, `apps/`, …). Kenyataannya root repository (`siintel`) berisi `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/` sebagai subfolder, ditambah `README.md` ("siintel"), `GAMBARAN WEBSITE.png`, tiga PDF sumber, dan `.DS_Store` yang sudah ter-commit. `.gitignore` hanya ada di dalam subfolder sehingga tidak melindungi root. Akibatnya seluruh path pada `CLAUDE.md` §3 (`docs/01-…`) dan `docs/07` tidak cocok dengan kondisi nyata, dan setiap task berikutnya akan menebak lokasi kerja.

**Dokumen terdampak.** `docs/07` (struktur), `README.md` (paket), `CLAUDE.md` §3 (path sumber kebenaran), `.gitignore`.

**Opsi.**
- **1A** — Pindahkan seluruh isi paket ke root repository; `.gitignore` naik ke root; PDF/PNG sumber dipindah ke `docs/source/` dan `design/`.
- **1B** — Biarkan bersarang, lalu ubah `docs/07`, `README.md`, dan `CLAUDE.md` §3 agar menyebut prefix `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/`.
- **1C** — Jadikan subfolder sebagai repository terpisah.

**Rekomendasi: 1A.** Struktur monorepo pada `docs/07` mensyaratkan `apps/`, `packages/`, `ml/`, `database/` berada di satu akar; menjalankan tooling monorepo dari subfolder yang bukan root Git akan menyulitkan CI, path relatif, dan `.gitignore`. Pemindahan dilakukan dengan `git mv` agar riwayat terjaga, dan `.DS_Store` dikeluarkan dari indeks. Nama folder "STARTER-V2" juga tidak lagi mencerminkan status proyek.

**Klasifikasi.** Struktur target = **A** (dinyatakan `docs/07`). Tindakan pemindahan file dan penataan ulang repo = **B**, dan karena memindahkan/menghapus file existing, tunduk pada CLAUDE.md aturan 11–12 → **butuh persetujuan eksplisit**.

**Dampak.** Semua path pada dokumen menjadi benar; TASK 001 dapat membuat skeleton langsung di root. Tanpa ini, setiap task berikutnya menanggung ambiguitas lokasi.

**Blocking:** TASK 001.

---

### GATE 2 — Konfirmasi stack: Next.js + FastAPI + PostgreSQL/PostGIS + MapLibre?

**Masalah.** `docs/01` §10 sudah menetapkan stack, tetapi menyebutnya "recommended initial architecture" dan memberi celah "MapLibre GL JS **or approved GIS alternative**". Sementara itu `docs/07` menyediakan `packages/shared/{types,schemas,constants}` dan `.gitignore` memuat `node_modules/` — struktur khas TypeScript — padahal backend adalah Python. Cara berbagi tipe antara FastAPI dan Next.js, tool monorepo, package manager Python, serta ORM/migration **tidak disebut di dokumen mana pun**, padahal CLAUDE.md aturan 7 mewajibkan setiap perubahan schema lewat migration.

**Dokumen terdampak.** `docs/01` §10, `docs/07` (bagian `packages/shared`), `docs/05` (kontrak API/OpenAPI), `.env.example`.

**Opsi (bagian yang belum ditentukan).**
- **2A** — FastAPI + SQLAlchemy 2.x + Alembic + GeoAlchemy2; package manager `uv`; tipe frontend digenerate dari OpenAPI.
- **2B** — FastAPI + SQLModel + Alembic; tipe ditulis manual di `packages/shared/types`.
- **2C** — Backend Node/NestJS (mengganti stack) — **ditolak**: melanggar CLAUDE.md aturan 13 dan `docs/01` §10.

**Rekomendasi: 2A.** Stack inti `docs/01` §10 dikonfirmasi apa adanya (Next.js + TypeScript, Tailwind + shadcn/ui, Python + FastAPI, PostgreSQL + PostGIS, MapLibre GL JS). Untuk yang belum ditentukan: SQLAlchemy 2.x + Alembic + GeoAlchemy2 (dukungan PostGIS matang, migration reproducible), `uv` sebagai package manager Python, pnpm workspaces untuk sisi TypeScript, dan `packages/shared` **hanya berisi artefak hasil generate dari OpenAPI + konstanta taksonomi bersama** — bukan tipe yang ditulis dua kali. Ini sekaligus menyelesaikan C-12.

**Klasifikasi.** Stack inti = **A**. ORM/migration/package manager/tooling monorepo/strategi berbagi tipe = **B**, butuh persetujuan.

**Dampak.** Menentukan isi TASK 001–002 dan seluruh TASK 010–016.

**Blocking:** TASK 001, TASK 002, TASK 010.

---

### GATE 3 — Mekanisme autentikasi: JWT atau session?

**Masalah.** `.env.example` memuat `JWT_SECRET` (mengisyaratkan JWT), `docs/08` TASK 050 menulis "session/token" (ambigu), `docs/05` tidak menyebut skema autentikasi sama sekali, dan `docs/02` #17 mendefinisikan `users` **tanpa kolom password** ("password tidak disimpan pada dataset dummy; gunakan password hash/identity provider"). Artinya tabel `users` yang akan dibuat di TASK 015 belum punya tempat menyimpan kredensial, padahal TASK 050 mewajibkan password hashing.

**Dokumen terdampak.** `docs/02` #17 (`users`), `docs/05` (bagian Authentication), `docs/08` TASK 050, `.env.example`, `docs/01` §11.

**Opsi.**
- **3A** — JWT access token berumur pendek + refresh token pada cookie `httpOnly; Secure; SameSite=Lax`; hash Argon2id.
- **3B** — Server-side session (cookie + penyimpanan sesi di database/Redis).
- **3C** — Identity provider eksternal (SSO Polri) — tidak dapat dinilai karena ketersediaannya tidak disebut dokumen mana pun.

**Rekomendasi: 3A.** Alasan: `.env.example` sudah menyediakan `JWT_SECRET`; `docs/01` §10 menyatakan Android akan menjadi klien API yang sama, dan token lebih cocok untuk klien mobile daripada cookie session murni. Refresh token tetap ditaruh di cookie `httpOnly` agar tidak tersimpan di JavaScript (CLAUDE.md §17: frontend tidak menaruh secret). Konsekuensi dokumentasi: `docs/02` #17 perlu menambah `password_hash`, `last_login_at`, dan `must_change_password`.

**Yang tetap terbuka:** masa berlaku token, kebijakan panjang/rotasi password, MFA, dan apakah SSO Polri tersedia → tetap `NOT SPECIFIED` (U-05), harus dijawab pemilik proyek sebelum TASK 050.

**Klasifikasi.** **B** (usulan teknis) dengan dukungan lemah dari `.env.example`; parameter kebijakan = **C**.

**Blocking:** TASK 015 (kolom `users`), TASK 050.

---

### GATE 4 — Bahasa kanonik untuk nama kolom, nilai enum, dan label UI?

**Masalah.** Tidak ada aturan bahasa di dokumen mana pun. Akibatnya nilai enum bercampur di dalam satu tabel yang sama: `recommendations.priority` = `Sedang`/`Tinggi` sementara `recommendations.status` = `Approved`/`Pending Review`/`Modified`/`Rejected`; `crime_incidents.status` berbahasa Indonesia (`Dilaporkan`, `Penyelidikan`, `Penyidikan`, `Selesai`) sedangkan `predictions.status` berbahasa Inggris (`Draft`, `Published`, `Validated`). Nilai-nilai ini juga hanya hidup di data dummy, tidak terdaftar di `docs/02`.

**Dokumen terdampak.** `docs/02` (seluruh daftar nilai + bagian "Master value yang belum final"), `docs/05` (payload API), `docs/07` (`config/taxonomy/`), dan seluruh file `data/sample/`.

**Opsi.**
- **4A** — Identifier teknis (nama tabel/kolom/enum tersimpan) **Inggris** `snake_case`/`UPPER_SNAKE`; label yang dilihat pengguna **Bahasa Indonesia** melalui lapisan label/i18n; istilah kedinasan resmi (Polsek, Kecamatan, Kelurahan, Samapta, Binmas, Intelkam, Reskrim, Lantas, Curanmor, Curat, Curas) dipertahankan apa adanya sebagai nilai taksonomi.
- **4B** — Seluruhnya Bahasa Indonesia termasuk nama kolom dan nilai enum.
- **4C** — Seluruhnya Inggris termasuk label UI.

**Rekomendasi: 4A.** Alasan: pengguna akhir adalah pejabat Polri sehingga UI dan alert publik harus berbahasa Indonesia (`docs/02` #7 melarang detail internal bocor ke alert publik — kontennya jelas untuk publik Indonesia), sementara identifier Inggris menjaga konsistensi dengan stack, dokumen `docs/01`/`docs/03`/`docs/05` yang sudah berbahasa Inggris, dan menghindari enum campur seperti sekarang. Istilah kedinasan tidak diterjemahkan karena merupakan nomenklatur resmi, bukan pilihan gaya.

**Dampak.** Diperlukan tabel pemetaan nilai (mis. `Dilaporkan → REPORTED`, `Sedang → MEDIUM`) yang **ditetapkan di `config/taxonomy/` pada TASK 011/020**, bukan sekarang. Label Indonesia untuk UI diambil dari lapisan label yang sama, sehingga tampilan Taskap tetap berbahasa Indonesia.

**Klasifikasi.** **B**, butuh persetujuan. Nilai taksonomi finalnya sendiri tetap **C** (U-16).

**Blocking:** TASK 011 (definisi enum), TASK 020–023 (seed).

---

### GATE 5 — Penomoran fase mana yang berlaku?

**Masalah.** `docs/01` §16 memakai Phase 0–8 dengan isi berbeda dari Phase 0–17 pada `docs/08`/`CLAUDE.md` §27. "Phase 5" berarti *Risk & prediction* di `docs/01` dan *Authentication & RBAC* di `docs/08`.

**Dokumen terdampak.** `docs/01` §16 (satu-satunya yang menyimpang — lihat koreksi di bagian 2).

**Opsi.**
- **5A** — `docs/08` menjadi penomoran kanonik; `docs/01` §16 diubah judulnya menjadi *Tahapan Konseptual* dan diberi tabel pemetaan ke PHASE `docs/08`.
- **5B** — `docs/01` §16 menjadi kanonik dan `docs/08` dinomori ulang.
- **5C** — Biarkan keduanya, tambahkan catatan.

**Rekomendasi: 5A.** `docs/08` adalah dokumen operasional yang dirujuk langsung oleh `CLAUDE.md` §27 dan berisi TASK-ID yang dipakai dalam prompt kerja; menomori ulang justru merusak referensi yang sudah dipakai. Usulan pemetaan:

| `docs/01` §16 | `docs/08` |
|---|---|
| Phase 0 — Foundation | PHASE 0–1 |
| Phase 1 — Backend foundation | PHASE 2, 4, 5 |
| Phase 2 — Core dashboard | PHASE 6–7 |
| Phase 3 — GIS | PHASE 8 |
| Phase 4 — Analytics | PHASE 9 |
| Phase 5 — Risk & prediction | PHASE 10 |
| Phase 6 — Warning & recommendation | PHASE 11–13 |
| Phase 7 — Evaluation | PHASE 15 |
| Phase 8 — Delivery | PHASE 16 |
| *(tidak ada padanan)* | PHASE 14 — Operation Center |
| Executive Brief (bagian Phase 8) | *(tidak ada task — U-11)* |

**Klasifikasi.** **B** (editorial), butuh persetujuan. Isi kedua daftar sendiri = **A**.

**Dampak.** Menghilangkan ambiguitas instruksi "kerjakan Phase X"; sekaligus mengungkap dua celah cakupan (PHASE 14 tanpa padanan konseptual, Executive Brief tanpa task).

**Blocking:** tidak memblokir TASK 001, tetapi memblokir kejelasan seluruh instruksi berikutnya.

---

### GATE 6 — Metode: tetap horizontal sesuai `docs/08`, atau disisipi slice vertikal?

**Masalah.** `docs/01` §15 menyatakan tegas *"Build vertical slices, not all frontend first and backend later"* dan §20 menetapkan slice pertama Login → … → Prediction vs Actual. `docs/08` justru horizontal murni: seluruh tabel (TASK 011–016) → seluruh API (TASK 031–040) → autentikasi → UI, sehingga potongan end-to-end pertama baru utuh sekitar TASK 150. Dua perintah ini tidak bisa dijalankan bersamaan.

**Dokumen terdampak.** `docs/01` §15 & §20, `docs/08` (urutan eksekusi + bagian CHECKPOINT), `CLAUDE.md` §27.

**Opsi.**
- **6A (hibrida)** — Pertahankan seluruh TASK-ID dan penomoran `docs/08`, tetapi tetapkan **urutan eksekusi** yang menyelesaikan satu slice tipis lebih dulu, lalu kembali ke urutan roadmap.
- **6B** — Horizontal murni sesuai urutan `docs/08` apa adanya; `docs/01` §15 dinyatakan tidak berlaku.
- **6C** — Vertical slice penuh; `docs/08` disusun ulang total.

**Rekomendasi: 6A.** Usulan susunan SLICE-1 (tanpa membuat TASK baru, hanya mengatur urutan TASK yang sudah ada):

```text
010 → 011 → 015 → 020 → 021 → 030 → 050 → 051 → 052 → 053 → 031 → 032 → 060 → 061 → 080 → 081
```

Artinya: database inti + administrasi, seed master & crime, fondasi API, autentikasi + RBAC + audit, API lokasi & crime, web shell + design system, base map + historical heatmap. Hasilnya satu jalur hidup **login → shell → daftar crime → peta** yang dapat diuji, sebelum melanjutkan TASK 012–014, 033–040, dan fase berikutnya sesuai roadmap.

Alasan: memenuhi `docs/01` §15 tanpa merusak TASK-ID; risiko integrasi (auth ↔ API ↔ peta ↔ data) terlihat di awal; dan CHECKPOINT `docs/08` tetap valid karena Checkpoint C memang sudah menggabungkan API + Authentication + RBAC.

**Klasifikasi.** **B**, butuh persetujuan — karena mengubah urutan kerja yang tertulis di `docs/08` dan `CLAUDE.md` §27 mengharuskan mengikuti roadmap.

**Dampak.** Menyelesaikan C-06 dan menurunkan risiko R-07.

**Blocking:** urutan seluruh PHASE 2–8.

---

### GATE 7 — Apakah autentikasi/RBAC dinaikkan ke sebelum PHASE 4?

**Masalah.** `docs/08` PHASE 4 mensyaratkan setiap endpoint memiliki "validation; **authorization**; test", padahal RBAC baru dibangun pada PHASE 5 (TASK 050–052). Sepuluh API domain (TASK 031–040) karenanya akan lahir tanpa mekanisme otorisasi, lalu ditambal belakangan — bertentangan dengan CLAUDE.md §16 dan §12 ("Backend/API juga wajib memvalidasi permission"), `docs/01` §11 ("authorization enforced server-side"), `docs/07` aturan 9, serta `docs/01` §16 yang menempatkan authentication + RBAC bersama database di Phase 1.

**Dokumen terdampak.** `docs/08` PHASE 4 & PHASE 5 (urutan), `docs/05` (bagian otorisasi per endpoint).

**Opsi.**
- **7A** — Urutan eksekusi: `030` (fondasi API) → `050`–`053` (auth, role, middleware, audit) → `031`–`040` (API domain). Penomoran tetap.
- **7B** — Tukar nomor PHASE 4 dan PHASE 5.
- **7C** — Biarkan; tambal otorisasi setelah semua API selesai.

**Rekomendasi: 7A.** Menempatkan middleware otorisasi dan audit sebelum API domain berarti setiap endpoint lahir sudah terlindungi dan setiap test API sejak awal mencakup kasus *allowed / denied / unauthenticated* (TASK 052) sesuai CLAUDE.md §22. Penomoran tidak diubah agar TASK-ID tetap stabil. Opsi 7C ditolak karena secara langsung melanggar aturan yang sudah mengikat.

**Klasifikasi.** **A — DIDUKUNG REQUIREMENT.** Ini bukan requirement baru, melainkan penyelarasan urutan roadmap terhadap aturan yang sudah berlaku. Perubahan urutan tetap perlu dikonfirmasi karena mengubah isi `docs/08`.

**Dampak.** Menyelesaikan C-07; menghapus risiko API tanpa proteksi.

**Blocking:** PHASE 4 dan PHASE 5.

---

### GATE 8 — Lingkungan deployment dan sumber tile peta?

**Masalah.** `docs/01` §19 secara eksplisit mencantumkan "deployment environment" sebagai open item, dan tidak ada dokumen yang menyebut jaringan, hosting, atau sumber basemap. Padahal MapLibre GL JS hanya sebuah *renderer*: ia membutuhkan sumber tile. Jika sistem dijalankan pada jaringan tertutup Polri, tile dari internet tidak akan termuat dan seluruh PHASE 8 (TASK 080–084) gagal. Ada pula konsekuensi lisensi/atribusi untuk sumber peta.

**Dokumen terdampak.** `docs/01` §10 & §19, `docs/07` (`infra/docker`), `.env.example`, `docs/08` PHASE 8.

**Opsi.**
- **8A** — On-premise/jaringan tertutup: tile server mandiri (ekstrak OSM wilayah Jakarta, disajikan lokal). Tanpa ketergantungan internet; perlu penyiapan data peta dan atribusi ODbL.
- **8B** — Cloud/VPS dengan internet: penyedia tile terkelola + API key pada environment. Cepat, tetapi menaruh ketergantungan eksternal dan biaya/lisensi.
- **8C** — Hybrid: pengembangan memakai tile server lokal via `docker-compose`, target produksi ditetapkan kemudian.

**Rekomendasi: 8C untuk sekarang, dengan 8A sebagai target yang perlu dikonfirmasi.** Alasan: PoC/Taskap kemungkinan besar didemokan di lingkungan yang tidak dijamin punya internet, dan sistem ini mengolah data Kamtibmas sehingga ketergantungan pada layanan pihak ketiga perlu persetujuan tersendiri. `.env.example` perlu menambahkan `MAP_TILE_URL` dan `MAP_STYLE_URL` agar sumber peta dapat diganti tanpa mengubah kode.

**Klasifikasi.** **C — BUTUH KEPUTUSAN PENGGUNA.** Lingkungan deployment, kebijakan jaringan, dan lisensi peta tidak dapat diputuskan dari dokumen.

**Dampak.** Tidak memblokir TASK 001 kecuali penambahan kunci pada `.env.example`; memblokir TASK 080 dan seluruh PHASE 8.

---

## 4. KEPUTUSAN ATAS TEMUAN KHUSUS

### 4.1 C-02 — `location_id` vs `grid_id`

`docs/02` §Konvensi, `docs/04` butir 1, dan `docs/06` ("Prediction → location") sudah menetapkan `location_id` sebagai referensi kanonik — ini **requirement yang berlaku**, bukan pilihan terbuka. Yang belum ada adalah cara menghubungkannya dengan dataset yang seluruhnya memakai `grid_id`.

Usulan: `locations` menjadi master wilayah/grid dengan `location_id` (UUID) sebagai PK dan `grid_id` sebagai **natural key yang unik** (`UNIQUE NOT NULL`). Seluruh tabel transaksi menyimpan `location_id` sebagai FK; kolom `kecamatan`/`kelurahan` yang terduplikasi di tabel transaksi **tidak ikut dipindahkan ke schema final** melainkan diperoleh lewat join, dan hanya dipertahankan pada tabel staging import. Konversi `grid_id → location_id` dilakukan di lapisan seed/ETL, bukan dengan mengubah canonical schema (CLAUDE.md §7).

Yang tetap terbuka: ukuran grid final dan sumber batas wilayah (U-04), serta perlunya kolom geometri poligon selain titik (D-08/D-12).

### 4.2 C-01 — Hubungan `risk_scores` dan `predictions`

Bukti paling menentukan justru ada di `docs/08` sendiri: **TASK 082 memakai `risk_scores` untuk *Current Risk Layer*, TASK 083 memakai `predictions` untuk *Predictive Heatmap*.** Artinya keduanya bukan dua tahap dari satu rantai, melainkan **dua produk analitik yang berbeda horizon waktu**:

- `risk_scores` — penilaian risiko **kondisi saat ini/periode yang sudah berjalan** per (lokasi × jendela waktu × jenis ancaman × tanggal penilaian). Menjadi layer risiko berjalan dan dapat menjadi fitur masukan model.
- `predictions` — **perkiraan untuk jendela waktu ke depan**, membawa `risk_score` dan `confidence`-nya sendiri. Early warning dan recommendation diturunkan **hanya dari `predictions`**, sesuai `docs/02` #11–#12 dan ERD.

Dengan pembacaan ini, kalimat `CLAUDE.md` §6 (Prediction → Risk Score → Early Warning) berarti *prediksi menghasilkan skor risiko yang memicu peringatan* — konsisten dengan kolom `predictions.risk_score`; sedangkan urutan pada `docs/01` §20 dan TASK 102→103 adalah **urutan membangun**, bukan urutan aliran data. Keduanya menjadi tidak bertentangan setelah dinyatakan eksplisit.

Usulan tambahan (opsional): kolom `predictions.baseline_risk_score_id` nullable untuk menelusuri risk score yang menjadi acuan. Ditandai opsional karena `docs/02` belum menyebutnya.

### 4.3 Temuan data dummy — **tidak diperbaiki sekarang**

Sesuai instruksi, tidak ada file `data/sample/` yang disentuh. Yang ditetapkan di sini hanyalah **kebijakan perbaikan dan tempat pelaksanaannya**; lihat bagian 7.

---

## 5. SPECIFICATION DECISION LOG

| ID | Masalah | Opsi | Rekomendasi | Dampak | Dasar | Status |
|---|---|---|---|---|---|---|
| **SDL-01** | Paket bersarang di `PREDIKSI-PRESISI-CLAUDE-STARTER-V2/`, `docs/07` mengasumsikan root (C-10) | 1A pindah ke root · 1B ubah dokumen · 1C repo terpisah | **1A** dengan `git mv`; PDF/PNG ke `docs/source/` & `design/`; `.gitignore` ke root; `.DS_Store` di-untrack | Semua path dokumen menjadi benar; prasyarat TASK 001 | A+B | MENUNGGU PERSETUJUAN |
| **SDL-02** | `docs/CLAUDE.md` identik dengan `CLAUDE.md` root — dua sumber kebenaran (C-10) | Hapus salinan `docs/` · pertahankan keduanya · jadikan `docs/` yang utama | **Hapus `docs/CLAUDE.md`**, sisakan satu di root sesuai `docs/07` | Menghilangkan risiko aturan kerja yang menyimpang | B | MENUNGGU PERSETUJUAN |
| **SDL-03** | Stack inti perlu ditegaskan (Gate 2) | Konfirmasi `docs/01` §10 · ganti stack | **Konfirmasi apa adanya**: Next.js+TS, Tailwind+shadcn/ui, FastAPI, PostgreSQL+PostGIS, MapLibre | Mengunci fondasi TASK 001–002 | A | MENUNGGU PERSETUJUAN |
| **SDL-04** | Tooling monorepo & berbagi tipe Python↔TS belum ditentukan (C-12) | pnpm workspaces + generate dari OpenAPI · tipe manual · tanpa tooling | **pnpm workspaces**; `packages/shared` hanya artefak generate + konstanta taksonomi | Menghapus duplikasi tipe & sumber kebenaran ganda | B | MENUNGGU PERSETUJUAN |
| **SDL-05** | ORM & migration belum ditentukan (CLAUDE.md §15 mewajibkan migration) | SQLAlchemy 2.x+Alembic+GeoAlchemy2 · SQLModel+Alembic · SQL murni | **SQLAlchemy 2.x + Alembic + GeoAlchemy2**; package manager `uv` | Menentukan TASK 010 & seluruh PHASE 2 | B | MENUNGGU PERSETUJUAN |
| **SDL-06** | Skema autentikasi ambigu; `users` tanpa `password_hash` (U-05) | 3A JWT+refresh cookie · 3B session · 3C SSO | **3A**, hash Argon2id; `docs/02` #17 ditambah `password_hash`, `last_login_at`, `must_change_password` | Menentukan kolom TASK 015 dan desain TASK 050 | B | MENUNGGU PERSETUJUAN |
| **SDL-07** | Bahasa identifier/enum/label belum diatur; enum campur dalam satu tabel (C-13) | 4A identifier EN + label ID · 4B semua ID · 4C semua EN | **4A**; istilah kedinasan tidak diterjemahkan; peta nilai ditaruh di `config/taxonomy/` | Menentukan enum schema & pemetaan seed | B | MENUNGGU PERSETUJUAN |
| **SDL-08** | Penomoran fase `docs/01` §16 menyimpang dari `docs/08`/`CLAUDE.md` §27 (C-05) | 5A `docs/08` kanonik · 5B `docs/01` kanonik · 5C biarkan | **5A** + tabel pemetaan pada `docs/01` §16 | Menghilangkan ambiguitas instruksi fase | B | MENUNGGU PERSETUJUAN |
| **SDL-09** | Vertical slice (`docs/01` §15) vs roadmap horizontal (C-06) | 6A hibrida SLICE-1 · 6B horizontal murni · 6C vertikal penuh | **6A**: urutan SLICE-1 `010→011→015→020→021→030→050→051→052→053→031→032→060→061→080→081` | Risiko integrasi terlihat awal; TASK-ID tetap | B | MENUNGGU PERSETUJUAN |
| **SDL-10** | API domain dijadwalkan sebelum RBAC ada (C-07) | 7A eksekusi `030→050–053→031–040` · 7B tukar nomor · 7C tambal belakangan | **7A** | Setiap endpoint lahir terproteksi; test denied/unauth sejak awal | A | MENUNGGU PERSETUJUAN |
| **SDL-11** | Lingkungan deployment & sumber tile tidak ditentukan (U-15) | 8A on-prem/tile mandiri · 8B cloud+tile terkelola · 8C hybrid | **8C sekarang, 8A sebagai target**; tambah `MAP_TILE_URL`/`MAP_STYLE_URL` di `.env.example` | Memblokir PHASE 8 bila tidak dijawab | C | BUTUH KEPUTUSAN PENGGUNA |
| **SDL-12** | `location_id` (dokumen) vs `grid_id` (seluruh dataset) (C-02) | Master `locations` + `grid_id` unik · pakai `grid_id` sebagai PK · denormalisasi penuh | **Master `locations`**: PK UUID, `grid_id` UNIQUE NOT NULL; tabel transaksi memakai FK `location_id`; konversi di lapisan seed/ETL | Menentukan seluruh schema PHASE 2 dan seluruh seed | A (referensi) + B (mekanisme) | MENUNGGU PERSETUJUAN |
| **SDL-13** | Relasi `risk_scores` ↔ `predictions` tidak terdefinisi (C-01) | Risk sebagai input · risk sebagai output · dua layer berbeda horizon | **Dua layer berbeda**: `risk_scores` = risiko berjalan (TASK 082), `predictions` = perkiraan ke depan (TASK 083); warning & recommendation hanya dari `predictions`; `baseline_risk_score_id` opsional | Menyelesaikan konflik terbesar model data | B (didasarkan TASK 082/083) | MENUNGGU PERSETUJUAN |
| **SDL-14** | `forecast_horizon` dummy hanya `24h`; hubungan horizon ↔ `time_window` tak terdefinisi (S-06, U-03) | Enum 5 horizon + `time_window` teks · horizon + `window_start`/`window_end` timestamptz | **Enum `{6h,12h,24h,3d,7d}`** sesuai `docs/01` §5.5–5.6 dan **ganti `time_window` teks menjadi `window_start`/`window_end` `timestamptz`**; seed wajib mencakup kelima horizon | Predictive heatmap NOW→+7D dapat didemokan; query jendela waktu menjadi sahih | B; definisi target prediksi tetap C (U-03) | MENUNGGU PERSETUJUAN |
| **SDL-15** | False negative & recall tidak dapat dihitung (U-09) | (A) hitung FN dari `crime_incidents` saat evaluasi · (B) tabel `evaluation_runs`+`evaluation_items` · (C) `prediction_id` nullable | **(A)** untuk PoC: `prediction_actual` tetap untuk Hit/FP; FN = kejadian aktual tanpa prediksi yang cocok, dihitung dari `crime_incidents` dengan aturan pencocokan spasial+temporal yang harus ditetapkan | Recall/FN pada TASK 104 & 151 menjadi mungkin; sampai aturan cocok ditetapkan, laporkan hanya precision + batasannya | B; aturan pencocokan = C | MENUNGGU PERSETUJUAN |
| **SDL-16** | Data dummy berhenti 2025-12-31, sekarang 2026-08-31 (D-11) | (A) demo clock/waktu acuan konfigurabel · (B) geser semua tanggal saat seed · (C) regenerasi dataset | **(A) sebagai utama.** Opsi (B) ditolak sebagai default karena akan merusak split 2023–2024 / Jan–Sep 2025 / Okt–Des 2025 pada `docs/01` §8; (B) hanya untuk dataset demo terpisah bila diminta | Dashboard "24 jam terakhir" terisi tanpa mengorbankan integritas split ML | B | MENUNGGU PERSETUJUAN |
| **SDL-17** | `commander_decisions.decision_by` = `USER-DEMO-PIMPINAN` (63/63) tidak ada di `users` (S-01) | Perbaiki data di TASK 023 · petakan diam-diam saat import · longgarkan FK | **Kebijakan fail-fast**: seed menolak orphan FK, tidak boleh melakukan koersi diam-diam; data diperbaiki saat TASK 023 dengan memetakan ke user ber-role Pimpinan dan mencatat perubahan | Mencegah data rusak masuk database; integritas human-in-the-loop terjaga | B | MENUNGGU PERSETUJUAN |
| **SDL-18** | Jumlah 5 faktor ≠ `risk_score` pada 1.822/1.848 baris (S-04) | Faktor = kontribusi yang harus menjumlah ke skor · faktor = sub-skor 0–100 dengan bobot terpisah | **Sub-skor 0–100 + bobot dari configuration layer**, `risk_score = Σ(bobot × faktor)`, disertai `factor_weights_version`. CHECK constraint baru dipasang **setelah** bobot disetujui; regenerasi faktor dummy di TASK 022 | Explainability dapat direkonstruksi; bobot tetap tidak di-hardcode (CLAUDE.md §9) | B; bobot tetap C (U-02) | MENUNGGU PERSETUJUAN |
| **SDL-19** | Audit dummy mencatat SUCCESS untuk aksi tanpa permission (±190 baris), pasangan action/resource acak, tidak ada DENIED; dan **6 tabel tidak punya task seed** (S-02, S-03) | Regenerasi audit dari matriks RBAC · biarkan · kosongkan audit dummy | **Regenerasi dari `role_permissions`** dengan pasangan action↔resource yang sah dan menyertakan kasus `DENIED`; enum `result = {SUCCESS, DENIED, FAILED}`; tambahkan **TASK 024 — Seed Public & Administration Data** untuk `users`, `role_permissions`, `citizen_reports`, `public_alerts`, `community_feedback`, `audit_logs` | Audit dapat dipakai sebagai bukti governance; celah cakupan seed tertutup | B | MENUNGGU PERSETUJUAN |
| **SDL-20** | 171/180 prediksi tak punya pasangan `risk_scores` (S-05) | Jadikan FK wajib · biarkan tanpa relasi · koherensi tingkat data demo | Setelah SDL-13, ketiadaan join **bukan pelanggaran schema**. Tetap disyaratkan **koherensi demo**: setiap prediksi punya `risk_scores` pada lokasi/ancaman/jendela yang sama untuk tanggal penilaian sebelumnya — diperbaiki di TASK 022 | Peta "risiko berjalan" dan "prediksi" tampak konsisten saat demo | B | MENUNGGU PERSETUJUAN |
| **SDL-21** | PK UUID (dokumen) vs ID string berprefix (dataset) (C-04) | UUID + kolom `code` · ID string sebagai PK · longgarkan konvensi | **UUID sebagai PK + `code` unik** menyimpan ID dummy (`INC-00001`, dst.) agar lampiran Taskap tetap dapat ditelusuri | Seed & traceability terjaga tanpa melanggar konvensi `docs/02` | A (UUID) + B (`code`) | MENUNGGU PERSETUJUAN |
| **SDL-22** | Timestamp dummy tanpa timezone, format campur `T` vs spasi (U-18, S-14) | Simpan UTC + tampilkan WIB · simpan waktu lokal tanpa zona | **Simpan `timestamptz` (UTC), tampilkan WIB (UTC+7)**; importer menerima kedua format dan menormalkannya; format kanonik dokumen = ISO-8601 | Konsisten dengan konvensi `docs/02`; query jendela waktu tidak ambigu | A (timestamptz) + B (kebijakan zona) | MENUNGGU PERSETUJUAN |

---

## 6. KONFLIK YANG HARUS DIPERBAIKI SETELAH GATE DITETAPKAN

Diperbaiki **hanya di dokumen**, setelah keputusan disetujui.

| Konflik | Diselesaikan oleh | Tindakan dokumentasi |
|---|---|---|
| C-01 urutan risk/prediction | SDL-13 | Tegaskan dua layer di `docs/01` §1/§5.7, `docs/02` #9–#10, `docs/04`, `docs/06`; perjelas kalimat `CLAUDE.md` §6 |
| C-02 `location_id` vs `grid_id` | SDL-12 | Tambahkan aturan natural key & konversi ETL di `docs/02`, `docs/04`, `docs/06` |
| C-03 ERD vs data dictionary (3 relasi) | SDL-12 + keputusan lanjutan | Sinkronkan `citizen_reports.location_id`, `operational_actions.created_by`; atau hapus relasinya dari `docs/04` |
| C-04 tipe PK | SDL-21 | Tambahkan aturan `code` pada §Konvensi `docs/02` |
| C-05 penomoran fase | SDL-08 | Ubah judul + tambah tabel pemetaan di `docs/01` §16 |
| C-06 vertical vs horizontal | SDL-09 | Tambahkan bagian "Urutan Eksekusi SLICE-1" di `docs/08`; rujuk dari `docs/01` §15 |
| C-07 authz sebelum RBAC | SDL-10 | Nyatakan urutan eksekusi pada `docs/08` PHASE 4/5 |
| C-08 matriks RBAC vs katalog permission | menyusul (butuh U-06) | Terbitkan katalog permission lengkap `resource:action` + kolom scope pada `docs/03`; tambah atribut jurisdiksi/fungsi pada `users` di `docs/02` |
| C-09 kontrak API tidak lengkap | Gate 2/3 + menyusul | Lengkapi `docs/05`: users, roles, locations, analytics, intelligence, patrol, operations, executive-brief, audit, citizen-reports, public-alerts + format error/pagination/versioning + skema auth |
| C-10 struktur repo & duplikat CLAUDE.md | SDL-01, SDL-02 | Perbarui `docs/07` (tambah `08-…` dan `docs/implementation-notes/`), `README.md`, `CLAUDE.md` §3 |
| C-11 tiga versi pipeline data | menyusul | Tetapkan satu definisi tahap + artefak keluaran; selaraskan `CLAUDE.md` §7, `docs/01` §7, `docs/07` aturan 5 |
| C-12 stack Python di struktur JS | SDL-04 | Perjelas peran `packages/shared` di `docs/07` |
| C-13 bahasa enum campur | SDL-07 | Tambahkan aturan bahasa di `CLAUDE.md`/`docs/02`; siapkan peta nilai di `config/taxonomy/` |
| C-14 README tidak konsisten | SDL-01 | Perbaiki bagian "Isi" `README.md` |

---

## 7. KEBIJAKAN PERBAIKAN DUMMY DATA (DILAKSANAKAN DI PHASE 2–3, BUKAN SEKARANG)

**Tidak ada file `data/sample/` yang diubah pada task ini.** Berikut penetapan *kapan* dan *bagaimana* setiap temuan diperbaiki, beserta acceptance criteria-nya.

| Temuan | Diperbaiki pada | Cara | Acceptance |
|---|---|---|---|
| S-01 `decision_by` orphan (63/63) | **TASK 023** | Petakan ke user ber-role Pimpinan; script validasi menolak orphan FK (fail-fast, tanpa koersi diam-diam) | Seed 63 keputusan berhasil dengan FK aktif; 0 orphan |
| S-02/S-03 audit tidak koheren & tanpa DENIED | **TASK 024 (baru, SDL-19)** | Regenerasi dari `role_permissions`; pasangan action↔resource sah; sertakan `DENIED` | Setiap baris audit lolos pemeriksaan permission; ada minimal satu kasus DENIED per role |
| S-04 faktor ≠ risk_score (1.822/1.848) | **TASK 022** | Regenerasi faktor sebagai sub-skor + bobot dari `config/risk/`; `factor_weights_version` terisi | `Σ(bobot × faktor)` = `risk_score` (toleransi pembulatan) pada 100% baris |
| S-05 prediksi tanpa pasangan risk score | **TASK 022** | Bangkitkan `risk_scores` pendamping untuk setiap prediksi (koherensi demo, bukan FK) | Setiap prediksi punya risk score pada lokasi/ancaman/jendela yang sama |
| S-06 horizon hanya `24h` | **TASK 022** | Bangkitkan kelima horizon `{6h,12h,24h,3d,7d}` dengan `window_start`/`window_end` | Predictive heatmap dapat menampilkan NOW→+6H→+12H→+24H→+3D→+7D |
| S-07 `dominant_factors` identik 180/180 | **TASK 022** | Bangkitkan faktor per baris dari sub-skor tertinggi; UI menandai sumbernya sebagai rule/dummy | Tidak ada dua prediksi dengan teks WHY identik seluruhnya; UI memuat penanda "berbasis rule/dummy" (CLAUDE.md §20) |
| S-08 evaluasi atas prediksi `Draft` (29) | **TASK 023** | Evaluasi hanya untuk prediksi `Published`/`Validated` | 0 baris evaluasi menunjuk prediksi `Draft` |
| S-09 tidak ada false negative | **TASK 023 + TASK 104/150** | Terapkan SDL-15: FN dihitung dari `crime_incidents`; dataset menyediakan kejadian aktual tanpa prediksi | Precision **dan** recall dapat dihitung |
| S-10 hanya 3 `operational_actions` untuk 33 `Approved` | **TASK 023** | Bangkitkan action untuk setiap keputusan `Approved` | Jumlah action ≥ jumlah keputusan `Approved` |
| S-11/S-12 grid = kelurahan, 9 kecamatan | **TASK 020** — tergantung U-04 | Menunggu keputusan ukuran grid & cakupan wilayah | Sesuai keputusan pemilik proyek |
| S-13 `is_synthetic` tidak konsisten (6/19) | **TASK 020–024** | Terapkan seragam pada seluruh file atau pindahkan sebagai metadata dataset | Konvensi tunggal, tercatat di `docs/02` |
| S-14 format waktu campur & tanpa zona | **TASK 020–024** | Terapkan SDL-22 pada importer | Semua timestamp tersimpan `timestamptz`; importer punya test untuk kedua format |
| S-15 status ganda rekomendasi↔keputusan | **TASK 013/014** | Tetapkan satu sumber kebenaran status + aturan sinkronisasi | Tidak ada status yang dapat menyimpang tanpa terdeteksi |
| S-16 semua warning terpublikasi | **TASK 111** — tergantung U-10 | Menunggu kebijakan publikasi | Sesuai kebijakan yang disetujui |
| S-17 `actual_grid_id` kosong (1 baris) | **TASK 014** | Nyatakan nullable secara eksplisit di schema | Kolom nullable terdokumentasi |
| S-18 `.DS_Store` ter-commit | **TASK 001** | `git rm --cached` + `.gitignore` di root | `git ls-files` bersih |

Prinsip yang diusulkan: **CSV di `data/sample/` tetap menjadi sumber dummy kanonik**; perbaikan dilakukan lewat script regenerasi/normalisasi deterministik di `scripts/seed/` beserta laporan validasi di `scripts/validation/`, disertai catatan perubahan — bukan penyuntingan manual satu per satu.

---

## 8. DAFTAR PERUBAHAN DOKUMENTASI YANG DIPERLUKAN

Dieksekusi **hanya setelah** keputusan terkait disetujui.

| # | Dokumen | Bagian | Perubahan | Bergantung pada |
|---|---|---|---|---|
| 1 | `README.md` (paket) | "Isi", "Baseline arsitektur" | Tambahkan `04`, `06`, `07`, `08` dan `docs/implementation-notes/` | SDL-01 |
| 2 | `CLAUDE.md` | §3 | Sesuaikan path setelah pemindahan ke root | SDL-01 |
| 3 | `CLAUDE.md` | §6 | Perjelas bahwa Risk Score adalah keluaran prediksi, dan `risk_scores` adalah layer risiko berjalan | SDL-13 |
| 4 | `CLAUDE.md` | §7 | Selaraskan tahapan pipeline dengan `docs/01` §7 dan `docs/07` aturan 5 | C-11 |
| 5 | `CLAUDE.md` | §12/baru | Tambahkan aturan bahasa identifier vs label | SDL-07 |
| 6 | `docs/CLAUDE.md` | seluruh file | **Dihapus** (duplikat) | SDL-02 |
| 7 | `docs/01` §16 | judul + isi | Ubah menjadi tahapan konseptual + tabel pemetaan ke PHASE `docs/08` | SDL-08 |
| 8 | `docs/01` §15/§20 | — | Rujuk urutan eksekusi SLICE-1 | SDL-09 |
| 9 | `docs/01` §10 | — | Tegaskan ORM/migration, package manager, tooling monorepo, sumber tile | SDL-03, SDL-04, SDL-05, SDL-11 |
| 10 | `docs/01` §19 | — | Perbarui daftar open item: tandai yang sudah dijawab gate, sisakan yang masih `NOT SPECIFIED` | seluruh SDL |
| 11 | `docs/02` §Konvensi | — | Tambahkan aturan `code` unik, timezone/format waktu, dan penandaan data sintetis | SDL-21, SDL-22, S-13 |
| 12 | `docs/02` #1–#15 | — | Ganti referensi lokasi menjadi `location_id` (FK) + `grid_id` pada `locations`; hapus kolom kecamatan/kelurahan terduplikasi dari tabel transaksi | SDL-12 |
| 13 | `docs/02` #9–#10 | — | Definisikan peran `risk_scores` vs `predictions`; kontrak faktor risiko + `factor_weights_version`; `window_start`/`window_end`; enum horizon | SDL-13, SDL-14, SDL-18 |
| 14 | `docs/02` #15 | — | Tambahkan cara false negative direpresentasikan | SDL-15 |
| 15 | `docs/02` #17 | — | Tambahkan `password_hash`, `last_login_at`, `must_change_password`, serta atribut jurisdiksi/fungsi | SDL-06, C-08 |
| 16 | `docs/02` #20 | — | Tambahkan enum `result = {SUCCESS, DENIED, FAILED}` | SDL-19 |
| 17 | `docs/02` §Master value | — | Daftarkan seluruh enum status yang saat ini hanya hidup di data dummy, tandai `PROPOSED` | SDL-07, U-08 |
| 18 | `docs/03` | seluruh matriks | Terbitkan katalog permission `resource:action` lengkap + kolom scope; selaraskan dengan `role_permissions`; tinjau hak `RW` Admin atas audit logs | C-08, U-06, U-21 |
| 19 | `docs/04` | ERD + keputusan desain | Sinkronkan 3 relasi bermasalah; tambahkan catatan `risk_scores` sebagai layer mandiri | SDL-12, SDL-13, C-03 |
| 20 | `docs/05` | seluruh dokumen | Tambahkan kelompok endpoint yang hilang, skema auth, format error, pagination, filter, versioning, dan aturan otorisasi per endpoint | C-09, SDL-06, SDL-10 |
| 21 | `docs/06` | Closed-loop + Constraints | Tambahkan posisi risk score; constraint FK `location_id`; catatan constraint bobot ditunda sampai disetujui | SDL-13, SDL-12, SDL-18 |
| 22 | `docs/07` | pohon folder + aturan | Tambahkan `08-implementation-roadmap.md`, `docs/implementation-notes/`, `docs/source/`; perjelas peran `packages/shared` | SDL-01, SDL-04 |
| 23 | `docs/08` | PHASE 3 | Tambahkan **TASK 024 — Seed Public & Administration Data** (`users`, `role_permissions`, `citizen_reports`, `public_alerts`, `community_feedback`, `audit_logs`) | SDL-19 |
| 24 | `docs/08` | PHASE 4/5 + bagian baru | Nyatakan urutan eksekusi `030→050–053→031–040` dan urutan SLICE-1 | SDL-09, SDL-10 |
| 25 | `docs/08` | PHASE 3 (TASK 020–023) | Tambahkan acceptance criteria kualitas data dari bagian 7 | SDL-17 s.d. SDL-20 |
| 26 | `.env.example` | — | Tambahkan `MAP_TILE_URL`, `MAP_STYLE_URL`, `SEED_REFERENCE_DATE`/`DEMO_REFERENCE_TIME`, parameter token | SDL-11, SDL-16, SDL-06 |

---

## 9. YANG TETAP TERBUKA SETELAH GATE 1–8

Gate 1–8 tidak menutup butir berikut. Semuanya tetap `NOT SPECIFIED` dan **tidak boleh diasumsikan**:

U-01 threshold risiko/warning · U-02 bobot faktor · U-03 definisi target prediksi & aturan pencocokan · U-04 ukuran grid & batas wilayah · U-06 scoping jurisdiksi/fungsi · U-07 penyimpanan hasil `Modify` · U-08 state machine antar status · U-10 kewenangan publikasi alert publik · U-11 sumber konten Executive Brief · U-12 penempatan modul Patrol Optimization/AI Assistant · U-13 identitas & bukti LAPOR PRESISI · U-14 retensi & klasifikasi data · U-16 taksonomi final · U-17 SLA/volume · U-19 data eksternal · U-20 detail kontrak API · U-21 detail audit.

Butir U-05 (sebagian), U-15 (arah), U-18, dan U-09 (mekanisme) terjawab sebagai **usulan** melalui SDL-06, SDL-11, SDL-22, dan SDL-15 — tetap menunggu persetujuan.

---

## 10. LANGKAH BERIKUTNYA

1. Pemilik proyek menyetujui, menolak, atau merevisi **SDL-01 s.d. SDL-22** (minimal SDL-01 s.d. SDL-11 untuk membuka TASK 001).
2. Setelah disetujui, jalankan **perubahan dokumentasi butir 1–26** pada bagian 8 — masih tanpa kode.
3. Baru kemudian TASK 001 — Initialize Repository.

**Tidak ada dokumen yang diubah, tidak ada kode yang ditulis. Pekerjaan berhenti di sini menunggu persetujuan.**
