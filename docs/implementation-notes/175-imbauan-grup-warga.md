# 175 — Imbauan bulanan ke grup WhatsApp warga (4 November 2026)

> **Revisi 6 November 2026 (3A):** pengiriman **menunggu persetujuan Pimpinan** per bulan
> (`advisory_approvals`, migrasi 0022). Butir 2 di bawah tidak berlaku lagi; lihat catatan 176.

Pertanyaan pemilik proyek: bila bot WhatsApp (WAHA) dimasukkan ke grup, bisakah ia otomatis
mengirim "isi rekomendasi satu bulan ke depan"? Keputusan pemilik proyek:

1. anggota grup: perwakilan RT/RW **dan** Babinkamtibmas;
2. **otomatis penuh**, tanpa persetujuan — bahan rekomendasi dianggap baik untuk warga sebagai
   imbauan kehati-hatian (contoh: pencurian pukul 11 → imbauan kunci ganda, jangan sembarangan
   meletakkan motor);
3. jadwal awal bulan, dan bisa dipicu dengan `/rekomendasi` (bulan depan).

## Rekonsiliasi dengan keputusan 2 November 2026

Batas informasi publik (warga hanya angka historis dan tingkat kerawanan kasar) tetap
berlaku. Yang dikirim ke grup adalah **imbauan warga**: jenis ancaman, jam rawan, jumlah
kejadian historis pada bulan yang sama tahun-tahun sebelumnya, dan tips. **Tidak** ikut: skor
risiko, confidence, fungsi/taktik kepolisian, titik kejadian. Versi lengkap (perkiraan singkat
`/patrol-plan/outlook`, .docx) tetap di `/ops`. Berbeda dari buletin mingguan yang disetujui
Pimpinan, imbauan ini terkirim tanpa persetujuan — dicatat sebagai keputusan pemilik proyek di
`docs/01` §19.

## Sumber dan bentuk

- `services/citizen_advisory.py`: `build_advisory(session, year, month, kelurahan)` memakai
  `outlook.build_outlook` (pola bulan yang sama, PROPOSED), mengambil slot yang jatuh pada
  kelurahan itu; bila kelurahan tidak menonjol untuk suatu jenis, dipakai jam puncak se-Polres
  dan **dikatakan** begitu. Maksimal empat jenis. `render_text` menyusun pesan WhatsApp.
- `config/recommendation/citizen-advice.yaml` (**PROPOSED — teks belum ditinjau pemilik
  proyek**): pembuka/penutup, label jenis untuk warga, tips per jenis (maks. tiga baris).
- Bulan: imbauan terjadwal = bulan berjalan menurut waktu sebenarnya; `/rekomendasi` = bulan
  berikutnya. Basis historis tetap tunduk pada batas tampilan data (sampai Desember 2025).

## Pendaftaran grup

Bot tidak tahu grup mana milik kelurahan mana. Dari dalam grup, Babin (atau siapa pun) mengetik
`/daftar <nama kelurahan>`; bot memanggil `POST /messaging/groups` yang menyimpan chat id grup
(`…@g.us`) pada baris Babinkamtibmas kelurahan itu (kolom baru `whatsapp_group_chat_id`,
migrasi 0018). Kelurahan tanpa kontak Babin ditolak dengan petunjuk mengisinya di
`/ops/babin`. Satu grup hanya untuk satu kelurahan. Chat id juga tampil dan dapat diubah di
panel samping Babinkamtibmas; lencana "Imbauan YYYY-MM" menunjukkan bulan terakhir terkirim.

## Pengiriman

- Terjadwal: `GET /messaging/advisories/pending` mengembalikan grup terdaftar yang
  `advisory_sent_month` ≠ bulan berjalan; bot (`deliver_advisories`, dalam loop buletin tiap
  ±2 menit) mengirim lewat WAHA lalu `POST /messaging/advisories/sent`. "Awal bulan" berarti
  pemeriksaan pertama setelah bulan berganti; bila gagal, dicatat (audit
  `SEND_CITIZEN_ADVISORY`, hasil FAILED) dan dicoba lagi pada putaran berikutnya.
- Permintaan: di grup `/rekomendasi` (kelurahan dari pendaftaran) atau `/rekomendasi <kelurahan>`;
  di pesan pribadi `/rekomendasi <kelurahan>`. Di grup bot melayani `/daftar`,
  `/rekomendasi`, `/babin` (kontak Babin kelurahan grup), dan `/mulai`/`/bantuan`/perintah
  tak dikenal → pesan pengenalan (fitur, tautan sigap.awansurya.com, kontak Babin; permintaan
  pemilik proyek 4 November 2026 sore). Pesan biasa tanpa garis miring diabaikan supaya alur
  laporan tidak berjalan di hadapan seluruh anggota grup. Kelurahan grup dicari lewat
  `GET /messaging/groups` (bukan antrean imbauan, yang kosong setelah bulan itu terkirim).
- Hanya WAHA yang dapat mengirim ke grup; pengirim grup selalu WAHA bila dikonfigurasi.

## Uji

API: `test_citizen_group_registration_and_monthly_advisory_for_bot` (pendaftaran, 400/404,
teks tanpa istilah kepolisian, antrean bulan berjalan sekali kirim) — 6 test berkas Babin lulus
dengan basis data pengembangan (migrasi 0018 diterapkan). Bot: 45 test (perintah grup, perintah
pribadi, pengiriman sekali per bulan, WAHA hanya menjawab perintah di grup). Web: tsc, 418 test.

## Belum

- Teks imbauan di `citizen-advice.yaml` menunggu tinjauan pemilik proyek (PROPOSED).
- Belum diuji dengan grup WhatsApp sungguhan; perlu nomor cadangan dimasukkan ke grup lalu
  `/daftar <kelurahan>` di dalamnya.
- Risiko pemblokiran: pesan terjadwal ke grup adalah pesan yang diinisiasi bot (panduan WAHA);
  diterima untuk peragaan.
