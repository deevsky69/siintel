# EVALUASI PERAN & KANAL MASYARAKAT — BAHAN KEPUTUSAN

Status: **PROPOSED — memerlukan keputusan pemilik proyek** (CLAUDE.md §2C)
Tanggal: 1 September 2026

---

## 1. TEMUAN YANG MENDAHULUI REKOMENDASI

Tiga hal diperiksa langsung ke basis data dan API, bukan diduga.

### 1.1 Laporan masyarakat belum ada datanya

| Tabel | Baris |
|---|---|
| `citizen_reports` | **0** |
| `public_alerts` | **0** |
| `community_feedback` | **0** |

Strukturnya sudah bermigrasi sejak TASK 012, tetapi seedingnya (TASK 024) ditunda pada
`docs/09` §5. Jadi kanal masyarakat saat ini **belum mengalirkan apa pun** — belum ada
data, belum ada endpoint, belum ada layar.

### 1.2 `citizen_reports` sengaja tidak menyimpan identitas pelapor

```
report_id, code, reported_at, incident_time, category, description,
latitude, longitude, geom, location_id, location_text,
urgency_score, verification_score, status, created_at, updated_at
```

Tidak ada `reporter_id`, nama, nomor telepon, maupun NIK. Ini rancangan yang benar dan
sejalan dengan CLAUDE.md §16 (minimalkan data pribadi) — dan ia menentukan jawaban atas
pertanyaan peran masyarakat pada §3.

### 1.3 Cakupan OWN_FUNCTION sebagian tidak dapat ditegakkan

`config/rbac/permissions.yaml` menyatakan peran **Fungsi** dibatasi `OWN_FUNCTION` untuk
`crime:read` dan `intelligence:read`. Diperiksa dengan akun `demo.fungsi` (RESKRIM):

| Data | Terlihat | Seharusnya |
|---|---|---|
| Rekomendasi | **20 dari 84** ✅ | dibatasi fungsi |
| Kejadian | **1200 dari 1200** ❌ | dibatasi fungsi |

Sebabnya ada di model data: `crime_incidents` dan `intelligence_reports` **tidak memiliki
kolom fungsi maupun unit**. Hanya `patrol_activity` dan `operational_actions` yang punya
`unit_id`, dan `recommendations` yang punya `recommended_function`.

**Kewenangan yang dideklarasikan tetapi tidak dapat ditegakkan lebih berbahaya daripada
yang tidak dideklarasikan**, karena ia memberi rasa aman yang keliru. Ini cacat yang sama
jenisnya dengan celah `GET /recommendations` yang ditutup pada catatan TASK 130.

---

## 2. YANG BELUM ADA DI APLIKASI

### 2.1 Kesenjangan terpenting: separuh rantai tidak dapat dijalankan

Modul penggunaan menggambarkan rantai tertutup. Aplikasi baru dapat menempuhnya **sampai
keputusan**:

```
DATA → ANALISIS → PREDIKSI → PERINGATAN → REKOMENDASI → KEPUTUSAN ✅ sampai sini
                                                            ↓
                        TINDAKAN OPERASIONAL → HASIL NYATA → EVALUASI ❌ tidak ada layar
```

Datanya ada (52 tindakan operasional, 241 baris evaluasi), tetapi tidak ada satu pun cara
mencatat bahwa tindakan **benar-benar dilaksanakan** dan apa **hasilnya**. Karena success
criteria #06 Taskap adalah validasi, lengan umpan balik inilah yang paling pantas
dikerjakan berikutnya.

### 2.2 Data yang ada tetapi tidak terlihat

| Data | Baris | Endpoint | Layar |
|---|---|---|---|
| Laporan intelijen | 120 | ✗ | ✗ |
| Kegiatan patroli | 180 | ✗ | ✗ |
| Tindakan operasional | 52 | ✗ | ✗ |
| Audit trail | 62 | ✗ | ✗ |
| Satuan / unit | 6 | ✗ | hanya agregat |
| Prediksi vs kenyataan | 241 | hanya agregat | hanya agregat |

### 2.3 Aplikasi masih nyaris hanya-baca

Dari 43 permission, hanya **tiga aksi tulis** yang benar-benar ada: memutuskan
rekomendasi, menerima peringatan, menyelesaikan peringatan.

Belum ada: input kejadian, input laporan intelijen, menjalankan penilaian risiko,
menjalankan dan mempublikasikan prediksi, menjalankan evaluasi, menyusun rekomendasi,
mencatat tindakan operasional, publikasi pengumuman, dan pengelolaan pengguna.

---

## 3. PERAN MASYARAKAT — REKOMENDASI: **JANGAN** JADIKAN PERAN RBAC

Kebutuhannya nyata; bentuknya yang perlu berbeda.

### Mengapa bukan peran di dalam RBAC ini

| Alasan | Uraian |
|---|---|
| **Permukaan serang berubah sifat** | RBAC sekarang melayani enam akun internal yang dibuat administrator. Membuka pendaftaran mandiri untuk publik mengubahnya menjadi sistem berhadapan publik — setiap akun warga adalah pijakan potensial ke dalam sistem intelijen kamtibmas |
| **Bertentangan dengan rancangan tabelnya sendiri** | `citizen_reports` sengaja tidak menyimpan identitas pelapor. Peran masyarakat justru **memaksa** penyimpanan identitas — membalik keputusan yang sudah benar |
| **Model cakupan harus dibongkar** | Cakupan saat ini `ALL`, `OWN_JURISDICTION`, `OWN_FUNCTION`. Warga menuntut jenis keempat, "hanya laporan sendiri", yang menyentuh setiap query di aplikasi |
| **Kanalnya memang sudah direncanakan terpisah** | LAPOR PRESISI (TASK 170–175) adalah aplikasi Android untuk masyarakat. Warga tidak perlu — dan tidak boleh — masuk ke antarmuka pusat kendali |

