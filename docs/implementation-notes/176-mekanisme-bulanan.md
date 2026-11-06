# 176 — Penyesuaian ke "Mekanisme dan Fungsi SIGAP" (6 November 2026)

Dokumen mekanisme (lima modul) menjadi acuan baru. Keputusan pemilik proyek: **1B** enam
peran (Pimpinan, Kasat Intelkam, Analis Intelkam, Fungsi, Polsek, Administrator), **2A** peta
3 bulan dulu, **3A** imbauan bulanan warga perlu persetujuan; menu dan teks diringkas.

| Tahap | Isi | Status |
|---|---|---|
| 1 | Modul 1: `vehicle_object`, `area_pending`, dugaan ganda, `crime_incident_revisions`, layar Pembakuan (0019) | **selesai 6 Nov 2026** |
| 2 | Modul 2–3: peringkat bulanan 65 kelurahan tersimpan (peta 3 bulan, 12 bulan, IKW), batas data, layar Peringkat | — |
| 3 | Modul 4: produk bulanan, empat tahap (Analis → KBO → Kasat → Pimpinan), peran baru, pimpinan memilih N kelurahan, alasan wajib | — |
| 4 | Modul 4b: pelaksanaan dicatat Fungsi/Polsek per kelurahan prioritas | — |
| 5 | Modul 5: cakupan, pembanding peta historis pada N sama, PAI, rekap usulan, tinjauan pelaksanaan | — |
| 6 | Menu ringkas, teks dipangkas, peringatan harian keluar dari alur utama, imbauan warga perlu persetujuan | — |

## Tahap 1 — pilihan teknis

- Objek kendaraan dari `target_type = 'Kendaraan bermotor'` (nilai Pusiknas apa adanya): 5.119
  baris, 644 pada 2025 — persis angka Uji Prediksi 2025.
- Kelurahan tertunda = lokasi tingkat kecamatan (413 baris). Perhitungan per kelurahan memang
  sudah tidak memuatnya; kini jumlahnya tampil dan dapat dipastikan satu per satu.
- Dugaan ganda hanya pada entri petugas: sejenis, lokasi sama, ±1 hari (PROPOSED). Yang
  CONFIRMED disembunyikan lewat saringan ORM global (`services/visibility.py`) — satu tempat.
- Entri petugas diberi `data_source = ENTRI:<unit>` supaya terpisah dari rekaman Pusiknas tanpa
  tabel baru.
