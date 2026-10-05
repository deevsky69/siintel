# 016 — Eksperimen model terlatih pertama (5 Oktober 2026)

**Status: selesai, TIDAK dipasang ke aplikasi.** Skrip: `scripts/ml/baseline_model.py`
(dijalankan dengan grup dependensi `analysis`, di luar image produksi).

## Pertanyaan

Tabel ambang (`/evaluation/threshold-sweep`) menunjukkan precision mesin aturan tetap ±1%
pada ambang berapa pun. Apakah model yang benar-benar dilatih pada 2023–2025 dan diuji pada
2026 memperbaikinya?

## Rancangan

| Hal | Nilai |
|---|---|
| Unit | kelurahan × jenis × jendela 6 jam × hari sasaran (sama dengan evaluasi mundur) |
| Label | ada ≥1 kejadian berjam tercatat pada unit itu di hari sasaran |
| Fitur (11) | kejadian unit yang *dilaporkan* dalam 7/30/90/365 hari; sel×jenis 30/365; sel 365; jenis×jendela 365 (pola jam); kecamatan×jenis 30; hari-dalam-pekan (sin/cos) |
| Kejujuran waktu | seluruh fitur dari kejadian yang **dilaporkan** sampai H-1 (`reported_at`), bukan yang terjadi |
| Model | regresi logistik, bobot kelas seimbang, L2, log1p + standardisasi |
| Latih / uji | hari sasaran 2024-01-01..2025-12-31 (657.900 baris, 2.383 positif) / 2026-01-03..2026-09-28 (242.100 baris, 758 positif) |
| Pembanding | peringkat menurut kejadian unit 365 hari (persis gagasan "persistensi" mesin aturan) |

Evaluasi dibuat setara: **pada jumlah peringatan per hari yang sama**, berapa precision dan
recall tiap pendekatan.

## Hasil

### Harian (H+1, jendela 6 jam)

| Peringatan/hari | Model: precision / recall | Peringkat riwayat: precision / recall |
|---|---|---|
| 77 | 0,011 / 0,307 | 0,010 / 0,277 |
| 20 | 0,014 / 0,100 | 0,014 / 0,102 |

AUC uji 0,775 — model **mengurutkan** dengan wajar, tetapi laju dasar per unit-hari hanya
≈0,3% (758 positif dari 242.100 unit-hari), sehingga precision tidak dapat tinggi berapa
pun pengurutannya.

### Mingguan (ada kejadian dalam 7 hari ke depan, satu usulan per pekan)

| Slot/pekan | Model: precision / recall | Peringkat riwayat: precision / recall |
|---|---|---|
| 30 | 0,085 / 0,134 | 0,083 / 0,130 |
| 15 | 0,112 / 0,088 | 0,100 / 0,079 |

## Kesimpulan

1. **Model terlatih ≈ penghitungan riwayat.** Selisihnya di bawah dua angka di belakang
   koma. Sinyal yang ada di data memang sinyal kepadatan historis — dan itu yang sudah
   dipakai mesin aturan dan rencana patroli.
2. **Satuan harian × 6 jam terlalu halus untuk data ini.** Sekitar 4 kejadian per hari
   tersebar di 520 unit; tidak ada metode yang dapat menebak unit mana hari ini. Pada
   satuan **mingguan** precision naik sepuluh kali lipat (≈10%), dan pada satuan
   **tahunan** (rencana patroli) ketepatan slot 57%.
3. Karena itu model **tidak dipasang**: memasangnya menambah kerumitan tanpa menambah
   ketepatan, dan melanggar prinsip "jangan mengejar model kompleks sebelum baseline dapat
   dievaluasi" (CLAUDE.md §25) ke arah sebaliknya — baseline sudah dievaluasi dan model
   tidak lebih baik.

## Yang mengikuti dari sini (keputusan pemilik proyek)

- **Satuan operasional peringatan**: harian × 6 jam (sekarang; precision 1%) atau
  **mingguan** per kelurahan × blok jam (precision ≈8–11% pada 15–30 slot/pekan). Yang
  kedua cocok dengan cara patroli dijadwalkan dan dengan rencana tahunan yang sudah ada.
- Bila mingguan dipilih: mesin aturan cukup diubah satuan waktunya, tanpa model baru.
- Data yang akan menambah sinyal (bukan algoritma): POI/kegiatan, cuaca, kalender —
  belum tersedia (U-19).

Reproduksi:

```bash
cd apps/api && DATABASE_URL=... uv run --group analysis python ../../scripts/ml/baseline_model.py \
  --train-from 2024-01-01 --train-to 2025-12-31 --test-from 2026-01-03 --test-to 2026-09-28
# mingguan:
#   ... --train-to 2025-12-25 --test-to 2026-09-22 --horizon-days 7 --step-days 7 --per-day 30 15
```