### Bentuk yang disarankan

```
Masyarakat  --(kanal publik, tanpa akun)-->  citizen_reports  --(triase)-->  Petugas
```

- Pengiriman **tanpa akun**. Bila perlu penanda untuk melacak status laporan, gunakan
  **nomor tiket acak** yang diberikan saat mengirim — bukan akun, bukan identitas.
- Bila kelak diperlukan verifikasi (misalnya OTP nomor telepon), simpan identitasnya di
  **penyimpanan terpisah** dari basis data intelijen, dan itu keputusan privasi
  tersendiri (**REQUIRES HUMAN / POLICY APPROVAL**).
- Sisi kepolisian: triase laporan masuk sudah tercakup permission `citizen_report:read`
  dan `citizen_report:write` yang dimiliki Command Center dan Polsek. **Tidak perlu peran
  baru.**

---

## 4. EVALUASI JUMLAH PERAN

### 4.1 Pemisahan mana yang benar-benar berguna

| Pemisahan | Menjaga apa | Penilaian |
|---|---|---|
| **Pimpinan vs seluruhnya** | Yang mengusulkan bukan yang memutuskan — inti klaim human-in-the-loop | **Wajib dipertahankan** |
| **Polsek (wilayah)** | Kebutuhan untuk tahu, dan bukti RBAC paling mudah diperagakan | **Wajib dipertahankan** |
| **Administrator tanpa kewenangan operasional** | Kewenangan teknis ≠ kewenangan operasional | **Wajib dipertahankan** |
| **Analyst vs Command Center** | — | **Dapat digabung** (§4.2) |
| **Fungsi (fungsi)** | Hanya dapat ditegakkan pada rekomendasi dan tindakan | **Perlu dikoreksi** (§4.3) |

### 4.2 Analyst + Command Center dapat digabung

Alasan pemisahan yang biasa dikemukakan adalah menghindari "menilai pekerjaan sendiri":
yang mencatat hasil nyata sebaiknya bukan yang menghitung ketepatan prediksi.

**Alasan itu tidak berlaku pada susunan sekarang.** Analyst sudah memegang `crime:write`
**dan** `evaluation:run` sekaligus — risiko menilai pekerjaan sendiri sudah ada di dalam
satu peran, sehingga memisahkannya dari Command Center tidak menutup apa pun.

Yang benar-benar berharga dijaga adalah pemisahan yang berbeda garisnya: **siapa pun yang
mencatat `prediction_actual` sebaiknya bukan yang menjalankan evaluasi.** Itu dapat
ditegakkan lewat permission, bukan lewat jumlah peran.

Kerugian penggabungan: enam peran sekarang mendekati struktur organisasi Polri, dan
peran yang mencerminkan struktur nyata lebih mudah dipertahankan di hadapan penguji
daripada abstraksi perancang sistem.

### 4.3 Cakupan Fungsi harus dikoreksi, bukan dibiarkan

Dua pilihan:

| | Tindakan | Konsekuensi |
|---|---|---|
| **A** | Persempit deklarasi ke yang dapat ditegakkan: `crime:read` dan `intelligence:read` menjadi `ALL` | Jujur terhadap kenyataan. Fungsi memang melihat seluruh kejadian — dan itu masuk akal, sebab kejadian tidak dimiliki oleh satu fungsi |
| **B** | Tambahkan kolom fungsi pada `crime_incidents` dan `intelligence_reports` | Perubahan schema besar, dan secara konseptual keliru: sebuah kejadian curanmor bukan "milik" Reskrim |

**Rekomendasi: A.** Deklarasi disesuaikan dengan kenyataan, bukan kenyataan dipaksa
mengikuti deklarasi.

### 4.4 Susunan yang diusulkan — **5 peran**

| # | Peran | Ringkasnya | Perubahan |
|---|---|---|---|
| 1 | **Pimpinan** | Memutuskan rekomendasi | tetap |
| 2 | **Pusat Kendali** | Menyiapkan data, menjalankan prediksi dan evaluasi, memantau peringatan, mencatat operasi | **gabungan Analyst + Command Center** |
| 3 | **Fungsi** | Menindaklanjuti rekomendasi bagi fungsinya | cakupan dikoreksi (§4.3) |
| 4 | **Polsek** | Bertindak di wilayah hukumnya | tetap |
| 5 | **Administrator** | Akun, peran, konfigurasi | tetap |

Masyarakat **tidak** menjadi peran keenam — ia kanal terpisah tanpa akun (§3).

---

## 5. KEPUTUSAN YANG DIPERLUKAN

1. **Gabungkan Analyst dan Command Center menjadi satu peran?**
   Ya / Tidak. Bila ya, usul nama: **Pusat Kendali**.

2. **Setuju masyarakat menjadi kanal terpisah tanpa akun**, bukan peran RBAC?

3. **Koreksi cakupan Fungsi** menurut §4.3 pilihan A?

4. **Prioritas pekerjaan berikutnya** — usul saya berurutan:
   a. Layar tindakan operasional dan hasil nyata (menutup rantai, menopang criteria #06);
   b. Seed dan layar laporan masyarakat (TASK 024), termasuk kanal pengiriman publik;
   c. Layar laporan intelijen dan patroli;
   d. Layar audit trail.
