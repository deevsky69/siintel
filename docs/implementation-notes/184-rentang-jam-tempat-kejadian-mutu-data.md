# 184 — Rentang jam 4 jam, rekomendasi menurut tempat kejadian, dan Mutu Data (18 November 2026)

Penyesuaian ke naskah Taskap Bab IV — butir 4, 6, dan 7 audit naskah–aplikasi. Pemilik proyek
menyetujui pengerjaannya pada 18 November 2026 ("deploy ke produksi dan audit").

## Butir 4 — rentang jam

| | Sebelum | Sesudah |
|---|---|---|
| Satuan jam analitik | Blok 3 jam (keputusan 30 September 2026) | **Enam rentang 4 jam mulai 00.00 WIB** (naskah) |
| Rentang pada draf produk | Satu puncak per kelurahan | Puncak **per jenis kejahatan**, dengan jumlah laporan berjam dan tanpa jam |

Satu tetapan (`api/analysis.py: HOUR_BLOCK_HOURS`) — analitik, pola, lampiran jam rawan,
produk bulanan, dan panduan warga mengikutinya. Rantai harian (penilaian risiko, prediksi)
tetap memakai jendela 6 jamnya sendiri: ia sudah di luar menu dan tidak disebut naskah.

**Membalik keputusan 30 September 2026.** Angka per rentang pada layar berubah; angka yang
sudah tersimpan (peringkat dan produk yang dibekukan) tidak diubah.

## Butir 6 — rekomendasi menurut tempat kejadian (Tabel 13 naskah)

Sebelumnya ketiga jenis kejahatan selalu diusulkan ke Samapta ("tingkatkan patroli"). Kini,
untuk tiap kelurahan usulan, sistem melihat jenis tempat kejadian terbanyak pada bulan-bulan
dasar peringkat dan memakai baris yang sesuai di `config/recommendation/function-rules.yaml`
(`place_rules`, PROPOSED):

| Tempat | Alternatif | Fungsi tercatat | Pelaksana |
|---|---|---|---|
| Rumah tinggal | Siskamling dan imbauan kunci ganda melalui RT/RW | BINMAS | Bhabinkamtibmas |
| Kos, kontrakan, asrama | Koordinasi pengamanan parkir penghuni dengan pengelola | BINMAS | Binmas, Polsek |
| Jalan dan perparkiran | Penguatan kewaspadaan dan pengamanan parkir | SAMAPTA | Samapta, Polsek |
| Niaga dan perkantoran | Koordinasi pengamanan dengan pengelola gedung dan pertokoan | BINMAS | Binmas, Polsek |

Draf menyebut jenis ancaman, rentang jam dengan jumlah laporan pendukungnya, tempat terbanyak,
pelaksana, dan dasar datanya. Tanpa tempat yang tercatat, dipakai aturan per jenis ancaman —
sistem tidak mengarang tempat. Contoh pada data nyata (Januari 2026): Cipete Utara, pencurian
kendaraan, 04.00–08.00 WIB (18 dari 24 laporan berjam), rumah tinggal (35 dari 51 laporan),
pelaksana Bhabinkamtibmas — sejalan dengan contoh draf pada naskah.

Draf tetap disusun **aturan dan templat, bukan model bahasa**. Naskah menyebutnya "AI
menyusun draf"; yang benar-benar AI di aplikasi adalah peringkatnya (model gradient boosting).
Ini perlu ditulis apa adanya di naskah.

## Butir 7 — Mutu Data (Modul 1, naskah 4.1 dan Tabel 22)

Layar **Mutu Data** (`/ops/pembakuan`, kembali ke menu — naskah menyebutnya menu tersendiri;
membalik sebagian keputusan menu ringkas 12 November 2026):

- **Kelengkapan** kelurahan, jam, koordinat, objek sasaran, tempat kejadian — indikator
  Tabel 25 naskah.
- **Isian yang ditandai**: jam kosong, objek kosong, tempat kosong, label curanmor dengan
  objek bukan kendaraan bermotor, tanggal laporan mendahului tanggal kejadian. Penandaan
  memakai **aturan tertulis, bukan model** — dinyatakan pada `basis`. Yang ditandai tidak
  diubah otomatis.
- **Pencocokan antarkanal**: laporan warga yang sudah diverifikasi disandingkan dengan
  kejadian resmi di wilayah yang sama dalam ±3 hari. Sistem mengusulkan; petugas memutuskan
  cocok atau tidak, **alasan wajib**. Kolom baru pada `citizen_reports` (0027).
- **Hitungan terpisah**: kejadian resmi; laporan warga tertaut (tidak menambah hitungan —
  satu peristiwa terhitung sekali); kejadian tambahan terverifikasi; menunggu pencocokan;
  menunggu pemeriksaan.
- **Alasan wajib** juga pada keputusan dugaan laporan ganda.

### Yang berbeda dari naskah — perlu keputusan atau penyesuaian naskah

1. **Siapa yang mencocokkan.** Naskah: analis. Aplikasi: pemegang `crime:triage`, yaitu
   Administrator (pengelola data). Memberi hak ini kepada Staf Intelkam atau operator Polsek
   adalah keputusan kewenangan — REQUIRES USER APPROVAL.
2. **"Satu nomor kejadian".** Laporan warga ditautkan ke kode kejadian resmi; tidak dibuat
   nomor kejadian baru untuk kejadian tambahan.
3. **Peta** belum menggambar kejadian tambahan terverifikasi; hitungannya baru ada di Mutu Data.
4. Pencocokan belum memakai ciri objek atau uraian (naskah menyebut keduanya) — hanya wilayah
   dan waktu, yang dapat diperiksa tanpa membaca teks bebas.
5. Jendela ±3 hari berstatus PROPOSED.

## Belum dikerjakan

**Butir 8 — persetujuan Humas** atas informasi publik. Menunggu satu keputusan: siapa yang
menyetujui (peran Humas baru, atau tetap Pimpinan) dan apa saja yang wajib disetujui.

## Verifikasi

- API: 792 lulus pada basis data berisi data contoh; migrasi 0027 naik-turun.
- Web: `tsc`, `biome`, `vitest` 430 lulus, `next build`.
