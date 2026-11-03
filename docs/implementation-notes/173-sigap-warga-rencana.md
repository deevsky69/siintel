# 173 — SIGAP WARGA: rencana perombakan sisi masyarakat (2 November 2026)

Keputusan pemilik proyek tercatat di docs/01 §19.2 (baris "SIGAP WARGA"). Catatan ini
menuliskan tahapannya supaya setiap tahap satu perubahan koheren (CLAUDE.md §7).

## Dua wajah, satu domain

```text
sigap.awansurya.com/           SIGAP WARGA — publik, tanpa akun, mode terang
sigap.awansurya.com/ops/...    SIGAP — Pimpinan/Administrator/Polsek/Fungsi (yang ada sekarang)
```

Jalur `/ops` dipilih atas subdomain karena: satu sertifikat dan satu blok nginx (mesin depan
tidak dapat dihubungi dari sini), satu deploy, dan middleware yang sudah memisahkan publik
dari aplikasi tinggal dipindahkan awalannya. Yang harus dijaga: cookie sesi dibatasi
`Path=/ops`, tautan internal diprefiks, Android petugas menunjuk `/api/v1` yang tidak berubah.

## Tahap 1 — dasbor warga (data sudah ada)

- Halaman muka baru: imbauan berlaku, peta wilayah (kecamatan → kelurahan) dengan jumlah
  3C historis per bulan dan tingkat kerawanan kasar (rendah/sedang/tinggi dari kuantil
  kejadian historis — bukan dari prediksi), Lapor, Darurat, Survey Rasa Aman.
- API publik baru `GET /public/areas/summary` — agregat historis per kelurahan (12 bulan
  terakhir sampai batas tampilan), tanpa koordinat kejadian.
- Survey Rasa Aman: tabel `area_reviews` (kelurahan, nilai 1–5, komentar ≤300, status
  PENDING/PUBLISHED/REJECTED, pembatas laju per alamat), moderasi di `/ops/survey`
  (`review:moderate` — Administrator; Binmas lewat peran Fungsi menunggu keputusan RBAC),
  nilai rata-rata dihitung dari yang tayang.

## Tahap 2 — berkas perkara (data dummy berlabel)

- Entitas `case_files`: nomor LP, jenis 3C, tahap (SP2HP: Lidik/Sidik/P21/SP3/Selesai),
  plat, nomor rangka/mesin, kelurahan, kontak pelapor (hash), `is_dummy`.
- `GET /public/cases/track` (nomor LP + 4 digit terakhir telepon pelapor) → tahap + riwayat.
- `GET /public/vehicles/check` (plat atau nomor rangka) → hanya "tercatat/tidak" + saran.
- Operator (`case_file:write`, Administrator/Reskrim) mengelola di `/ops/perkara`.
- Label **DUMMY** tampil di setiap hasil selama datanya sintetis.

## Tahap 3 — kontak Babinkamtibmas dan buletin kelurahan

- Entitas `babinkamtibmas` (kelurahan, polsek, nama, nomor dinas, tautan grup, `is_dummy`),
  CRUD di `/ops/babin`, ditampilkan di bot (menu "Kontak Babin") dan dasbor warga.
- Buletin mingguan per kelurahan: disusun sistem (kejadian + rekomendasi minggu lalu),
  **disetujui** di `/ops` sebelum terkirim; bot Telegram mengirim ke grup kelurahan,
  WhatsApp perorangan ke nomor Babin (API resmi tidak menjangkau grup).
- Menu bot: tautan dasbor warga.

## Tema

Dasbor warga memakai tema sendiri, terang sebagai bawaan; arah visual ditentukan pemilik
proyek dari refero.design. Komponen sisi polisi tidak dipakai ulang di sisi warga.

## Tahap 1 — SELESAI 2 November 2026

