# KESESUAIAN TERHADAP RESUME SPESIFIKASI APLIKASI

Sumber: `docs/source/Resume_Spesifikasi_Aplikasi_PREDIKSI_PRESISI.pdf`
Diperiksa: 1 September 2026 — terhadap kode dan basis data yang berjalan, bukan terhadap ingatan.

---

## 1. DAFTAR MVP (spesifikasi §9) — DAFTAR PERIKSA UTAMA

Ini yang menjadi ukuran, karena §9 menyebut dirinya kebutuhan minimum proof of concept.

| # | Fitur MVP | Status | Bukti / catatan |
|---|---|---|---|
| 1 | Login dan Role-Based Access Control | ✅ **ADA** | 6 peran, 43 permission, cakupan ditegakkan di query |
| 2 | Executive Dashboard | ✅ **ADA** | `/` |
| 3 | Live Crime Map | ⚠️ **SEBAGIAN** | Peta ada; layer **titik kejadian aktual** belum |
| 4 | Historical Heatmap | ⚠️ **SEBAGIAN** | Riwayat tampil sebagai angka di panel rincian, belum sebagai layer peta |
| 5 | Crime Pattern DNA | ✅ **ADA** | `/pola` — kelima dimensi dari 1200 kejadian |
| 6 | Predictive Heatmap | ✅ **ADA** | Layer prediktif pada `/peta` |
| 7 | AI Prediction Center | ❌ **BELUM** | Halaman `/prediksi` masih berupa rencana |
| 8 | Risk Scoring | ⚠️ **SEBAGIAN** | Skor ada dan terpakai; **menjalankannya** dari layar belum bisa |
| 9 | Early Warning | ✅ **ADA** | `/peringatan` beserta terima/selesaikan |
| 10 | AI Recommendation | ✅ **ADA** | `/rekomendasi` |
| 11 | Commander Decision / Approval | ✅ **ADA** | Setujui / Modifikasi / Tolak, usulan asli tidak tertimpa |
| 12 | Community Intelligence & manajemen laporan masyarakat | ⚠️ **SEBAGIAN** | `/masyarakat` — 150 laporan terbaca; **triase (aksi tulis) belum ada** |
| 13 | Prediction vs Actual | ✅ **ADA** | `/evaluasi`, precision 0,397 · recall 0,400 |
| 14 | Executive Brief | ✅ **ADA** | `/brief`, siap cetak |

**Skor per 1 September 2026: 10 dari 14 lengkap, 3 sebagian, 1 belum.**

Naik dari 8/3/3 pada pemeriksaan pertama hari ini. Yang tersisa belum sama sekali
hanya **#7 AI Prediction Center** — ia memerlukan endpoint `prediction:run` dan
`prediction:publish`, dan itu bukan sekadar layar.

---

## 2. MODUL INTI (spesifikasi §3)

| Modul | Status |
|---|---|
| Executive Dashboard | ✅ |
| Live Kamtibmas Map | ⚠️ layer kejadian & laporan masyarakat belum; layer unit patroli belum |
| Crime Analytics | ⚠️ sebagian tercakup Crime Pattern DNA; `/analitik` masih rencana |
| Crime Pattern DNA | ✅ |
| AI Prediction Center | ❌ |
| Risk Scoring Engine | ⚠️ skor ada, mesin penjalannya belum |
| Early Warning Center | ✅ |
| AI Recommendation | ✅ |
| Commander Decision | ✅ |
| Operation Center | ✅ `/operasi` |
| Prediction vs Actual | ✅ |
| Executive Brief | ✅ |

---

## 3. KELUARAN UTAMA (spesifikasi §8)

| # | Keluaran | Status |
|---|---|---|
| 1 | Peta kerawanan historis dan predictive heatmap | ⚠️ prediktif ada, historis belum sebagai layer |
| 2 | Crime Pattern DNA | ✅ |
| 3 | Kamtibmas Risk Score per wilayah dan time-window | ✅ |
| 4 | Early warning dan alert operasional tervalidasi | ✅ |
| 5 | AI recommendation lintas fungsi | ✅ |
| 6 | **Community signal dashboard** | ✅ |
| 7 | Prediction vs actual | ✅ |
| 8 | **Executive brief harian atau per shift** | ✅ harian; batas shift menunggu aturan organisasi |

---

