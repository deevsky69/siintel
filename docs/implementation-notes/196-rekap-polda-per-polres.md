# 196 — Rekap Polda Metro Jaya per Polres (25 November 2026)

**USER DECISION.** Pemilik proyek, 25 November 2026: "cek data xlsx terbaru yang saya push ke
github … implementasi agar sekarang saya punya data polres seluruhnya di polda metro."

## Sumber

`docs/Rekap_Data_Kriminal_Keseluruhan_dan_3C_Polda_Metro_Jaya_Per_Polres_2024-20261110.xlsx`
— rekap Pusiknas Bareskrim Polri, posisi data 10 November 2026 pukul 17.19 WIB. Delapan lembar:
Keterangan, Ringkasan, Tabel 1 (3C per Polres), Tabel 2 (keseluruhan per Polres), 3C per
Polres dan jenis, per jenis 3C, per bulan, jenis terbanyak. 13 Polres dan 7 satuan kerja
tingkat Polda; tahun 2024, 2025, dan 2026 sampai 10 November.

**FACT FROM DOCUMENT — ini data AGREGAT.** Isinya jumlah Laporan Polisi (CT) menurut tanggal
laporan dan penyelesaian (CC) per satuan per tahun. Tidak ada baris per kejadian, tidak ada
kelurahan, jam, atau koordinat untuk Polres lain. Karena itu:

- yang dapat dibangun adalah **perbandingan antarsatuan**, bukan peta kelurahan, analitik, atau
  prediksi untuk Polres lain;
- angka Jakarta Selatan di sini (3C 2025: menurut tanggal laporan, seluruh 3C) **tidak sama**
  dengan layar lain yang menghitung kejadian menurut tanggal kejadian; layar menuliskannya.

## Yang dibangun

| Bagian | Isi |
|---|---|
| Migrasi 0035, tabel `polda_recaps` | satu baris per posisi data: `position_at` (unik), `source`, `source_sha256`, `payload` JSONB, `imported_by`, `imported_at` |
| `scripts/import/rekap_polda.py` | membaca berkas, memvalidasi, mencetak ringkasan; dengan `--kirim` mengirim ke API atas nama akun `config:manage` |
| `GET /polda/recap` | posisi terbaru + turunan: CR, porsi terhadap Polda, porsi 3C terhadap keseluruhan, peringkat antar-Polres |
| `PUT /polda/recap` | menerima paket impor, memvalidasi ulang, mencatat audit `IMPORT_POLDA_RECAP` |
| `/ops/polda` (menu Wilayah → Polda Metro) | ringkasan per tahun, sorotan Jakarta Selatan, peta 3C per Polres, enam tabel |

**TECHNICAL DECISION — satu tabel JSONB.** Rekap adalah tabel acuan yang selalu diganti satu
paket dan hanya dibaca; tidak ada penyaringan atau penggabungan per baris. Skema isi dijaga
pydantic (kolom di luar skema ditolak), bukan oleh kolom basis data.

**TECHNICAL DECISION — impor lewat API, bukan langsung ke basis data.** Jalur yang sama
berlaku di lokal dan produksi, tervalidasi dua kali (skrip dan API), dan tercatat di audit.
API tidak perlu pustaka Excel.

**Validasi impor** (satu selisih menggagalkan): jumlah per satuan = baris JUMLAH untuk CT, CC,
dan tiap jenis 3C; curat + curas + curanmor = jumlah 3C; jumlah per bulan = jumlah setahun;
lembar Ringkasan = baris JUMLAH. Berkas 10 November 2026 lolos seluruhnya.

Beranda tidak diubah: tetap hanya Jakarta Selatan yang diwarnai, sesuai Lampiran M naskah.

## REQUIRES HUMAN / POLICY APPROVAL

1. **Berkas sumber berlabel CONFIDENTIAL dan berada di repositori GitHub yang PUBLIK**
   (`docs/`, commit 609b51c). Aturan repositori menaruh data mentah di `data/raw/` yang
   diabaikan git. Menghapusnya dari riwayat adalah operasi destruktif dan keputusan pemilik
   data — tidak dikerjakan di sini.
2. **Siapa yang boleh membaca rekap.** PROPOSED: `analytics:read` dengan cakupan seluruh
   wilayah (Pimpinan, Kasat, Wakasat, KBO, Analis, Fungsi, Administrator); Polsek dan Humas
   tidak. Tidak ada izin baru yang dibuat.

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh (tiga test baru dengan
angka buatan: impor dan turunan, penolakan bila jumlah tidak cocok atau ada kolom asing,
pembatasan akses); migrasi 0035 naik-turun; web `tsc`, `biome`, `vitest` 439 lulus,
`next build`. Berkas asli diimpor ke basis data lokal lewat API dan halamannya diperiksa
lewat potret pada lebar 1440 dan 390, termasuk keadaan "Tidak berwenang" untuk akun Polsek.