- API: `routers/public_areas.py` (`GET /public/areas/summary`), `routers/reviews.py`
  (kirim/baca ulasan publik; antrean dan moderasi `review:moderate`), tabel `area_reviews`
  (0015), kelompok `REVIEW` di `/notifications`; tautan antrean berawalan `/ops`.
- Web: sisi kepolisian dipindah ke `app/ops/(app)` + `app/ops/masuk`; middleware: akar
  terbuka, `/ops` menuntut sesi; `safeNextPath` hanya menerima jalur `/ops`. Sisi warga:
  `app/(publik)/layout.tsx` (tema `.warga` terang-hangat, navigasi atas/bawah),
  beranda `/` (peta kecamatan + imbauan + sorotan survey + wilayah tinggi), `/peta`
  (kecamatan → kelurahan, panel angka), `/survey` (nilai, ulasan tayang, formulir anonim),
  `/lapor` disesuaikan. Moderasi di `/ops/survey`.
- Tema: arah B (peta di depan) dengan rupa A (gading hangat, biru tua, aksen kuning),
  Inter untuk semua teks; tidak memakai komponen/huruf teknis sisi /ops.
- Pemeriksaan produksi: beranda warga 200, `/ops` dialihkan, ringkasan publik 200,
  Server Action diuji pada `/ops/masuk`.

## Tahap 2 — SELESAI 2 November 2026

- API: `models/case_file.py` (`case_files`, `case_file_stages`, 0016; PIN di-hash bersama
  nomor LP; `is_dummy` + `dummy_pin`), `routers/public_cases.py` (lacak LP+PIN jawaban
  seragam 404; cek kendaraan tercatat/tidak), `routers/case_files.py` (daftar, catat dengan
  PIN sekali tampil, pindah tahap; cakupan Polsek), permission `case_file:read/write`
  (Pimpinan baca; Polsek wilayah; Administrator semua), `seeding/case_files_dummy.py` +
  perintah `predpol seed-case-files-dummy` + `scripts/isi-perkara-dummy-produksi.sh`.
- Web warga: `/lacak` (tab Lacak laporan / Cek kendaraan), tautan di beranda dan navigasi.
- Web petugas: `/ops/perkara` (saring, pindah tahap, catat perkara baru).
- Test: `test_api_case_files.py` (5), web 412; label DUMMY tampil di sisi warga dan petugas.

## Tahap 3 — SELESAI 2 November 2026

- API: `babinkamtibmas` + `bulletins` (0017), `routers/babin.py` (publik: nomor dinas saja;
  kelola: Administrator), `routers/bulletins.py` (susun DRAFT per kelurahan dari
  `services/bulletin.py`; setujui = Pimpinan `bulletin:approve`; bot: pending/sent),
  seeder `seed-babin-dummy` (ikut `scripts/isi-perkara-dummy-produksi.sh`).
- Bot: `/babin` (kecamatan → kelurahan → kontak), `/dasbor` (tautan SIGAP WARGA), thread
  buletin: APPROVED → grup Telegram (chat id) dan/atau WhatsApp Babin → `sent` per kanal.
- Web: `/ops/babin` (kontak + tujuan buletin), `/ops/buletin` (susun, setujui, status kirim);
  warga: kontak Babin di panel kelurahan `/peta`.
- Keputusan tercatat: grup WhatsApp tidak terjangkau API resmi → Telegram + WA perorangan.

## Rupa baru sisi warga — 3 November 2026

Permintaan pemilik proyek: "transisi yang mantap" dan "logo Polri bersama masyarakat".

- **Lambang Polri** resmi (berkas domain publik dari Wikimedia Commons, `Insignia of the
  Indonesian National Police` / `Lambang Polri.png`) dikecilkan ke `apps/web/public/brand/`
  (96/256/512 px). Tampil di kepala halaman, hero, kaki halaman, dan halaman masuk petugas.
