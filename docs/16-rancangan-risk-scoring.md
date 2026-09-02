# RANCANGAN RISK SCORING — PREDIKSI PRESISI

Status: **PROPOSED / DEMO — disusun atas permintaan pemilik proyek, menunggu penetapan**
Tanggal: 1 September 2026

> Seluruh angka pada dokumen ini **bukan** hasil penelitian dan **bukan** ketentuan resmi
> Polri. Ia rancangan kerja agar sistem punya dasar yang dapat diperiksa dan diperdebatkan
> (CLAUDE.md §11). Yang menetapkannya adalah pemilik proyek, bukan sistem.

---

## 1. TEMUAN YANG MENGUBAH RANCANGAN

Permintaan menyebut dua contoh yang tampak setara tetapi **berbeda sifatnya secara mendasar**:

> *"misal tindak kriminal begal berapa, kemudian rencana aksi unjuk rasa bagaimana"*

| | Begal | Unjuk rasa |
|---|---|---|
| Sifat | Kejahatan, terjadi diam-diam | Kegiatan yang **direncanakan terbuka** |
| Diketahui | **Setelah** terjadi | **Sebelum** terjadi |
| Sumber utama | Riwayat kejadian | **Informasi intelijen** |
| Yang diperkirakan | Kemungkinan terjadi | **Dampaknya bila terjadi** |
| Bila tidak terjadi | Prediksi meleset | Belum tentu meleset — bisa jadi pengamanannya berhasil |

**Menilai keduanya dengan rumus yang sama adalah kekeliruan.** Kepadatan kejadian
historis adalah faktor terkuat bagi begal, dan hampir tidak berarti bagi unjuk rasa yang
akan berlangsung Selasa depan di depan kantor DPRD karena ada seruan organisasi.

Karena itu rancangan ini memakai **dua profil penilaian**, bukan satu.

---

## 2. KATALOG ANCAMAN

Diusulkan berkembang dari 5 menjadi 10 jenis, dikelompokkan menurut **cara menilainya**.

### 2.1 Kelompok A — dinilai dari pola historis

Kejahatan yang berulang dan meninggalkan jejak statistik.

| Kode | Nama | Keterangan | Data sekarang |
|---|---|---|---|
| `CURANMOR` | Pencurian kendaraan bermotor | | 464 |
| `CURAT` | Pencurian dengan pemberatan | | 282 |
| `CURAS` | Pencurian dengan kekerasan | | 184 |
| `BEGAL` | **Begal jalanan** | Perampasan disertai kekerasan di jalan, umumnya bersepeda motor. Secara yuridis bagian dari Curas, tetapi **dipisahkan** karena pola waktu, lokasi, dan penanganannya berbeda: jalan sepi, dini hari, sasaran pengendara tunggal | **belum ada** |
| `KEJAHATAN_JALANAN` | Kejahatan jalanan lain | | 141 |
| `PREMANISME` | Premanisme dan pemerasan | Pungutan liar, pemerasan di pasar dan terminal | **belum ada** |
| `NARKOBA` | Peredaran narkoba | Titik peredaran, **bukan** individu | **belum ada** |

> **Mengapa `BEGAL` dipisahkan dari `CURAS`.** Bila digabung, jam rawan Curas menjadi
> campuran perampokan rumah (siang) dan begal (dini hari), sehingga pola waktunya saling
> menghapus dan `temporal_factor` kehilangan daya bedanya. Pemisahan ini **keputusan
> analitik, bukan yuridis** — pada berkas perkara keduanya tetap Pasal 365 KUHP.

### 2.2 Kelompok B — dinilai dari informasi intelijen

Gangguan yang **direncanakan** dan diketahui sebelum terjadi.

| Kode | Nama | Keterangan | Data sekarang |
|---|---|---|---|
| `UNJUK_RASA` | Unjuk rasa / penyampaian pendapat di muka umum | Punya waktu, tempat, penyelenggara, dan perkiraan massa | **belum ada** |
| `KERAMAIAN` | Kegiatan keramaian | Konser, pertandingan, pasar malam, konvoi | **belum ada** |
| `TAWURAN` | Tawuran | **Di antara dua kelompok**: berulang seperti kejahatan, tetapi kerap didahului seruan yang terdeteksi intelijen | 129 |

---

## 3. PROFIL PENILAIAN A — POLA HISTORIS

Dipakai untuk Kelompok A. Mempertahankan bentuk yang sudah ada
(`config/risk/risk-weights.yaml`) dengan dua faktor tambahan.

```
risk_score = round( Σ ( bobot_i × faktor_i ) )      Σ bobot_i = 1,  faktor_i ∈ [0,100]
```

