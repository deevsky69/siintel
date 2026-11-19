# 186 — IKW, tahap KBO, dan Humas mengikuti naskah Taskap final (19 November 2026)

Keputusan pemilik proyek 19 November 2026 ("samakan untuk hal-hal yang beda") atas matriks
perbandingan aplikasi dengan `TASKAP_FINISH.docx`. Model dibahas di catatan 185.

## 1. IKW (naskah Bab IV B.4.2, Lampiran 9) — migrasi 0028

`IKW = 25 × (0,50 F + 0,35 D + 0,15 T)`, menggantikan frekuensi/tren/konsistensi (catatan 176).

| Unsur | Cara hitung |
|---|---|
| F | 0 bila nihil 12 bulan; selain itu 1–4 menurut kuartil volume positif antarkelurahan |
| D | dampak tertinggi yang TERVERIFIKASI dalam tiga bulan: 1 percobaan, 2 kehilangan/kerusakan, 3 cedera, 4 cedera berat/kematian |
| T | jumlah bulan berkejadian dalam empat bulan terakhir |

Dihitung atas seluruh 3C, apa pun cakupan peringkatnya. Status **LENGKAP / SEMENTARA /
DITAHAN** mengikuti verifikasi dampak; yang ditahan tidak diterbitkan (IKW kosong), bukan
dianggap nol. Contoh hitung naskah (70, lalu 87,5 setelah cedera berat) dijadikan test.

**Akibat yang perlu diketahui:** data Pusiknas tidak memuat dampak. Sampai petugas mengisinya
di Mutu Data (dengan rujukan sumber), hampir semua kelurahan yang punya kejadian dalam tiga
bulan terakhir berstatus DITAHAN. Itu sesuai naskah ("IKW mengikuti status verifikasi
dampak"), tetapi layar Peringkat akan banyak menampilkan "ditahan" sampai pengisian berjalan.
Siapa yang mengisi (naskah: PIC Satreskrim/Polsek memeriksa, analis mencatat, KBO memeriksa
status) saat ini pemegang `crime:triage`, yaitu Administrator — REQUIRES USER APPROVAL bila
ingin dipindahkan.

## 2. Rantai empat tahap — migrasi 0029

Analis Intelkam → **KBO** → Kasat Intelkam → Pimpinan, sesuai naskah B.4.4 dan Lampiran 9 D.
**Membalik keputusan tiga tahap 17 November 2026** (catatan 183, "staf dan KBO sama saja").

- Peran **KBO** (ROLE-07) dengan `monthly_product:review`; endpoint `/kbo` dihidupkan lagi.
- `Staf Intelkam` kembali bernama `Analis Intelkam` (istilah naskah).
- Status: DRAFT → ANALYST_REVIEWED → KBO_CHECKED → VALIDATED → DECIDED. Pengembalian oleh
  KBO atau Kasat selalu ke analis, dan produk melewati KBO lagi.
- Empat hak (`draft`, `review`, `validate`, `decide`) masing-masing dipegang tepat satu peran;
  dijaga test. Peringatan catatan 183 tetap berlaku dan kini lebih tajam: bila KBO dan Kasat
  diklik orang yang sama, masalah 10 November terulang.

## 3. Humas — migrasi 0029

**Membalik keputusan 18 November 2026** (tidak ada peran Humas). Peran **Humas** (ROLE-08)
memegang `public_info:approve`. Yang ditahan sampai disetujui: **imbauan bulanan** ke grup
dan ke pelanggan (tabel `advisory_approvals`, 0022, dipakai lagi).

Yang BELUM mengikuti naskah, dinyatakan apa adanya:

- Ringkasan wilayah di situs warga tetap terbit otomatis dari data; naskah menyebutnya
  "diverifikasi dan disetujui Humas". Menahannya berarti situs warga kosong sampai disetujui —
  keputusan tersendiri.
- Buletin mingguan dan peringatan publik tetap disetujui Pimpinan.
- `/info` atas permintaan warga tidak ditahan.

## Akun

`demo.kbo` dan `demo.humas` dibuat migrasi tanpa kata sandi yang sah; ditetapkan lewat
`scripts/sandi-peragaan-produksi.sh` (kini delapan akun). Delapan peran.

## Yang masih berbeda dari naskah final

Model 2026 (83 vs 86; catatan 185); isian dampak belum terisi; ringkasan wilayah belum lewat
Humas; pencocokan antarkanal belum memakai nomor laporan, ciri objek, dan uraian; peta belum
menggambar kejadian tambahan; satu layar profil kelurahan; formulir skor mutu draf dan waktu
kerja (Lampiran 10); draf rekomendasi disusun aturan, bukan model.

## Verifikasi

API 796 lulus pada basis data berisi data contoh; migrasi 0028 dan 0029 naik-turun; matriks
`docs/03` dibangkitkan ulang. Web `tsc`, `biome`, `vitest` 430 lulus, `next build`.
