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
| 5 | Crime Pattern DNA | ❌ **BELUM** | Datanya lengkap (`modus`, `target_type`, `location_type`, jam) — analisisnya belum ada |
| 6 | Predictive Heatmap | ✅ **ADA** | Layer prediktif pada `/peta` |
| 7 | AI Prediction Center | ❌ **BELUM** | Halaman `/prediksi` masih berupa rencana |
| 8 | Risk Scoring | ⚠️ **SEBAGIAN** | Skor ada dan terpakai; **menjalankannya** dari layar belum bisa |
| 9 | Early Warning | ✅ **ADA** | `/peringatan` beserta terima/selesaikan |
| 10 | AI Recommendation | ✅ **ADA** | `/rekomendasi` |
| 11 | Commander Decision / Approval | ✅ **ADA** | Setujui / Modifikasi / Tolak, usulan asli tidak tertimpa |
| 12 | Community Intelligence & manajemen laporan masyarakat | ❌ **BELUM** | `citizen_reports` **0 baris**, tanpa endpoint, tanpa layar |
| 13 | Prediction vs Actual | ✅ **ADA** | `/evaluasi`, precision 0,397 · recall 0,400 |
| 14 | Executive Brief | ❌ **BELUM** | Disebut §3, §8 no. 8, dan §9 no. 14 — tiga kali |

**Skor: 8 dari 14 lengkap, 3 sebagian, 3 belum.**

---

## 2. MODUL INTI (spesifikasi §3)

| Modul | Status |
|---|---|
| Executive Dashboard | ✅ |
| Live Kamtibmas Map | ⚠️ layer kejadian & laporan masyarakat belum; layer unit patroli belum |
| Crime Analytics | ❌ `/analitik` masih rencana |
| Crime Pattern DNA | ❌ |
| AI Prediction Center | ❌ |
| Risk Scoring Engine | ⚠️ skor ada, mesin penjalannya belum |
| Early Warning Center | ✅ |
| AI Recommendation | ✅ |
| Commander Decision | ✅ |
| Operation Center | 🔄 **sedang dikerjakan** — API selesai, layar menyusul |
| Prediction vs Actual | ✅ |
| Executive Brief | ❌ |

---

## 3. KELUARAN UTAMA (spesifikasi §8)

| # | Keluaran | Status |
|---|---|---|
| 1 | Peta kerawanan historis dan predictive heatmap | ⚠️ prediktif ada, historis belum sebagai layer |
| 2 | Crime Pattern DNA | ❌ |
| 3 | Kamtibmas Risk Score per wilayah dan time-window | ✅ |
| 4 | Early warning dan alert operasional tervalidasi | ✅ |
| 5 | AI recommendation lintas fungsi | ✅ |
| 6 | **Community signal dashboard** | ❌ |
| 7 | Prediction vs actual | ✅ |
| 8 | **Executive brief harian atau per shift** | ❌ |

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

| Urutan | Pekerjaan | Alasan |
|---|---|---|
| 1 | **Executive Brief** | Disebut spesifikasi **tiga kali** (§3, §8, §9) dan satu-satunya keluaran yang ditujukan langsung kepada pimpinan. Seluruh datanya sudah ada — tidak perlu data baru |
| 2 | **Crime Pattern DNA** | Satu-satunya modul dengan nilai akademik khas Taskap, dan datanya sudah lengkap: `modus`, `target_type`, `location_type`, jam, dan pengulangan per grid |
| 3 | **Community Intelligence** | Melengkapi kaki ketiga arsitektur (data internal + AI + masyarakat). Perlu seed TASK 024 lebih dulu |
| 4 | Layer kejadian & historis pada peta | Melengkapi MVP #3 dan #4 |
| 5 | AI Prediction Center | Perlu endpoint `prediction:run` dan `prediction:publish` |

**LAPOR PRESISI** (spesifikasi §4 — panic button, info sekitar, status laporan, community
watch) tetap Tahap F sesuai ketentuan pemilik proyek: Android paling akhir.
