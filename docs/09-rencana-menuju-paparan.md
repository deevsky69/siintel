# RENCANA MENUJU PAPARAN — PREDIKSI PRESISI

> Status: **BERLAKU. Menggantikan urutan fase pada `docs/08` bila keduanya berbeda.**
> Dasar: instruksi pemilik proyek 2026-09-01 dan dokumen sumber Taskap (`docs/source/`).

---

## 1. TUJUAN AKHIR

Dari `docs/source/Paparan_Gambaran_Umum_Rencana_Taskap`:

> **TASKAP SESPIMMA 2026** — Polres Metro Jakarta Selatan
> End state: **TASKAP FINAL + PREDIKSI PRESISI + SOP + VALIDATION + PAPARAN**

Aplikasi ini adalah **alat bukti** untuk Taskap yang akan dipertahankan, bukan sistem produksi.
Dua dari tujuh success criteria menyangkut aplikasi secara langsung:

| # | Kriteria | Artinya bagi aplikasi |
|---|---|---|
| 05 | **WORKING PROTOTYPE** — "bukan mockup semata" | Harus benar-benar berjalan di atas data dan API, bukan layar statis |
| 06 | **VALIDATION** — Prediction vs Actual | Precision/recall harus dapat ditampilkan dan ditelusuri |

## 2. KETENTUAN DARI PEMILIK PROYEK

| Hal | Ketentuan |
|---|---|
| Waktu paparan | **Secepatnya** — jadwal menjadi penentu prioritas |
| Tempat demo | Server ini, dengan domain milik pemilik proyek (self-hosted) |
| Tampilan | Mengikuti aplikasi acuan `siintel-app` dan `design/gambaran-website.png` — **ini prioritas utama** |
| Android (LAPOR PRESISI) | Tetap harus didemokan, tetapi **paling akhir** |
| Kewenangan | Fase awal boleh diubah bila menghambat tujuan |

## 3. YANG BERUBAH DARI RENCANA LAMA

| Sebelum | Sesudah | Alasan |
|---|---|---|
| 18 fase, 74 task dikerjakan berurutan | **Jalur kritis ±20 task**, sisanya ditunda atau dinyatakan sebagai roadmap | 74 task berurutan tidak selesai sebelum paparan |
| Urutan fase mengikat (`docs/08`, CLAUDE.md §38) | Urutan mengikuti **jalur kritis menuju paparan** | Urutan fase melayani kerapian; jadwal paparan yang menentukan |
| Peta memerlukan tile server (B-1) | **Peta digambar dari GeoJSON wilayah, tanpa tile server** | Aplikasi acuan pun tidak memakai tile basemap. Menghapus ketergantungan internet dan menghilangkan satu blocker |
| PHASE 17 Android setelah semuanya | Tetap terakhir, tetapi masuk rencana | Sesuai ketentuan pemilik proyek |
| PHASE 16 hardening penuh (6 task) | Ringkas: yang menyangkut demo publik saja | Sisanya bukan syarat pertahanan Taskap |

**B-1 (sumber tile peta) dinyatakan selesai** dan tidak lagi memblokir PHASE 8.

## 4. JALUR KRITIS

Nomor task tetap mengikuti `docs/08`. Urutannya yang berubah.
Status per **1 September 2026** ditulis di kolom terakhir; **SELESAI** berarti sudah
diverifikasi terhadap data nyata lewat HTTP, bukan sekadar kodenya ada.

### Tahap A ✅ SELESAI — Aplikasi terlihat (prioritas utama pemilik proyek)
| Task | Isi |
|---|---|
| 061 | Design system: tema command-center gelap, tipografi, kartu, badge, tabel, panel |
| 060 | Shell aplikasi: sidebar 9 menu, topbar, jam WIB, identitas pengguna |

### Tahap B ✅ SELESAI — Aplikasi hidup di atas data nyata
| Task | Isi |
|---|---|
| 030 | Fondasi API: konfigurasi, error handling, validasi, logging |
| 050–053 | Login, role, middleware otorisasi, audit logging |
| 031, 032 | API lokasi dan kejadian |
| 036, 037, 038 | API prediksi, peringatan, rekomendasi |
| 040 | API evaluasi |
| 070 | Executive Dashboard sesuai `design/gambaran-website.png` |

