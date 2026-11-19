# 185 — Model mengikuti Lampiran 8 E naskah Taskap final (19 November 2026)

Keputusan pemilik proyek 19 November 2026 ("samakan untuk hal-hal yang beda") setelah matriks
perbandingan aplikasi dengan `TASKAP_FINISH.docx`. Menggantikan rancangan model catatan 181,
yang merupakan pilihan penyusun teknis sebelum naskah final memuat resep lengkapnya.

## Yang berubah

| | Catatan 181 | Sekarang (Lampiran 8 E) |
|---|---|---|
| Algoritma | GradientBoostingRegressor, kerugian kuadrat | HistGradientBoostingRegressor, kerugian **Poisson** |
| Pengaturan | 300 pohon, kedalaman 2, daun min. 20, laju 0,03 | 100 iterasi, 7 daun, daun min. 40, laju 0,05, L2 = 2, seed 42 |
| Baris latih | 1.365 (horizon 1) | **9.750 berbobot** (horizon 1–12; bobot = 1 / jumlah horizon tersedia) |
| Bulan sasaran latih | April 2023 – Des 2024 | **Juli 2023 – Des 2024** (riwayat minimal enam bulan) |
| Masukan | 10 | 11: rerata 1/3/6/12, rerata sepanjang riwayat, selisih rerata 3 dan 12, sekecamatan 3 dan 12, horizon, sin/cos bulan |
| scikit-learn | ≥ 1.5 | **dikunci 1.8.0** (versi naskah; 1.9.1 memberi hasil berbeda) |
| Laporan tanpa tanggal kejadian | ikut (memakai tanggal laporan) | dikecualikan dari deret bulanan (naskah Tabel 6) → 3.677 kejadian latih |
| Peringkat | skor dibulatkan dua desimal dulu | skor penuh; pembulatan hanya saat disimpan |
| Alasan model | kontribusi sebagai tambahan jumlah | kontribusi sebagai **pengali** (skala log), tampil sebagai persen |

Ditambah pada uji historis: **skenario tetap** (model dengan informasi sampai akhir masa
latih, peta tahun 2024, peta Oktober–Desember 2024) dan pilihan **4, 6, atau 8 kelurahan**.

## Seberapa cocok dengan naskah

Dihitung aplikasi dari data Pusiknas yang sama (posisi 29 September 2026):

| Ukuran | Naskah | Aplikasi | |
|---|---|---|---|
| 2025, bulanan, 6 kelurahan | 190 / 634 | **190 / 634** | cocok, **termasuk tiap bulan** |
| 2025, 4 kelurahan | 139 | **139** | cocok |
| 2025, 8 kelurahan | 235 | **235** | cocok |
| Seluruh pembanding (3, 12, 1 bulan; peta 2024) | — | — | cocok (sejak catatan 181) |
| Peta Oktober–Desember 2024 | 147 | **147** | cocok |
| 2025, skenario tetap | 149 | 148 | selisih 1 (April: 13 vs 14) |
| Jan–Ags 2026, 6 kelurahan | 86 / 483 | 83 / 483 | selisih 3 (April: 17 vs 20) |
| Jan–Ags 2026, 4 kelurahan | 63 | 62 | selisih 1 |
| Jan–Ags 2026, 8 kelurahan | 119 | 103 | **selisih 16** |

Model 2025 terreplikasi persis. Untuk 2026 dan skenario tetap masih ada selisih yang tidak
dapat dijelaskan dari uraian Lampiran 8 E saja: skor beberapa kelurahan di sekitar peringkat
keenam berbeda tipis. Dua dugaan sudah diuji dan tidak cocok (melatih ulang dengan data sampai
akhir 2025; rerata sekecamatan sebagai jumlah). Kode aslinya ada pada
`Uji_Prediksi_2025_Pusiknas.xlsx`, lembar "Replikasi Python", yang tidak ada di server —
**dengan berkas itu sisanya dapat disamakan persis**.

Sampai itu, angka 2026 di aplikasi (83) berbeda dari naskah (86). Model tetap di atas
pembanding terbaik (79) pada enam kelurahan.

## Dampak pada aplikasi

- `model_version` berawalan `hgb-`. Peringkat yang sudah dibekukan dengan model lama tidak
  diubah; peringkat baru memakai model ini.
- Penjaga (`ranking.operational`) tetap berjalan: pada 12 bulan uji terakhir sebelum Januari
  2026, model 188 dari 627, pembanding terbaik 174 → model menjadi dasar usulan.
- Pada empat kelurahan pembanding historis lebih tinggi (149 vs 139, 2025) — sama seperti
  temuan naskah. Jumlah kelurahan uji bawaan tetap enam.

## Verifikasi

`uv run pytest` 793 lulus; `tests/test_monthly_model.py` memeriksa 150 pasangan (bulan,
horizon) per kelurahan, bobot baris, dan bahwa exp(nilai awal + kontribusi) = perkiraan.
Web: `tsc`, `biome`, `vitest` 430 lulus.
