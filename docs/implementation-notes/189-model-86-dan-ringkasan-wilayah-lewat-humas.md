# 189 — Angka model 86 dan ringkasan wilayah lewat Humas (21 November 2026)

**USER DECISION.** Pemilik proyek, 21 November 2026: "samakan angka model jadi 86 dan
ringkasan wilayah lewat Humas" — dua keputusan yang dibiarkan terbuka pada catatan 188.

## 1. Model — rerata kelurahan sekecamatan dihitung dengan satu pembagian

`IncidentHistory.features`: masukan `kec_3` dan `kec_12` kini = seluruh kejadian kelurahan lain
sekecamatan pada jendela itu dibagi (jumlah kelurahan × jumlah bulan). Sebelumnya dua langkah
(rata-rata per bulan, lalu rata-rata jendela). Secara matematis sama; berbeda pada digit
terakhir bilangan pecahan — dan pohon keputusan model peka terhadap itu.

| Ukuran | Naskah (Lampiran J) | Sebelum | Sesudah |
|---|---|---|---|
| 2025 bulanan, 6 kelurahan | 190 | 190 | **190** |
| Jan–Ags 2026, 6 kelurahan | 86 | 83 | **86** |
| Enam pilihan sama dengan naskah (20 bulan) | — | 19 bulan | **20 bulan** |
| Tercakup per bulan (Lampiran J huruf F dan G) | — | beda April 2026 | **sama seluruhnya** |
| 2025, 4 kelurahan | 139 | 139 | 138 |
| 2025, 8 kelurahan | 235 | 235 | 237 |
| Jan–Ags 2026, 4 kelurahan | 63 | 62 | 67 |
| Jan–Ags 2026, 8 kelurahan | 119 | 103 | 103 |
| 2025 skenario tetap | 149 | 148 | 148 |

Uji utama (enam kelurahan) kini sama dengan naskah di kedua periode; uji tambahan empat dan
delapan kelurahan TIDAK, dan untuk 2025 justru menjauh satu dan dua kejadian. Pemilik proyek
memilih ini dengan mengetahui akibatnya. Urutan di dalam enam pilihan masih berbeda pada
sebagian bulan. Penyamaan penuh tetap menunggu lembar "Replikasi Python" pada
`Uji_Prediksi_2025_Pusiknas.xlsx`. `model_version` berubah karena sidik data latih berubah;
peringkat yang sudah dibekukan tidak dihitung ulang.

Catatan untuk naskah: Tabel 4.6 ("83 (17,81%)") dan Lampiran M (273 dari 1.117) memakai angka
lama; angka aplikasi kini 86 dan 276.

## 2. Ringkasan wilayah publik menunggu persetujuan Humas — migrasi 0033

Naskah Lampiran K huruf I: "Humas menyajikan ringkasan wilayah yang disetujui."

- Tabel `area_summary_approvals` (satu baris per periode = bulan terakhir jendela 12 bulan).
- `GET /public/areas/summary`: sebelum disetujui → `published: false`, `areas` dan `kecamatan`
  kosong, `notice` berisi keterangan; angka dan tingkat **tidak dikirim**. `directory` (daftar
  kelurahan beserta nilai Survey Rasa Aman) selalu ada. Sesudah disetujui → seperti semula,
  ditambah `published: true` dan `approved_at`.
- `GET /area-summary/approval` (`bulletin:read`) pratinjau; `POST /area-summary/approval`
  (`public_info:approve`: Humas, Administrator), 409 bila periode itu sudah disetujui; audit
  `APPROVE_AREA_SUMMARY`.
- Web: panel di **Warga → Buletin & Imbauan**; Beranda dan Peta warga menampilkan keterangan
  saat belum disetujui; Survey, Babinkamtibmas, dan Berkas Perkara membaca `directory` sehingga
  tidak ikut kosong.
- **Migrasi tidak membuatkan persetujuan.** Setelah deploy, halaman warga menampilkan
  keterangan sampai Humas menyetujui periode berjalan. Dalam mode demo periodenya tetap
  (2025-12), jadi cukup sekali.
- Tidak ada pencabutan persetujuan dari layar (belum diminta).

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh; migrasi 0033 naik-turun;
hasil model dihitung ulang pada data Pusiknas untuk 4, 6, dan 8 kelurahan; web `tsc`, `biome`,
`vitest` lulus, `next build`; halaman warga (belum dan sudah disetujui) serta panel Buletin &
Imbauan diperiksa lewat potret pada salinan lokal.
