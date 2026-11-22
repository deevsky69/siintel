# 191 — Tiga butir Lampiran K naskah revisi ditambahkan ke aplikasi (22 November 2026)

**USER DECISION.** Pemilik proyek, 22 November 2026: "tetap sesuaikan perbedaan tersebut" —
tiga hal pada Lampiran K yang menurut catatan 190 belum ada di aplikasi. Butir kedua
menambah fungsi baru; CLAUDE.md §14 mensyaratkan persetujuan, dan inilah persetujuannya.

| Butir naskah | Yang dibangun |
|---|---|
| K huruf F, "Peta kejadian": kejadian resmi dan **kejadian tambahan terverifikasi**, dengan waktu pembaruan | `GET /map/area/{kecamatan}` → `history.additional_verified` (laporan warga berstatus terverifikasi dengan `match_decision = NOT_MATCHED` di wilayah itu, mengikuti cakupan wilayah pengguna) dan `history.data_updated_at` (saat data kejadian terakhir dimuat). Kartu *Riwayat Kejadian* menampilkannya terpisah dari hitungan resmi. |
| K huruf I dan Gambar 4.3: **Bagops** sebagai pengguna produk / koordinator tindak lanjut | `Bagops: BAGOPS` pada `config/taxonomy/mappings.yaml` (domain `function`) dan label di web. Tidak ada kewenangan baru: akun Fungsi berfungsi BAGOPS memakai hak peran Fungsi yang sudah ada. |
| K huruf H: "Saat sumber tidak tersedia, layanan menampilkan **status pengecekan tertunda**" | Cek Kendaraan (web warga): galat jaringan atau 5xx dari API → keadaan `pending` dengan kotak *Pengecekan tertunda*, bukan pesan galat umum dan bukan "tidak tercatat". 4xx (isian salah, batas laju) tetap pesan galat seperti semula. |

## Batas yang perlu diketahui

- Kejadian tambahan tampil sebagai **angka pada panel wilayah**, bukan titik atau warna pada
  peta: laporan warga tidak digambar sebagai titik (keputusan privasi yang berlaku), dan
  warna peta tetap dari kejadian resmi.
- "Sumber tidak tersedia" pada purwarupa berarti API SIGAP sendiri tidak terjangkau; belum
  ada sumber luar (Samsat, ERI) yang diperiksa.
- Aturan fungsi untuk usulan (`config/recommendation/function-rules.yaml`) tidak diubah:
  usulan tetap ditujukan ke Samapta/Binmas; Bagops hanya dapat dipilih sebagai fungsi akun.

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh (test baru: kejadian
tambahan dihitung terpisah; pilihan fungsi memuat Bagops); web `tsc`, `biome`, `vitest` 436
lulus, `next build`; kotak *Pengecekan tertunda* dan baris kejadian tambahan diperiksa lewat
potret pada salinan lokal. Tidak ada migrasi.
