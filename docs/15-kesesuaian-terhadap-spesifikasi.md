# KESESUAIAN TERHADAP RESUME SPESIFIKASI APLIKASI

Sumber: `docs/source/Resume_Spesifikasi_Aplikasi_PREDIKSI_PRESISI.pdf`
Diperiksa ulang: **9 September 2026** — terhadap kode, basis data, dan demo yang berjalan,
bukan terhadap ingatan. Pemeriksaan sebelumnya: 1 dan 2 September 2026.

> **Catatan tentang dokumen ini sendiri.** Pada 9 September 2026 ia ditemukan usang dan
> bahkan bertentangan dengan dirinya: tabel MVP menandai triase laporan masyarakat sudah
> ada, sementara paragraf di bawahnya menyatakan "belum dapat diubah dari layar". Dokumen
> kesesuaian yang salah lebih berbahaya daripada tidak ada, sebab justru ia yang dibaca
> sebagai klaim. Seluruh baris di bawah diperiksa ulang terhadap keadaan hari ini.

---

## 1. DAFTAR MVP (spesifikasi §9) — DAFTAR PERIKSA UTAMA

Ini yang menjadi ukuran, karena §9 menyebut dirinya kebutuhan minimum proof of concept.

| # | Fitur MVP | Status | Bukti / catatan |
|---|---|---|---|
| 1 | Login dan Role-Based Access Control | ✅ **ADA** | **4 peran** (22/40/17/22 grant), 43 permission, cakupan ditegakkan di query |
| 2 | Executive Dashboard | ✅ **ADA** | `/` |
| 3 | Live Crime Map | ✅ **ADA** | Layer historis pada `/peta` menggambar titik lokasi, luasnya sebanding cacah kejadian |
| 4 | Historical Heatmap | ✅ **ADA** | Layer **Historis** pada `/peta`, jendela 1 / 3 / 12 / 36 bulan |
| 5 | Crime Pattern DNA | ✅ **ADA** | `/pola` — kelima dimensi dari 1200 kejadian |
| 6 | Predictive Heatmap | ✅ **ADA** | Layer prediktif pada `/peta` |
| 7 | AI Prediction Center | ✅ **ADA** | `/prediksi`; `POST /predictions/run` dan `/predictions/{code}/publish` |
| 8 | Risk Scoring | ✅ **ADA** | `/skoring`; `POST /risk-scores/run` beserta bobot dan ambang yang mendasarinya |
| 9 | Early Warning | ✅ **ADA** | `/peringatan` beserta terima/selesaikan |
| 10 | AI Recommendation | ✅ **ADA** | `/rekomendasi` |
| 11 | Commander Decision / Approval | ✅ **ADA** | Setujui / Modifikasi / Tolak, usulan asli tidak tertimpa |
| 12 | Community Intelligence & manajemen laporan masyarakat | ✅ **ADA** | Kanal publik `/lapor` dan aplikasi Android menerima; `/masyarakat` membaca; triase pada `/input` lewat `POST /citizen-reports/{code}/status`; petugas juga memverifikasi dari ponsel |
| 13 | Prediction vs Actual | ✅ **ADA** | `/evaluasi`, precision 0,397 · recall 0,400 |
| 14 | Executive Brief | ✅ **ADA** | `/brief`, siap cetak |

**Skor per 9 September 2026: 14 dari 14 lengkap, 0 sebagian, 0 belum.**

Riwayat: 8/3/3 → 10/3/1 (1 September) → 11/3/0 → 13/1/0 (2 September) → **14/0/0**
(9 September).

`/peta` kini memuat **ketiga** layer yang diminta CLAUDE.md §24 — historis, risiko
berjalan, prediktif — sehingga #3 dan #4 tertutup sekaligus. Ketiganya sengaja berwarna
berjauhan dan bersatuan berbeda: dua layer memakai skor 0–100, sedangkan layer historis
memakai **cacah kejadian** dan karena itu tidak diberi kelas risiko apa pun.