- **Tanda tangan rupa**: `BersamaRing` — lambang di tengah, dua lingkaran titik "warga"
  mengelilinginya perlahan (48 s dan 32 s), di bawah tulisan "Polri bersama masyarakat".
- **Gerak** (semua dimatikan pada `prefers-reduced-motion`): isi halaman naik bergiliran pada
  tiap perpindahan rute (`(publik)/template.tsx` + `.warga-enter`), bagian di bawah lipatan
  muncul saat digulir (`components/warga/reveal.tsx`, tetap tampil tanpa JavaScript setelah
  2,5 s), poligon peta mengembang berurutan saat dimuat dan terang saat disentuh
  (`.warga-poly`), pil navigasi aktif dan garis kuning tab bawah (`components/warga/nav.tsx`).
- **Tipografi**: judul sisi warga memakai Plus Jakarta Sans (`--font-display`, dibundel lewat
  next/font); badan tetap Inter. Hero satu-satunya bidang biru malam di sisi warga, tombol
  utama kuning Polri.
- Tidak ada perubahan API, data, maupun teks yang diuji; 414 test web tetap lulus.

## Beranda dirombak — kanvas peta (3 November 2026, sore)

Permintaan pemilik proyek: "rombak total" beranda dengan referensi dasbor keamanan publik dari
refero.design, dan "elemen yang ada transisinya".

- **Referensi** (Refero, MCP `refero`): Nextdoor *Alerts* — peta memenuhi bidang sebagai meja
  kerja, panel putih mengambang berisi chip saring dan kartu peringatan, keterangan di sudut
  peta (`refero.design/pages/685c5750-10a0-4c5f-9a84-a3a42ca4e414`); Google Maps *nearby
  fires* (iOS) — peta di atas, lembar informasi naik dari bawah, untuk tata letak ponsel; kartu
  peringatan cuaca Apple — satu garis tingkat, judul singkat, isi di bawahnya.
- **Susunan baru** (`components/warga/map-canvas.tsx`, `(publik)/page.tsx`): kanvas kertas
  bertitik (`.warga-canvas`) memuat peta kecamatan di kanan dan panel `.warga-float` di kiri
  (ponsel: peta di atas, panel menjadi lembar dengan pegangan). Panel: lambang dengan cincin
  warga (varian terang), judul, rentang bulan, **chip saring** Semua/Tinggi/Sedang/Rendah
  dengan jumlah kecamatan, imbauan berlaku (maks. 3), tombol Lapor dan 110. Di bawahnya empat
  ubin jalan pintas (Lacak, Cek kendaraan, Survey, Peta kelurahan), lalu Survey Rasa Aman dan
  wilayah tinggi. Hero biru malam dihapus; sisi warga kini seluruhnya terang.
- **Transisi**: panel meluncur masuk (dari kiri di layar lebar, naik dari bawah di ponsel);
  chip yang ditekan berwarna penuh dan **meredupkan poligon tingkat lain** (`emphasis` pada
  `PublicMap`, transisi `fill-opacity`); wilayah yang disentuh/difokus memunculkan kartu
  kecil nama + tingkat + jumlah (`tip` pada `PublicMap`, prop boolean — komponen klien tidak
  boleh menerima fungsi); kartu imbauan naik bergiliran setelah panel tiba; ubin terangkat
  dan panahnya bergeser; baris wilayah bergeser saat disentuh. Yang lama tetap: transisi
  rute, reveal saat gulir, poligon menggambar diri, orbit cincin. Semua mati pada
  `prefers-reduced-motion`.
- **Lebar** sisi warga 5xl → 6xl supaya kanvas lapang. Tidak ada perubahan API/data; isi yang
  tampil sama seperti keputusan 2 November (tingkat kasar, imbauan terbit, survey).
- Test: `map-canvas.test.tsx` (chip meredupkan dan melepas, kartu kecil saat fokus, keadaan
  tanpa ringkasan); `publik.test.tsx` tetap; 417 test web lulus; `next build` berhasil.
