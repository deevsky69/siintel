# 182 — SIGAP BERSAMA: langganan imbauan, panduan pengamanan, survei triwulanan (17 November 2026)

Penyesuaian ke naskah Taskap 4.7 (butir 10 audit naskah–aplikasi; butir 9, penamaan, ada pada
commit tersendiri). Keputusan pemilik proyek 17 November 2026.

## Yang berubah

| Naskah 4.7 | Sebelum | Sesudah |
|---|---|---|
| b. Pemberitahuan wilayah bagi warga yang memilih | Hanya GRUP WhatsApp (`/daftar`) | Warga berlangganan dari percakapan pribadi: `/langganan <kelurahan>`, `/berhenti` |
| f. Panduan pengamanan kos, parkir, gedung, RT/RW | Tidak ada; tips hanya per jenis kejahatan | Halaman `/panduan`, `GET /public/guides`, perintah bot `/panduan` |
| h. Survei rasa aman triwulanan dengan cakupan responden | Nilai berjalan terus, tanpa periode | Hasil per triwulan: responden, rata-rata, kelurahan terwakili |

## Langganan imbauan — data pribadi

Pengenal percakapan WhatsApp memuat nomor telepon. Rancangannya mengikuti CLAUDE.md §16:

| | |
|---|---|
| Tujuan | Mengirim imbauan bulanan kelurahan yang dipilih warga itu sendiri |
| Isian minimum | Kanal, pengenal percakapan, kelurahan. Tanpa nama, tanpa alamat |
| Persetujuan | Warga mengetik perintahnya sendiri; balasan bot menyebut apa yang disimpan |
| Akses | Hanya bot (kunci `MESSAGING_API_KEY`). Tidak ada layar yang menampilkan pengenalnya; `/ops/buletin` hanya memuat jumlah pelanggan |
| Berhenti | `/berhenti` MENGHAPUS barisnya |
| Audit | `SUBSCRIBE_/UNSUBSCRIBE_AREA_ADVISORY`, `SEND_SUBSCRIBER_ADVISORY` — tanpa pengenal percakapan |

Tabel `area_subscriptions` (0025). Satu percakapan satu kelurahan; berlangganan lagi berarti
pindah. Pelanggan baru menerima imbauan bulan berjalan pada putaran bot berikutnya, lalu sekali
tiap awal bulan. Kegagalan kirim ditandai dan tidak diulang sampai bulan berikutnya.

**REQUIRES HUMAN / POLICY APPROVAL** sebelum dibuka untuk umum:

1. masa simpan langganan yang tidak aktif (saat ini tanpa batas sampai warga berhenti);
2. kanal resmi pengirimnya — WAHA hanya untuk peragaan (keputusan 3 November 2026);
3. apakah teks imbauan perlu disetujui Humas sebelum terkirim (naskah menyebut Humas; aplikasi
   mengirim otomatis sejak 10 November 2026 — butir audit 8, belum diputuskan).

## Panduan pengamanan

- Teks di `config/recommendation/security-guides.yaml`, status **PROPOSED**: rancangan awal,
  belum ditinjau Binmas/Humas. Empat panduan mengikuti empat jenis tempat pada Tabel 13 naskah.
- "Berdasarkan pola kejadian" diisi dari data, bukan kalimat tempelan: tiap panduan membawa
  agregat 3C 12 bulan terakhir pada kategori tempat kejadian yang dipetakan di berkas itu —
  jumlah, porsi, modus terbanyak, blok jam terbanyak. Se-Polres, tanpa alamat atau tanggal.
- Blok jam mengikuti blok 3 jam aplikasi (keputusan 30 September 2026); naskah memakai 4 jam —
  butir audit 4, belum diputuskan.

## Survei triwulanan

- Warga tetap dapat mengisi kapan saja; yang berubah adalah PENYAJIAN: empat triwulan kalender
  terakhir, masing-masing dengan responden (ulasan tayang), nilai rata-rata, dan kelurahan
  terwakili dari seluruh kelurahan. Moderator juga melihat jumlah ulasan masuk dan rincian per
  kecamatan.
- Pengisian sukarela, jadi ini bukan sampel acak penduduk — dinyatakan pada `basis` dan tampil
  di kedua layar.
- **Perubahan perilaku:** `area_reviews.submitted_at` kini memakai waktu sebenarnya
  (`clock.citizen_now`), bukan waktu acuan peragaan. Dengan waktu acuan yang beku, seluruh
  ulasan jatuh pada satu triwulan dan hasil triwulanan tidak bermakna. Ulasan yang sudah
  tersimpan tidak diubah.

## Yang TIDAK dikerjakan

- Lacak barang hilang selain berkas perkara 3C, cek kendaraan dengan nomor laporan, dan
  persetujuan Humas — bagian 4.7 lain yang tidak termasuk butir 10.
- Tab bawah ponsel tetap lima; Panduan ada di navigasi atas, kartu beranda, dan kaki halaman.

## Verifikasi

- API: `uv run pytest` 787 lulus pada basis data berisi data contoh (setara CI); migrasi 0025
  naik-turun.
- Bot: 48 lulus (langganan, berhenti, panduan, pengiriman per kanal sekali per bulan).
- Web: `tsc`, `biome`, `vitest` 426 lulus, `next build` berhasil.