**#12 tertutup.** `POST /citizen-reports/{code}/status` ada dan menegakkan
`citizen_report:write`; layar `/input` memakainya, dan aplikasi Android petugas
memverifikasi lewat endpoint yang sama. Diperiksa ujung ke ujung pada demo produksi
9 September 2026: warga mengirim laporan dari aplikasi, laporan muncul di antrean Polsek,
petugas memverifikasinya.

**Yang bertambah setelah daftar MVP ini disusun** — bukan bagian dari 14 butir, tetapi
menutup lengan terakhir rantai CLAUDE.md §9: **kanal imbauan kepada masyarakat**
(`/imbauan`, TASK 111). Peringatan dini kini dapat diterbitkan Pimpinan menjadi imbauan
publik, terbaca tanpa akun di halaman muka web maupun di aplikasi Android warga.

---

## 2. MODUL INTI (spesifikasi §3)

| Modul | Status |
|---|---|
| Executive Dashboard | ✅ |
| Live Kamtibmas Map | ⚠️ tiga layer ada (historis, risiko berjalan, prediktif); layer **laporan masyarakat** dan **unit patroli** belum — keduanya menuntut sumber posisi yang belum dimiliki sistem |
| Crime Analytics | ✅ `/analitik` — tren bulanan, pola waktu, perbandingan antarwilayah |
| Crime Pattern DNA | ✅ |
| AI Prediction Center | ✅ `/prediksi` |
| Risk Scoring Engine | ✅ `/skoring` |
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
| 1 | Peta kerawanan historis dan predictive heatmap | ✅ ketiga layer §24 ada: historis, risiko berjalan, prediktif |
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

## 5. MODEL DATA TERHADAP SPESIFIKASI §5

| Spesifikasi | Keadaan | Catatan |
|---|---|---|
| **Foto / Video / Audio** (opsional) | ✅ **ADA** sejak 8 September 2026 | Tabel `citizen_report_attachments` (migration 0008). Metadata dilucuti sebelum disimpan — EXIF pada gambar lewat Pillow, metadata wadah audio/video lewat ffmpeg — sehingga koordinat GPS yang ditanam kamera ponsel tidak ikut tersimpan. Berkas dihapus 90 hari setelah laporannya selesai, dan pembersihannya berjalan terjadwal tiap jam |
| **Identitas / Kontak** (opsional) | ❌ tidak ada kolom | **Sengaja.** Menambahkannya adalah keputusan privasi (CLAUDE.md §16, docs/14 §3), bukan kekurangan teknis. Spesifikasi sendiri menyebutnya *opsional sesuai mekanisme akun dan kebijakan perlindungan data* |

Konsekuensi yang perlu disadari dari baris kedua: karena tidak ada identitas pelapor,
**tidak ada pula cara pelapor melihat status laporannya**. Tiket `RPT-xxxx` berurut dan
karena itu dapat ditebak; sebuah endpoint yang hanya menuntut tiket akan membocorkan status
laporan siapa pun. Menutupnya memerlukan token klaim acak yang disimpan di ponsel pelapor —
perubahan skema dan kontrak API, dan itu keputusan pemilik proyek (sisa U-13).

---

## 6. YANG DIKERJAKAN, BERURUT MENURUT NILAI

### Sudah dikerjakan 1 September 2026

| Pekerjaan | Hasil |
|---|---|
| Executive Brief | `/brief` — kalimat dari template, angka dari basis data |
| Crime Pattern DNA | `/pola` — tanpa penandaan "signifikan"; kerapuhan sampel dinyatakan lewat aritmetikanya |
| Community Intelligence | `/masyarakat` — 150 laporan, tanpa identitas pelapor, belum memengaruhi risk score |
| Operation Center | `/operasi` — menutup lengan umpan balik |

### Dikerjakan 8–9 September 2026

