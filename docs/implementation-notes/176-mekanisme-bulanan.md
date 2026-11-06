# 176 — Penyesuaian ke "Mekanisme dan Fungsi SIGAP" (6 November 2026)

Dokumen mekanisme (lima modul) menjadi acuan baru. Keputusan pemilik proyek: **1B** enam
peran (Pimpinan, Kasat Intelkam, Analis Intelkam, Fungsi, Polsek, Administrator), **2A** peta
3 bulan dulu, **3A** imbauan bulanan warga perlu persetujuan; menu dan teks diringkas.

| Tahap | Isi | Status |
|---|---|---|
| 1 | Modul 1: `vehicle_object`, `area_pending`, dugaan ganda, `crime_incident_revisions`, layar Pembakuan (0019) | **selesai 6 Nov 2026** |
| 2 | Modul 2–3: peringkat bulanan 65 kelurahan tersimpan (peta 3 bulan, 12 bulan, IKW), batas data, layar Peringkat (0020) | **selesai 6 Nov 2026** |
| 3 | Modul 4: produk bulanan, empat tahap (Analis → KBO → Kasat → Pimpinan), peran baru, pimpinan memilih N kelurahan, alasan wajib (0021) | **selesai 6 Nov 2026** |
| 4 | Modul 4b: pelaksanaan dicatat Fungsi/Polsek per kelurahan prioritas (`monthly_actions`, 0021) | **selesai 6 Nov 2026** |
| 5 | Modul 5: cakupan, pembanding peta historis pada N sama, rekap usulan, tinjauan pelaksanaan (`GET /evaluation/monthly`) | **selesai 6 Nov 2026**; PAI menunggu luas kelurahan di API |
| 6 | Menu ringkas (lima kelompok), layar harian keluar dari menu, imbauan warga perlu persetujuan (0022) | **selesai 6 Nov 2026** |

## Tahap 1 — pilihan teknis

- Objek kendaraan dari `target_type = 'Kendaraan bermotor'` (nilai Pusiknas apa adanya): 5.119
  baris, 644 pada 2025 — persis angka Uji Prediksi 2025.
- Kelurahan tertunda = lokasi tingkat kecamatan (413 baris). Perhitungan per kelurahan memang
  sudah tidak memuatnya; kini jumlahnya tampil dan dapat dipastikan satu per satu.
- Dugaan ganda hanya pada entri petugas: sejenis, lokasi sama, ±1 hari (PROPOSED). Yang
  CONFIRMED disembunyikan lewat saringan ORM global (`services/visibility.py`) — satu tempat.
- Entri petugas diberi `data_source = ENTRI:<unit>` supaya terpisah dari rekaman Pusiknas tanpa
  tabel baru.

## Tahap 2 — pilihan teknis

- Perkiraan per kelurahan = rata-rata bulanan pada 3 bulan kalender terakhir sebelum bulan
  sasaran (HISTORY_3M, keputusan 2A); HISTORY_12M tersedia sebagai pembanding; MODEL ditolak
  400 sampai ada model yang diuji.
- Batas data = hari terakhir bulan sebelum bulan sasaran; hanya kejadian dengan
  `coalesce(reported_at, occurred_at)` ≤ batas (klausa `_known_by` yang sama dengan evaluasi
  mundur). Kejadian `area_pending` tidak ikut; jumlahnya disimpan (`pending_count`).
- Seri: nama kelurahan (abjad), sesuai dokumen. Seluruh kelurahan masuk, termasuk yang nol.
- IKW = 0,5·frekuensi(12 bulan, dinormalkan ke tertinggi) + 0,25·tren(3 vs 9 bulan, 0–100)
  + 0,25·konsistensi(bagian bulan ≥1 kejadian). Bobot dan kategori di
  `config/ranking/monthly.yaml`, PROPOSED; tidak menentukan urutan.
- Pembekuan satu kali per (bulan, metode, cakupan); `generated_at` memakai waktu sebenarnya.

## Tahap 3–4 — pilihan teknis

- Peran baru menempati jenjang kosong: Kasat Intelkam level 2 (ROLE-02), Analis Intelkam
  level 3 (ROLE-03). Akun peragaan `demo.kasat`/`demo.analis` dibuat TERKUNCI oleh migrasi;
  kata sandi lewat `scripts/sandi-peragaan-produksi.sh` (kini enam akun).
- Tahap KBO: `monthly_product:review` dipegang Kasat Intelkam dan Analis Intelkam (1B). Siapa
  yang mencatatnya terlihat di `monthly_product_stages.acted_by`.
- Administrator hanya `read` + `draft`; `review`/`validate`/`decide`/`execute` bukan
  pekerjaannya (test pemisahan tugas diperbarui).
- Draf mengusulkan `draft_top_n = 10` kelurahan teratas (config/ranking/monthly.yaml);
  Pimpinan bebas memilih jumlah dan kelurahan mana pun yang tidak ditolak analis.
- Polsek mencatat kegiatan hanya di kelurahan polseknya — ditegakkan endpoint (404), bukan
  lewat scope OWN_JURISDICTION, karena item membawa `polsek` tetapi bukan tabel yang dikenal
  pemeriksa scope.
- Rekomendasi harian (`recommendations`, `commander_decisions`) dibiarkan; keluar dari menu
  pada tahap 6.

## Tahap 5 — pilihan teknis

- Cakupan dihitung per peringkat beku pada N teratas; N = `priority_count` produk bila sudah
  ditetapkan, selain itu `evaluation.default_top_n` (6, seperti Uji Prediksi 2025).
- Pembanding dihitung ulang dengan batas data peringkat beku (`ranking.compute(..., data_cutoff)`)
  — bukan dari data yang diketahui belakangan.
- Kejadian tanpa kelurahan / `area_pending` dilaporkan sebagai "belum dapat dipetakan", tidak
  masuk pembilang maupun penyebut.
- PAI belum dihitung: `locations.geom` titik; poligon kelurahan hanya ada di web
  (`lib/wilayah`). Memindahkannya ke API adalah pekerjaan tersendiri.

## Tahap 6 — pilihan teknis

- Menu: Wilayah · Bulan Ini · Data · Warga · Sistem. Rute harian (`/ops/peringatan`,
  `/ops/prediksi`, `/ops/skoring`, `/ops/rekomendasi`, `/ops/operasi`, `/ops/brief`,
  `/ops/informasi`, `/ops/evaluasi`) tidak dihapus — hanya tidak ada di menu — supaya tautan
  lama dan data yang sudah tercatat tetap dapat dibuka.
- Lencana sidebar kini menghitung produk bulanan yang menunggu penetapan Pimpinan (status
  VALIDATED), bukan rekomendasi harian.
- Imbauan bulanan: satu persetujuan per bulan (`advisory_approvals`); bot membaca
  `approved` dari antrean. Keputusan 4 November (otomatis) direvisi oleh pemilik proyek (3A).
- Beranda `/ops` masih memuat ringkasan harian (peringatan, prediksi); penyusunan ulang
  beranda mengikuti siklus bulanan adalah pekerjaan berikutnya.
