# TASK 031, 032, 036, 037, 038, 040 — API BACA + AGREGAT DASHBOARD

Tanggal: 2026-09-01
Status: **SELESAI — diverifikasi terhadap data nyata lewat HTTP.**

| Endpoint | Permission | Isi |
|---|---|---|
| `GET /locations` | `location:read` | Master wilayah/grid |
| `GET /crimes` | `crime:read` | Kejadian, filter tanggal/jenis/kecamatan |
| `GET /risk-scores` | `risk_score:read` | Layer risiko berjalan |
| `GET /predictions` | `prediction:read` | Prediksi + WHY, filter horizon/ancaman/status |
| `GET /warnings` | `warning:read` | Peringatan dini |
| `GET /recommendations` | `recommendation:read` | Rekomendasi per fungsi |
| `GET /evaluation/metrics` | `evaluation:read` | Precision, recall, FP, FN |
| `GET /evaluation/summary` | `evaluation:read` | Rincian per jenis ancaman |
| `GET /dashboard/summary` | `dashboard:read` | Agregat layar utama |
| `GET /dashboard/trends` | `dashboard:read` | Tren kejadian per bulan |
| `GET /dashboard/predictive-outlook` | `prediction:read` | Prediksi per horizon |

---

## 1. WAKTU ACUAN — KEPUTUSAN SDL-16 AKHIRNYA TERPAKAI

Dataset berhenti 31 Desember 2025, demo berjalan September 2026. Tanpa penanganan, seluruh
panel "24 jam terakhir" akan kosong — dan panel kosong sulit dibedakan dari sistem rusak.

`services/clock.py` menyediakan "sekarang" versi aplikasi. Tanggal historis **tidak digeser**
(itu akan merusak pembagian data latih/validasi `docs/01` §8); yang digeser hanya acuan waktunya.

Setiap respons dashboard menyertakan `reference_time` dan `demo_clock`, sehingga antarmuka
dapat menyatakannya terbuka. Dengan `DEMO_REFERENCE_TIME=2025-12-27T09:30+07:00`:

```text
kejadian 24 jam : 2      prediksi 24 jam : 4
warning aktif   : 36     jam kritis      : 18:00-23:59
```

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | Penyaringan cakupan dilakukan **di query**, bukan setelah data terambil | Pengguna ber-scope tidak menerima baris di luar wilayahnya, bahkan tidak lewat `total_items` |
| 2 | `security_index` = 100 − rata-rata **seluruh sel** risiko, bukan rata-rata puncak per kecamatan | Versi pertama memakai puncak dan menghasilkan indeks 19 — satu sel kritis mewakili seluruh wilayah. Setelah diperbaiki: 47 |
| 3 | Setiap angka turunan membawa `*_basis` | Indeks keamanan bukan angka resmi (U-01/U-02); menampilkannya tanpa penjelasan asal akan menyesatkan |
| 4 | Prediksi **selalu** keluar bersama `dominant_factors` beserta `source` | Menyembunyikan asal penjelasan membuat hasil aturan terbaca sebagai temuan model (CLAUDE.md §27) |
| 5 | Metrik evaluasi **selalu** bertanda `PROPOSED` + `basis` | Aturan pencocokan belum ditetapkan (U-03) |
| 6 | Precision/recall dijawab `null` bila penyebutnya nol | "Tidak dapat dihitung" berbeda maknanya dari "nilainya nol" |
| 7 | Batas `page_size` 200 | Membatasi biaya satu permintaan; melebihi batas dijawab 400 |

---

## 3. VERIFIKASI PENEGAKAN CAKUPAN — DENGAN DATA NYATA

Tiga akun diberi password lewat CLI, lalu jumlah kejadian yang terlihat dibandingkan:

```text
Pimpinan   1200
Analyst    1200
Polsek      159      seluruhnya Polsek Tebet
```

Ini bukti bahwa cakupan ditegakkan backend, bukan sekadar menu yang disembunyikan.

Contoh WHY yang benar-benar keluar dari API:

```text
PRD-00116  Kebayoran Baru  CURANMOR  risk 54  conf 63
  historical_incident_density  0.378  RULE
  recent_incident_trend        0.185  RULE
  spatial_concentration        0.181  RULE
```

Evaluasi:

```text
hit 60 | fp 91 | fn 90 | precision 0.397 | recall 0.4 | status PROPOSED
```

---

## 4. CATATAN ATAS SEBUAH TEST YANG DIPERBAIKI

`test_demo_accounts_cannot_be_used_to_log_in` gagal setelah password ditetapkan lewat CLI.
Test itu memeriksa **keadaan database**, padahal yang seharusnya dijaga adalah **perilaku seed**.
Diganti menjadi `test_seeding_never_creates_a_usable_password`, yang menguji bahwa seed tidak
pernah menghasilkan kredensial dapat pakai — tanpa memaksa seluruh akun tetap terkunci selamanya.

---

## 5. HASIL PEMERIKSAAN

```text
ruff + format (70 berkas) → bersih
mypy (70 berkas)          → no issues
pytest                    → 216 lulus
```

## 6. BERIKUTNYA

**TASK 070** — menyambungkan dashboard ke API ini sehingga angka pada layar berasal dari
database, bukan dari kode.