| Pekerjaan | Hasil |
|---|---|
| Triase laporan masyarakat | `POST /citizen-reports/{code}/status`, dipakai `/input` dan aplikasi Android petugas — menutup MVP #12 |
| Layer historis & prediktif pada peta | Ketiga layer §24 ada, dan peta beranda kini memuat seluruh wilayah hukum Polda Metro Jaya |
| AI Prediction Center | `/prediksi` beserta `prediction:run` dan `prediction:publish` |
| Lampiran laporan masyarakat | Foto/suara/video, metadata dilucuti, retensi 90 hari berjalan terjadwal |
| Kanal imbauan publik | `/imbauan` — peringatan dini dapat diterbitkan Pimpinan, terbaca tanpa akun (TASK 111) |
| Penetapan U-01, U-02, U-16, U-22, separuh U-10 | Bobot, ambang, taksonomi, pemetaan status wilayah, dan kewenangan publikasi alert |

### Dikerjakan 30 September – 1 Oktober 2026 — data asli menggantikan data sintetis

| Pekerjaan | Keadaan |
|---|---|
| **Impor data resmi Pusiknas** (8.203 LP Curanmor/Curat/Curas, 2023–Sep 2026) | `scripts/import/pusiknas.py`: menolak kolom identitas, membangun 65 lokasi kelurahan + 10 cadangan kecamatan, memeriksa hasilnya terhadap lima lembar rekap resmi dan **menolak menulis** bila ada selisih. Berkas sumber dan hasil di `data/raw/`, `data/processed/` — tidak pernah masuk repo publik |
| **Skema kejadian jujur pada jam kosong** (migration 0010) | `incident_time` boleh NULL + `time_known`; kolom Laporan Polisi (`reported_at`, `report_lag_hours`, `report_source`, `receiving_unit`, `data_group`, koordinat, `data_source`). Lima pola jam hanya membaca kejadian yang jamnya tercatat |
| **Tujuh tabel sintetis dihapus** (keputusan pemilik proyek) | Intelijen, patroli, laporan masyarakat, imbauan, umpan balik, keputusan, tindakan: mulai kosong, terisi hanya oleh aplikasi |
| **Bobot `pusiknas-2026-10-01`** | Angka U-02 utuh, cakupan tiga jenis; tujuh jenis sintetis `outside_scope` |
| **Rantai PREDIKSI → PERINGATAN → REKOMENDASI disambung** | Sebelumnya tidak ada kode runtime yang menerbitkan peringatan/rekomendasi. Publikasi (tunggal / massal `publish-run`) menerbitkan keduanya dari ambang yang berlaku; fungsi dari `config/recommendation/function-rules.yaml` (PROPOSED) |
| **Evaluasi mundur** (success criteria #06) | `cli backtest`: bukti dibatasi tanggal lapor, unit sel × jenis × jendela, kejadian tanpa jam dilaporkan terpisah. Hasil TEST Jan–Sep 2026: precision 0,010, recall 0,259 |
| **Analitik blok 3 jam, peta kelurahan, label sumber data** | Keputusan 30 September 2026; layer peta `level=kelurahan`; "Pusiknas, posisi 29 September 2026" dibaca dari baris data |
| **Produksi** | **Diterapkan 1–4 Oktober 2026** lewat `scripts/terapkan-data-asli-produksi.sh` (cadangan `~/siintel-cadangan/predpol-prod-20261001-035009.sql.gz`, skema 0010, data sintetis dihapus, 8.203 kejadian + 75 lokasi dimuat, 832 skor dan prediksi, 96 peringatan + rekomendasi, evaluasi mundur precision 0,010 / recall 0,259; `prod:periksa` lulus seluruhnya) |

### Dikerjakan 4 Oktober 2026 — aplikasi berdiri di awal 2026

| Pekerjaan | Keadaan |
|---|---|
| **Batas tampilan data** | Saringan ORM global (`services/visibility.py`): layar hanya memuat kejadian ≤ `DISPLAY_DATA_UNTIL` (31 Desember 2025); jam acuan 1 Januari 2026. Seeder, evaluasi mundur, dan pencocokan rencana menyatakan bypass eksplisit |
| **Rencana patroli 2026 + pencocokan** | `/patrol-plan` dan `/patrol-plan/evaluation`, halaman `/rencana-patroli`: usulan kelurahan × blok 3 jam × jenis dari pola 2025 (PROPOSED), dicocokkan kejadian nyata 2026 — pola jam 84%, pola wilayah 75%, ketepatan slot 57%, cakupan 4% |
| **Keputusan Pimpinan atas rencana patroli** | Migration 0011 `patrol_plan_decisions`; `POST /patrol-plan/decisions` (setujui / setujui sebagian / tolak), usulan disalin saat diputus, keputusan terakhir yang berlaku, pencocokan mengikuti rencana yang berlaku; formulir di `/rencana-patroli` bagi pemegang `commander_decision:approve` |
| **Peta** | Klik kecamatan pada `/peta` membuka peta kelurahan berwarna (sudah sejak 1 Oktober 2026) |
| **Produksi** | **Diterapkan 4 Oktober 2026**: jam acuan 1 Januari 2026, batas tampilan 2025, 816 skor dan prediksi 24H, 32 peringatan + rekomendasi, evaluasi mundur 3 Jan–28 Sep 2026; `prod:periksa` lulus. Potret keadaan: `scripts/status-produksi.sh`; mesin dapat diulang: `scripts/jalankan-mesin-produksi.sh` |

### Masih tersisa

| Urutan | Pekerjaan | Alasan |
|---|---|---|
| 1 | **Near-repeat** pada Crime Pattern DNA | docs/01 §5.4 menyebutnya; definisi jendela jarak dan waktu **menunggu keputusan pemilik proyek** |
| 2 | Layer **laporan masyarakat** dan **unit patroli** pada peta | Modul §3 menyebut keduanya. Laporan masyarakat punya koordinat dan dapat digambar; posisi unit patroli **tidak ada sumbernya** — `patrol_activity` mencatat kegiatan, bukan posisi berjalan |
| 3 | Severity minimum publikasi alert (sisa U-10) | Kanalnya berjalan **tanpa** gerbang severity, dan layar menyatakannya |
| 4 | Ambang peringkat volume laporan | Dipisahkan dari U-22 pada 9 September 2026, masih `PROPOSED` |
| 5 | Definisi target prediksi & aturan pencocokan evaluasi (U-03) | Evaluasi mundur sudah menghitung dengan aturan `PROPOSED`; hasilnya (precision 0,010 pada ambang 70) menuntut keputusan atas ambang dan/atau aturan pencocokan |
| 6 | Kunci rilis satuan untuk APK | APK rilis kini ditandatangani **kunci debug** — memadai untuk paparan pada perangkat sendiri, tidak untuk disebarkan |
| 7 | Faktor konteks pada data asli | `context_factor` hampir seragam antar-kelurahan (tidak ada data POI/kegiatan pada Pusiknas); bobot tidak dibagi ulang karena U-02 FINAL — menunggu pilihan pemilik proyek |
| 8 | Master satuan (`police_units`) | Daftar unit sintetis dihapus; daftar resmi belum diberikan, sehingga layar Operasi belum dapat mencatat penugasan |
| 9 | Fungsi yang diusulkan per jenis | `function-rules.yaml` PROPOSED (Samapta untuk ketiganya) |
| 10 | Konfirmasi perubahan sistem pelaporan 2024 | Tren 3.992 → 1.884 → 1.237 → 1.090 terlalu curam untuk dibaca sebagai penurunan kejahatan semata |

### Android — keadaan per 9 September 2026

**Satu APK**, bukan dua lagi (`id.polri.jaksel.laporpresisi`, 2.0.0). Layar mukanya dua
pintu: lapor untuk warga, masuk untuk petugas. Diperiksa langsung terhadap demo produksi
pada 9 September 2026 — bukan terhadap emulator dan bukan terhadap ingatan.

| Bagian | Yang sudah bekerja | Yang belum |
|---|---|---|
| **Warga** | Mengirim laporan sampai tersimpan · berbagi lokasi · lampiran foto/suara/video · **imbauan kewaspadaan yang sedang berlaku** ("info sekitar" §4) · **cek status laporan sendiri** dengan token klaim | Panic button dan community watch — keduanya terhalang keputusan, bukan pekerjaan teknis (lihat di bawah) |
| **Petugas** | Masuk · sesi tujuh hari (teruji melewati proxy) · membaca antrean menurut kewenangan · **memverifikasi laporan** | Menyetujui rekomendasi dan menutup peringatan dari ponsel |

Lingkaran penuhnya terbukti pada demo sungguhan: warga mengirim laporan → laporan muncul
di antrean Polsek yang berwenang → petugas memverifikasinya.

**Keamanan APK, diperiksa 9 September 2026.** Token petugas disimpan
`EncryptedSharedPreferences` (AES256-GCM); tidak ada satu pun pernyataan `Log` di seluruh
kode; sandi tidak pernah disimpan; tiga izin saja (internet dan lokasi, diminta hanya saat
tombol ditekan); hanya layar muka yang `exported`; `allowBackup=false`; HTTP polos ditolak
termasuk pada Android 7–8. Jangkar CA satuan dihapus dari varian rilis setelah sertifikat
Let's Encrypt terbit.

**Satu hal menutup jalan penyebaran:** APK rilis ditandatangani **kunci debug** —
`C=US, O=Android, CN=Android Debug`. Kunci itu sama pada setiap mesin pengembang di dunia
dan sandinya diketahui umum, sehingga siapa pun dapat membangun "pembaruan" yang diterima
Android sebagai aplikasi yang sama. Memadai untuk paparan pada perangkat sendiri; tidak
untuk dibagikan.

#### Status laporan — dikerjakan 9 September 2026

Pelapor kini dapat memeriksa status laporannya sendiri, dan cara mengamankannya perlu
dicatat karena masalahnya nyata: nomor tiket `RPT-xxxx` **berurut** sehingga dapat ditebak,
sedangkan sistem sengaja tidak menyimpan identitas pelapor — tidak ada akun, tidak ada
nomor telepon, tidak ada apa pun untuk mengikat hak baca.

Jawabannya **token klaim**: 256 bit acak, diterbitkan sekali saat laporan dikirim,
tersimpan terenkripsi di ponsel pelapor. Basis data hanya menyimpan SHA-256-nya. Tiket
tanpa token, token salah, tiket tak dikenal, dan laporan lama tanpa token dijawab **404
yang identik** — sehingga endpoint ini tidak dapat dipakai memastikan sebuah tiket ada.

Harganya dinyatakan kepada pelapor, bukan disembunyikan: kode yang hilang tidak dapat
diterbitkan ulang, karena tidak ada identitas yang dapat dipakai mengenalinya kembali.

#### Dua fitur §4 yang TIDAK dikerjakan, dan mengapa

Keduanya terhalang keputusan pemilik proyek, bukan kesulitan teknis. Mengerjakannya tanpa
keputusan itu bukan kemajuan melainkan kerusakan:

| Fitur | Yang menghalangi |
|---|---|
| **Panic button** | **Komitmen respons** — siapa yang menerima, dalam berapa lama, dan apa yang terjadi bila tidak ada yang menjawab. Tombol darurat yang menjanjikan bantuan tanpa ada yang berkewajiban datang lebih berbahaya daripada tidak ada tombol sama sekali: ia membuat orang berhenti mencari pertolongan lain |
| **Community watch** | Belum ada definisi produk. Apa yang dibagikan, kepada siapa, dan siapa yang memoderasinya adalah pertanyaan kebijakan sebelum menjadi pertanyaan teknis |