### Tahap C ✅ SELESAI, penyempurnaan berjalan — Peta dan rantai keputusan
| Task | Isi |
|---|---|
| 080–084 | Peta wilayah, historical heatmap, layer risiko, layer prediktif, klik grid → WHAT/WHERE/WHEN/RISK/CONFIDENCE/WHY |
| 111 | Warning Center |
| 121 | Tampilan rekomendasi per fungsi |
| 130 | Review & Approval — rantai human-in-the-loop |

Penyempurnaan yang masih berjalan pada tahap ini: memindahkan peta ke endpoint
`/map/*` yang sudah tersedia (agar agregasi dan kelas risiko tetap milik backend),
memperkaya panel rincian wilayah dengan riwayat kejadian dan peringatan aktif, serta
menyambungkan tombol acknowledge/resolve pada Warning Center.


### Tahap D ✅ SELESAI — Validasi (success criteria #06)
| Task | Isi |
|---|---|
| 150, 151 | Prediction vs Actual dan metrik precision/recall/FP/FN |

### Tahap E ⏳ MENUNGGU NAMA DOMAIN — Demo dapat diakses
| Task | Isi |
|---|---|
| D-1 | Build produksi, Docker Compose, reverse proxy, HTTPS, domain — **berkas siap**, lihat `docs/10-panduan-deployment.md`. Server ini sudah menjalankan Coolify, jadi TLS dan domain ditangani proxy-nya; yang tersisa hanyalah nama domain dari pemilik proyek |
| D-2 | Panduan menjalankan dan menghentikan demo — **selesai**, `docs/10` §9 |

### Tahap F ⏸ BELUM DIMULAI — Android (paling akhir)
| Task | Isi |
|---|---|
| 170–175 | LAPOR PRESISI |

## 5. YANG DITUNDA — DAN DISAJIKAN SEBAGAI ROADMAP

Bukan dibuang, melainkan dinyatakan terbuka saat paparan:

| Ditunda | Alasan |
|---|---|
| TASK 024 seed publik & audit | Tidak terlihat di layar utama; dikerjakan bila waktu memungkinkan sebelum paparan |
| TASK 033–035, 039 (API intelijen, patroli, analitik, operasi) | Tidak dipakai layar jalur kritis |
| TASK 090–094 analytics lanjutan | Crime Pattern DNA disajikan sebagai rencana |
| TASK 100–104 model ML | Prediksi memakai data dummy yang sudah koheren; model asli adalah pekerjaan lanjutan |
| TASK 160–165 hardening penuh | Ringkas ke yang menyangkut demo publik |

**Konsekuensi yang harus dinyatakan terbuka saat paparan:** prediksi dan risk score berasal dari
data sintetis dengan bobot dan threshold berstatus `DEMO / PROPOSED`, bukan dari model terlatih.
Ini bukan kelemahan yang disembunyikan — justru itu yang membuat klaim tetap dapat
dipertanggungjawabkan (CLAUDE.md §11, §20, §27).

## 6. YANG SUDAH SIAP DAN MENOPANG KLAIM "BUKAN MOCKUP"

| Sudah ada | Nilainya saat paparan |
|---|---|
| 20 tabel, 7 migration, reproducible dari nol | Struktur data nyata, bukan layar statis |
| 3.981 baris data koheren di 13 tabel | Angka di layar berasal dari database |
| Rantai prediction → warning → recommendation → decision → action | Human-in-the-loop yang benar-benar terpasang |
| Trigger database menolak tindakan tanpa persetujuan | Governance yang ditegakkan mesin, bukan sekadar janji |
| precision 0,397 · recall 0,400 dari 241 baris evaluasi | Success criteria #06 sudah punya dasar data |
| 243 test API + 76 test web, CI lint/typecheck/test/migrate | Bukti kualitas yang dapat ditunjukkan |
| Lima layar (dashboard, peta, peringatan, evaluasi, keputusan) hidup di atas API | Angka di layar berasal dari database, bukan dari kode |
| Peta sembilan kecamatan: hover dan klik membuka potensi ancaman wilayah | Permintaan langsung pemilik proyek; layar utama paparan |
| Keputusan komandan dapat dibuat sungguhan, usulan asli tidak tertimpa | Human-in-the-loop yang dapat diperagakan hidup, bukan diceritakan |
| Cakupan wilayah ditegakkan di query — Polsek melihat 13 dari 84 rekomendasi | RBAC yang dapat dibuktikan di depan penguji |