| Faktor | Bobot usulan | Artinya | Sumber data |
|---|---|---|---|
| `historical_factor` | **0,25** | Kepadatan kejadian historis pada sel dan jenis ini | `crime_incidents` |
| `recent_trend_factor` | **0,20** | Kecenderungan 30 hari terakhir dibanding rata-ratanya | `crime_incidents` |
| `temporal_factor` | **0,18** | Kesesuaian jendela waktu dengan jam rawan jenis ini | `crime_incidents.incident_time` |
| `spatial_factor` | **0,12** | Konsentrasi spasial dan pengulangan pada sel | `crime_incidents` + grid |
| `context_factor` | **0,10** | Objek di sekitar: pasar, terminal, ATM, permukiman padat | `locations.location_type` |
| `intelligence_factor` | **0,08** | Laporan intelijen terverifikasi yang menyebut sel dan jenis ini | `intelligence_reports` |
| `community_factor` | **0,07** | Laporan masyarakat **terverifikasi** pada sel ini | `citizen_reports` |

Dua faktor terakhir **baru**, dan keduanya menutup celah yang selama ini menganga:
120 laporan intelijen dan 150 laporan masyarakat tersimpan tetapi **tidak memengaruhi
skor sama sekali**.

> **Syarat mutlak bagi `community_factor`.** Hanya laporan berstatus `VERIFIED` ke atas
> yang boleh masuk. Spesifikasi §4 tegas: laporan masyarakat tidak langsung dianggap
> fakta. Selama klasifikasi, deteksi duplikasi, dan deteksi spam belum ada, bobot ini
> **wajib disetel 0** — dan itulah nilai awalnya.

---

## 4. PROFIL PENILAIAN B — GANGGUAN TERENCANA

Dipakai untuk Kelompok B. **Rumusnya berbeda**, dan yang dinilai bukan kemungkinan
terjadi melainkan **perkiraan dampak bila terjadi**.

| Faktor | Bobot usulan | Artinya | Cara mengisi |
|---|---|---|---|
| `mass_estimate_factor` | **0,30** | Perkiraan jumlah massa | Dari laporan intelijen |
| `location_sensitivity_factor` | **0,25** | Kedekatan objek vital: kantor pemerintah, DPRD, kedutaan, jalan protokol | `locations.location_type` |
| `history_of_disorder_factor` | **0,20** | Riwayat kericuhan pada isu atau lokasi serupa | `crime_incidents` + `intelligence_reports` |
| `source_reliability_factor` | **0,15** | Keandalan sumber informasi | `intelligence_reports.reliability` |
| `readiness_factor` | **−0,10** | Kesiapan personel — **mengurangi** skor | `police_units`, `patrol_activity` |

`readiness_factor` bertanda negatif: makin siap satuan, makin rendah risiko dampaknya.
Ini membuat model **menjawab tindakan** — risiko turun ketika pengamanan disiapkan, dan
justru itulah yang membuat rekomendasi punya arti.

> **Perbedaan penting pada evaluasi.** Unjuk rasa yang diprediksi berisiko tinggi lalu
> berlangsung tertib **bukan prediksi yang meleset** — bisa jadi justru karena
> pengamanannya berhasil. Karena itu `prediction_actual` untuk Kelompok B **tidak boleh**
> dinilai dengan precision/recall yang sama seperti Kelompok A. Ini keterbatasan yang
> harus dinyatakan terbuka, bukan disembunyikan di balik satu angka gabungan.

---

## 5. AMBANG

Kelas risiko tetap seperti `config/risk/warning-thresholds.yaml` dan **tidak diubah**:

| Kelas | Rentang |
|---|---|
| `LOW` | 0–44 |
| `MODERATE` | 45–69 |
| `HIGH` | 70–84 |
| `CRITICAL` | 85–100 |

Peringatan dini terbit pada skor ≥ 70.

**Usulan tambahan untuk Kelompok B:** peringatan terbit pada skor ≥ 60, karena gangguan
terencana punya waktu persiapan dan peringatan yang terlambat kehilangan gunanya.
Menunggu penetapan.

---

## 6. YANG DIHASILKAN

Untuk setiap kombinasi **sel grid × jenis ancaman × jendela waktu**, satu baris
`risk_scores` berisi skor, kelas, `weights_version`, dan rincian faktor pembentuknya.

Rincian faktor itulah yang menjadi jawaban **WHY** — dan karena berasal dari rumus yang
benar-benar dijalankan, bukan dari kalimat yang disusun belakangan, ia memenuhi
CLAUDE.md §27.

---

## 7. YANG DIPUTUSKAN PEMILIK PROYEK

| # | Pertanyaan | Usulan |
|---|---|---|
| 1 | Katalog 10 jenis ancaman pada §2 | Terima, atau ubah daftarnya |
| 2 | `BEGAL` dipisah dari `CURAS` | Ya — pemisahan analitik, bukan yuridis |
| 3 | Bobot Profil A pada §3 | Terima sebagai `DEMO / PROPOSED` |
| 4 | Bobot Profil B pada §4 | Terima sebagai `DEMO / PROPOSED` |
| 5 | `community_factor` disetel 0 sampai verifikasi ada | Ya |
| 6 | Ambang peringatan Kelompok B diturunkan ke 60 | Menunggu |
| 7 | Kelompok B dikecualikan dari precision/recall | Menunggu — menyangkut klaim validasi Taskap |