## 4. YANG SUDAH SESUAI DAN TIDAK PERLU DISENTUH

Diperiksa langsung, bukan diasumsikan.

### 4.1 Struktur database (spesifikasi §10) — **cocok seluruhnya**

Kelima kelompok tabel ada persis seperti disebut spesifikasi, ditambah tabel yang
diperlukan model kewenangan (`role_permissions`) dan lokasi (`locations`).

### 4.2 Variabel data internal (spesifikasi §6) — **cocok seluruhnya**

| Variabel spesifikasi | Kolom | Ada |
|---|---|---|
| ID Anonim | `crime_incidents.code` | ✅ |
| Jenis Kejadian | `incident_type` | ✅ |
| Tanggal / Jam Kejadian | `incident_date`, `incident_time` | ✅ |
| Polsek / Kecamatan / Kelurahan | `locations.*` | ✅ |
| Alamat / Grid Lokasi | `locations.grid_id` | ✅ |
| Latitude / Longitude | `locations.latitude/longitude` + PostGIS | ✅ |
| Kategori TKP | `location_type` | ✅ |
| Modus | `modus` | ✅ |
| Objek Sasaran | `target_type` | ✅ |
| Status Penanganan | `status` | ✅ |

Fokus jenis kejadian juga sesuai: **Curanmor 464, Curat 282, Curas 184** (ditambah
Kejahatan Jalanan 141 dan Tawuran 129).

Tidak ada identitas korban, pelaku, maupun saksi — sesuai perintah spesifikasi §6.

### 4.3 Status laporan masyarakat (spesifikasi §5) — **cocok seluruhnya**

`config/taxonomy/mappings.yaml` sudah memuat kelima status persis seperti spesifikasi:
Diterima → Diverifikasi → Diteruskan → Ditangani → Selesai.

### 4.4 Governance (spesifikasi §11) — **cocok**

RBAC, audit trail, pembatasan akses informasi sensitif, dan prinsip **AI output ≠ police
decision** seluruhnya terpasang. Yang terakhir bahkan dijaga trigger basis data, bukan
hanya oleh aplikasi.

---

## 5. YANG BELUM SESUAI PADA MODEL DATA

Dua kekurangan pada `citizen_reports` dibanding spesifikasi §5:

| Spesifikasi | Keadaan | Catatan |
|---|---|---|
| **Foto / Video / Audio** (opsional) | ❌ tidak ada kolom maupun tabel lampiran | Perlu tabel lampiran terpisah; menyimpan berkas juga menyentuh kebijakan retensi |
| **Identitas / Kontak** (opsional) | ❌ tidak ada kolom | **Sengaja.** Menambahkannya adalah keputusan privasi (CLAUDE.md §16, docs/14 §3), bukan kekurangan teknis |

Yang kedua tidak dianggap cacat: spesifikasi sendiri menyebutnya *opsional sesuai
mekanisme akun dan kebijakan perlindungan data*.

---

## 6. YANG DIKERJAKAN, BERURUT MENURUT NILAI

### Sudah dikerjakan 1 September 2026

| Pekerjaan | Hasil |
|---|---|
| Executive Brief | `/brief` — kalimat dari template, angka dari basis data |
| Crime Pattern DNA | `/pola` — tanpa penandaan "signifikan"; kerapuhan sampel dinyatakan lewat aritmetikanya |
| Community Intelligence | `/masyarakat` — 150 laporan, tanpa identitas pelapor, belum memengaruhi risk score |
| Operation Center | `/operasi` — menutup lengan umpan balik |

### Masih tersisa

| Urutan | Pekerjaan | Alasan |
|---|---|---|
| 1 | Triase laporan masyarakat (aksi tulis) | Melengkapi MVP #12; statusnya sudah ada, penyuntingannya belum |
| 2 | Layer kejadian & historis pada peta | Melengkapi MVP #3 dan #4 |
| 3 | AI Prediction Center | MVP #7 — perlu endpoint `prediction:run` dan `prediction:publish` |
| 4 | Near-repeat pada Crime Pattern DNA | docs/01 §5.4 menyebutnya; definisi jendela jarak dan waktu **menunggu keputusan pemilik proyek** |

**LAPOR PRESISI** (spesifikasi §4 — panic button, info sekitar, status laporan, community
watch) tetap Tahap F sesuai ketentuan pemilik proyek: Android paling akhir.
