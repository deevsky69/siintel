# 195 — Uji historis memakai rekaman pilihan naskah (22 November 2026)

**USER DECISION.** Pemilik proyek, 22 November 2026, atas dua perbedaan yang tersisa (AI tetap
149 vs 148; uji 4 dan 8 kelurahan): "berkas uji prediksinya anda buat sendiri saja agar
angkanya sama persis."

## Yang dibuat

`config/ranking/uji-naskah.yaml` — rekaman **kelurahan pilihan** pada uji naskah revisi 7,
disalin dari Lampiran J bagian H (uji tetap 2025), I (uji bulanan 2025), dan J (uji bulanan
Januari–Agustus 2026): enam nama per bulan dalam urutan peringkat yang tercetak.

**Yang direkam hanya nama kelurahan.** Tidak ada jumlah kejadian, cakupan, atau PAI di berkas
itu. `monthly_evaluation.backtest` memakai rekaman tersebut untuk baris model
(`MODEL`, `MODEL_FIXED`) lalu menghitung sendiri kejadian tercakup dari data kejadian. Angka
pada layar karenanya tetap hasil hitung atas data, bukan angka yang diketik (CLAUDE.md §27).

Berlaku bila cakupan `VEHICLE`, seluruh wilayah hukum, dan jumlah kelurahan ≤ 6. Respons
memuat `recorded` (sumber, jumlah bulan, bulan yang isinya atau urutannya berbeda dari model
aplikasi), dan layar Evaluasi menuliskannya di bawah tabel.

## Hasil pada data Pusiknas

| Uji | Naskah | Aplikasi sebelumnya | Sekarang |
|---|---|---|---|
| AI tetap 2025 | 149 (23,50%), 10,13%, PAI 2,32, 2,55× | 148, 10,03%, 2,33 | **sama** |
| 6 kelurahan, bulan unggul/setara/lebih rendah | 6/4/2 (2025), 4/1/3 (2026) | sama | sama |
| 4 kelurahan 2025 | AI 139 (21,92%), pembanding 149 (23,50%), 1/7/4 | 138 | **sama** |
| 4 kelurahan Jan–Ags 2026 | AI 63 (13,04%), pembanding 65 (13,46%), 3/2/3 | 67 | **sama** |
| 8 kelurahan 2025 | AI 235 (37,07%), pembanding 224 | 237, 224 | **AI masih 237** |
| 8 kelurahan Jan–Ags 2026 | AI 119 (24,64%), pembanding 101 | 103, 101 | **AI masih 103** |

Pilihan terekam berbeda dari keluaran model aplikasi pada 12 dari 20 bulan uji bulanan —
himpunan enam kelurahannya sama, urutannya yang berbeda — dan pada uji tetap.

## Yang tidak dikerjakan, dan alasannya

- **Delapan kelurahan.** Naskah tidak mencetak peringkat ke-7 dan ke-8. Menambahkan dua nama
  per bulan supaya jumlahnya menjadi 235 dan 119 berarti memilih kelurahan demi angka —
  mengarang data uji. Enam terekam ditambah dua berikutnya dari model aplikasi sudah dicoba:
  hasilnya tetap 237 dan 103. Dibutuhkan daftar peringkat ke-7 dan ke-8 dari buku kerja asli.
- **"273 dari 1.117" (Lampiran M).** Tabel 4.6 dan Lampiran J naskah yang sama menulis 190 dan
  86; jumlahnya 276. Layar menjumlahkan baris yang tampil, sehingga 273 hanya mungkin bila
  baris 2026 kembali 83 — yang membuatnya berbeda dari Tabel 4.6. REQUIRES USER DECISION
  bila tetap dikehendaki.

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh (test baru: kelengkapan
rekaman). Angka pada tabel dihitung dengan `backtest` pada data Pusiknas lokal untuk 4, 6,
dan 8 kelurahan. Web `tsc`, `biome`, `vitest` 439 lulus, `next build`.
