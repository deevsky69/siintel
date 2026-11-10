# 178 — SIGAP WARGA: rupa baru dari mockup pemilik proyek (10 November 2026)

> **Sumber:** `SIGAP-main.zip` (kanvas desain "SIGAP WARGA Redesign": `Main`, `Peta`, `Survey`,
> `Lacak`, `Lapor` .dc.html; `sigap-login-petugas.html`; `sigap-peta.html`, dua varian 3D).
> Diterima lewat tautan ttl.space 10 November 2026. Berkasnya tidak dimasukkan ke repo.

## Bahasa rupa yang diambil

| Unsur | Mockup | Penerapan |
|---|---|---|
| Warna | navy `#000B47`, navy2 `#0E1A5E`, emas `#C1801E`/`#DF9A33`, merah `#B91C1C`, kanvas `#F8F8F8`, garis `#E2E6EC`/`#D5DBE3`/`#9AA6B8`, tinta `#1A2147`, redup `#687693` | token `.warga` di `globals.css` (`--warga-navy`, `--warga-gold`, dst.); risk-* untuk teks lencana, `LEVEL_FILL` untuk isian peta (`#BFD7EA`/`#F2B45A`/`#EA580C`) |
| Huruf | Inter badan, Manrope 700–800 judul | `--font-display` diganti Manrope (next/font, tanpa internet); Barlow Condensed tidak dipakai lagi |
| Bentuk | sudut persegi, bayangan 1px (`box-shadow: 0 0 0 1px #9AA6B8`), garis emas ganda di kepala, garis emas 3px di atas kartu | `.warga-card`, `.warga-card-raised`, `.warga-card-gold`, `.warga-masthead` |
| Menu | garis emas tipis; saat disentuh/aktif bingkai emas "digambar" dari dua sudut | `.warga-nav-link::before/::after` |
| Tombol | navy penuh (utama), emas (kedua), merah (darurat), bingkai navy (ghost) | `.warga-btn-primary/-gold/-danger/-ghost/-white-outline/-danger-outline` |
| Isian | bingkai 1,5px, tinggi 48–52px; pada Masuk garis emas mengisi dari kiri saat fokus | `.warga-field`, `.warga-inp::after` |

## Per halaman

- **Kerangka**: strip navy (satuan + "Masuk petugas →"), masthead putih (lambang, nama dua
  baris, menu, tombol Lapor/Darurat), kaki navy dua baris. Tab bawah ponsel dipertahankan.
  `main` tidak lagi berpembungkus: tiap halaman memakai `.warga-wrap` (1280px) atau
  `.warga-bleed` (selebar layar).
- **Beranda** (`MapCanvas` + `page.tsx`): hero navy — pil periode, judul, kotak cari (GET
  `/peta?q=`), tiga angka kecamatan per tingkat; kartu putih peta dengan chip saring dan
  legenda; strip Imbauan Polres menumpang di tepi hero; empat kartu layanan; daftar kelurahan
  rawan tinggi bernomor + kartu navy Survey (sorotan kelurahan yang diulas). "Ulasan terbaru"
  lintas kelurahan pada mockup tidak ada API-nya; dipakai sorotan kelurahan (yang ada).
- **Peta**: panggung tiga kolom di atas kanvas abu bergaris putih — panel kiri (cari, chip
  saring lewat `?tingkat=`, jejak, daftar kecamatan/kelurahan), peta tengah, kartu rincian
  kanan (`<details>` dapat dilipat; kejadian per jenis, batang bulanan, kelurahan rawan,
  Babinkamtibmas, tombol "Tandai rasa aman"/"Lapor di wilayah ini"). Peta jalan skematis,
  Street View, dan 3D pada mockup tidak dibangun (lihat bawah).
- **Survey**: spanduk merah, kartu pilih kelurahan, kartu navy nilai rata-rata, ulasan yang
  tayang (garis emas kiri), formulir lima kotak bintang, kelurahan yang sudah diulas (grid),
  "Perlindungan data Anda" 01/02/03.
- **Lacak**: hero navy, kartu menumpang dengan dua tab, hasil lacak berupa linimasa bernomor
  (navy; tahap berikutnya abu), cek kendaraan dengan pilihan plat/rangka, hasil hijau/merah.
- **Lapor**: spanduk merah, tiga fieldset bernomor (jenis sebagai kartu pilihan, waktu &
  lokasi, kronologi + lampiran), pernyataan kebenaran (centang, tidak dikirim ke API), hasil
  berupa **nomor tiket**.
- **Masuk petugas** (`/ops/masuk`): dibungkus `.warga.masuk` — hero navy dengan sapuan emas
  CSS (pengganti shader WebGL mockup), lambang berhalo, kartu bergaris emas, tombol tersapu
  emas, tombol lihat sandi, dua tautan warga.

## Yang SENGAJA tidak dibangun (butuh keputusan pemilik proyek)

1. **Blok "4 Kontak pelapor"** (nama lengkap, HP/WhatsApp) pada Lapor — bertentangan dengan
   U-13 dan `docs/14` §3 (laporan tanpa identitas); test `publik.test.tsx` menjaga agar nama
   isian tidak memuat nama/telepon. Perlu keputusan privasi bila ingin diadakan.
2. **Nomor LP + PIN sebagai hasil Lapor** — LP lahir dari pencatatan petugas di Berkas
   Perkara; laporan web memberi nomor tiket. Menyatukannya mengubah alur SPKT.
3. **Peta 3D** (`sigap-peta-3d*.html`: maplibre dengan tile luar; three.js) dan **Street View**
   (iframe Google) — sumber tile produksi masih terbuka (U-15) dan menuntut akses internet
   saat paparan.
4. **Dropdown bertingkat buatan** (listbox) pada Survey/Lapor — dipakai `<select>` asli
   bergaya; perilakunya sama dan dapat diakses pembaca layar.

## Verifikasi

`tsc --noEmit`, `biome check`, `vitest run` (421), `next build` — lulus. Tanpa tangkapan layar
(Chromium headless tidak tersedia di mesin ini); verifikasi rupa dilakukan lewat kode dan
test kontrak (`publik.test.tsx`, `map-canvas.test.tsx`).
