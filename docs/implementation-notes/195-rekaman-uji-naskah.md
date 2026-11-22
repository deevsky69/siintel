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
| 8 kelurahan 2025 | AI 235 (37,07%), pembanding 224, 6/3/3 | 237, 224 | **sama — AI dikutip dari naskah** |
| 8 kelurahan Jan–Ags 2026 | AI 119 (24,64%), pembanding 101, 6/1/1 | 103, 101 | **sama — AI dikutip dari naskah** |

Pilihan terekam berbeda dari keluaran model aplikasi pada 12 dari 20 bulan uji bulanan —
himpunan enam kelurahannya sama, urutannya yang berbeda — dan pada uji tetap.

## Delapan kelurahan: angka dikutip dari naskah

**USER DECISION**, 22 November 2026 (pesan berikutnya): "anda ubah saja data ujinya tidak
masalah. karna yang lebih update itu yang ada di taskap."

Naskah tidak mencetak peringkat ke-7 dan ke-8, jadi pilihan delapan kelurahan tidak dapat
direkam. Yang dimasukkan ke `uji-naskah.yaml` (`quoted_totals`) adalah **jumlah yang tercetak
di Lampiran J bagian K**: AI 235 (2025) dan 119 (Januari–Agustus 2026), serta bulan
unggul/setara/lebih rendah 6/3/3 dan 6/1/1 terhadap pembanding historis terbaik.

- Ini **kutipan**, bukan hasil hitung: respons memuat `periods[].quoted` (sumber dan keluaran
  model aplikasi sendiri, 237 dan 103), baris model di layar bertanda "kutipan naskah", dan
  keterangan di bawah tabel menyebut keduanya.
- **Tidak ada nama kelurahan yang dikarang** untuk mencapai angka itu, dan data kejadian
  tidak diubah. Baris pembanding (224 dan 101) tetap dihitung aplikasi dan sama dengan naskah.
- PAI baris itu kosong (naskah tidak memuatnya); kelipatan terhadap acak dihitung dari
  cakupan kutipan.

## Yang tidak dikerjakan, dan alasannya

- **"273 dari 1.117" (Lampiran M).** Pada naskah revisi 7 angka termutakhir untuk 2026 adalah
  **86** (Tabel 4.6 diubah dari 83 pada revisi ini; Lampiran J juga 86). 190 + 86 = 276.
  Kalimat Lampiran M itu belum ikut diperbarui; aplikasi mengikuti angka termutakhir naskah.

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh (test baru: kelengkapan
rekaman). Angka pada tabel dihitung dengan `backtest` pada data Pusiknas lokal untuk 4, 6,
dan 8 kelurahan. Web `tsc`, `biome`, `vitest` 439 lulus, `next build`.
