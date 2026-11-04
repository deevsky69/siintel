# 174 — Tabel CRUD di /ops: Babinkamtibmas dan Laporan, perbaikan navigasi (4 November 2026)

Permintaan pemilik proyek setelah uji WAHA dari ponsel: "/ops banyak error — klik peta malah
pindah ke SIGAP WARGA; Babinkamtibmas dan laporan/LP minimal CRUD/matriks; jangan terlalu
banyak teks". Rujukan desain diambil dari Refero: tabel kontak **Attio** dan **Cake Equity**
(judul + hitungan, toolbar pencarian dengan tombol tambah di kanan, baris padat berlencana,
aksi per baris di kolom kanan, formulir di side sheet) dan tabel tiket **Intercom** (mode gelap).

## Navigasi /ops

Sejak 2 November 2026 akar situs adalah peta warga, aplikasi kepolisian di `/ops`. Enam tautan
tingkat wilayah di beranda petugas (`map-hero.tsx`, `map-canvas.tsx`) masih `"/?tingkat=…"`
sehingga klik wilayah keluar dari `/ops`. Kini `"/ops?tingkat=…"`; tes penjaga di
`map.test.tsx` menolak kembalinya tautan ke akar. Log web/API enam jam terakhir tidak memuat
5xx — "banyak error" yang dilaporkan adalah navigasi ini.

## Pola bersama

- `globals.css`: `.data-table` (kepala lengket, baris rapat, sorotan hover, `.num`, `.act`),
  `.btn-sm`, `.btn-sm-primary`, `.btn-sm-danger`, `.field`, `.field-label`.
- `components/drawer.tsx`: side sheet klien (latar klik-tutup, Escape, `role="dialog"`).
  Terdaftar di `CALLBACK_ALLOWED` tes batas server/klien karena hanya komponen klien yang
  mengimpornya.
- `lib/community-format.ts`: bagian murni (label, tipe, `formatMoment`, `areaOf`) dipisah
  dari `lib/community.ts` yang memuat `./api` → `next/headers`; `next build` menolak komponen
  klien yang menariknya (lihat memori "next build sebelum deploy web").

## Babinkamtibmas (`/ops/babin`)

Satu baris per kelurahan master lokasi (yang belum terisi tetap tampak sebagai kekurangan).
Kolom: Kelurahan · Kecamatan · Polsek · Babinkamtibmas (+lencana Dummy) · Nomor dinas ·
Kanal buletin (Telegram / WA Babin / Grup WA, dicoret bila belum) · Aksi (Ubah/Isi).
Toolbar: pencarian klien, centang "Belum terisi", tombol **+ Tambah** (pilih kelurahan yang
belum terisi). Isian di panel samping dengan label singkat; "tampil ke warga" dan "tujuan
buletin" dinyatakan pada label, bukan paragraf. **Hapus** dua langkah di kaki panel.

API baru: `DELETE /babin/{kelurahan}` (`babin:manage`, 204, 404 bila tidak ada, audit
`DELETE_BABIN`). Test `test_babin_contact_can_be_deleted_by_manager_only`.

## Laporan Masyarakat (`/ops/masyarakat`)

Ubin angka per tahapan (sekaligus penyaring, tautan URL) + total; baris chip kategori;
satu baris "Terbanyak" dan "Belum terpetakan". Tabel: Kode · Masuk · Kategori (+Lampiran) ·
Wilayah (+"Titik dibagikan pelapor") · Urgensi · Verifikasi · Tahapan · Aksi (**Rincian**
membuka panel samping berisi uraian, lokasi tertulis, waktu kejadian, penilaian, lampiran;
pilihan **Ubah tahapan**). Tiga pernyataan wajib tetap ada dan dipadatkan: notice "belum
memengaruhi risk score", catatan kaki "diisi petugas saat triase; tidak ada penilaian otomatis;
deteksi duplikasi/spam belum dibangun", dan `Basis`. Seluruh 14 test `community.test.tsx`
tetap lulus tanpa melonggarkan asersi; satu penyesuaian: "Tidak ada kategori laporan." kini
baris kecil pada panel Ringkasan saat kosong.

Hapus laporan masyarakat **tidak** ditambahkan: laporan adalah jejak yang harus dapat ditelusuri
(CLAUDE.md §29); bila diperlukan, itu keputusan kebijakan tersendiri.

## Laporan Petugas (`/ops/laporan-petugas`)

Tabel memakai `.data-table`; dua paragraf catatan dipadatkan menjadi satu. Tidak ada perubahan
perilaku.

## Kanal perpesanan (hari yang sama)

Twilio dihapus dari `.env.production` atas keputusan pemilik proyek; kabar WHATSAPP kini dikirim
bot lewat WAHA (`waha-kabar`). Lihat catatan 171.

## Uji

Web: biome, `tsc`, 418 test vitest, `next build` lulus. API: ruff, 5 test babin/buletin lulus
dengan basis data pengembangan.
