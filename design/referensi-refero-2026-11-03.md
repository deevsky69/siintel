# Referensi Refero — tiga layar pilihan pemilik proyek (3 November 2026)

Tiga layar dari refero.design yang dipilih pemilik proyek dengan kata kunci pencarian
*"website to report base on maps with simple and modern layout"* (dua layar) dan satu layar
dari jalur "layar serupa". Isi tiap bagian diambil dari metadata Refero (deskripsi, tata
letak, fungsi, elemen, huruf, warna), lalu ditutup catatan singkat: apa yang dapat dipindahkan
ke SIGAP WARGA dan apa yang tidak.

Status: **REFERENSI** — bukan keputusan desain. Keputusan tercatat di
`docs/implementation-notes/173-sigap-warga-rencana.md`.

---

## 1. Tesla — Find Us (peta penuh dengan saring kategori)

| | |
|---|---|
| Refero | https://refero.design/pages/cdf3f7df-4975-47fb-88f5-633b4b987eeb |
| Situs | Tesla · tesla.com · kategori: Electronic & Devices, Marketplace, Transport |
| Halaman asal | https://www.tesla.com/findus |
| Platform | web (desktop) |
| Pola UX | Searching |
| Elemen UI | Map, Button, Tags & Chips, Navigation Bar, Search Field, Icon, Map Pin |
| Huruf | Roboto, Universal Sans |
| Warna | `#F8F7F7` `#C3C3C3` `#4D4241` `#5B626E` `#837E7E` |
| Gambar | https://images.refero.design/screenshots/tesla.com/desktop/27704fec-fe48-4c5f-8456-dbd8fc8b6b9f_preview.jpg |

**Deskripsi.** Peta interaktif selebar layar, berpusat pada Minnesota–Wisconsin–Dakota. Dasar
peta abu-abu (daratan abu muda, garis putih, label kota redup). Ikon berwarna (merah, abu
gelap, biru, kuning) menandai jenis fasilitas: Stores and Galleries, Service, Body Shops,
Superchargers (beberapa kategori), Self-Serve Demo Drive, Delivery Centers, Destination
Charging. Sudut kiri atas memuat kolom pencarian ("Enter location" dengan ikon kaca pembesar)
dan di bawahnya panel keterangan sekaligus saring: tiap kategori berupa chip putih berisi ikon
dan label huruf kecil, dapat dinyalakan/dimatikan. Kontrol zoom (+/−) di tepi kanan sebagai
kotak putih bergaris. Logo Tesla di kiri atas; navigasi tengah atas: Vehicles, Energy,
Charging, Discover, Shop — teks tipis tanpa pil; kanan atas tiga ikon bulat (bantuan, bahasa,
profil). Palet nyaris monokrom dengan aksen merah dan biru.

**Tata letak.** Peta memenuhi hampir seluruh viewport. Baris navigasi horizontal di atas,
tautan berjarak rata di tengah. Panel kiri atas bertumpuk vertikal: pencarian, lalu
keterangan/saring dalam beberapa baris chip. Zoom bertumpuk vertikal di kanan tengah. Tiga
ikon kecil di kanan atas. UI minimal supaya bidang peta maksimal; semua kontrol pada posisi
tetap.

**Fungsi.** Cari lokasi, zoom, jelajahi jaringan fasilitas, saring tampilan per kategori lewat
chip di keterangan, buka bagian situs lain lewat navigasi atas.

**Catatan untuk SIGAP WARGA.**
- Pola **"keterangan = saring"** (chip kategori yang sekaligus legenda) sudah dipakai di
  beranda warga untuk tingkat Rendah/Sedang/Tinggi. Tesla menaruhnya **di atas peta**, bukan di
  panel samping; ini layak dipertimbangkan untuk halaman `/peta` yang bidangnya lebih luas.
- Navigasi atas berupa teks polos berjarak rata, tanpa tombol berwarna — sejalan dengan
  keputusan "menu bar jangan seperti AI".
- Dasar peta abu-abu redup membuat ikon berwarna menonjol. Padanan di SIGAP WARGA: kanvas
  arang dengan poligon berwarna.
- Yang **tidak** dipindahkan: titik/pin per lokasi. Keputusan pemilik proyek 2 November 2026:
  sisi warga tidak menampilkan titik kejadian, hanya tingkat per wilayah.

---

## 2. Missive — beranda produk (hero sederhana, tangkapan layar produk, bagian bertumpuk)

| | |
|---|---|
| Refero | https://refero.design/pages/8200fc53-f06d-4ed5-89e5-bcc7b268797d |
| Situs | Missive · missiveapp.com · kategori: Business, Collaboration Tools, Communication Tools |
| Halaman asal | https://missiveapp.com/ |
| Platform | web (desktop) |
| Jenis halaman | Product Page & Landing, Home Page |
| Pola UX | Reviews & Rating, Testimonials, Video Player, Product Features, Bento Grid |
| Elemen UI | Cards & Tiles, Carousel, Button, Tags & Chips, Progress Bar, Navigation Bar, Footer, Icon, Logo Wall, Hero Image, Thumbnail, Product Image, Animation |
| Huruf | Tiempos Headline (judul, serif), Inter, Arial |
| Warna | `#1E2023` `#2A6EEB` `#636B73` `#99A3AB` `#F9F9F9` |
| Gambar | https://images.refero.design/screenshots/missiveapp.com/desktop/8d27bfd7-8e89-432e-8385-061b21eafd73_preview.jpg |

**Deskripsi.** Halaman pendarat satu kolom, palet hitam-putih dengan tombol aksi biru terang
(`#0069FF`) dan abu halus (`#F0F0F0`, `#CCCCCC`). Judul serif modern tebal (32–40 px), badan
sans-serif abu gelap (`#555555`, ±16 px). Navigasi atas: logo kiri, tautan Features /
Customers / Pricing / Help dan aksi Log in / Book a demo / Try for free di kanan — tautan teks
polos, satu tombol biru untuk aksi utama. Hero: judul besar, kalimat pendukung, dua tombol
(utama biru, sekunder abu). Di bawahnya tangkapan layar aplikasi dalam bingkai perangkat
(sidebar folder, daftar surel, panel pratinjau). Bagian fitur bergantian: judul serif, paragraf,
ikon atau tangkapan layar kecil (team spaces, status baca, tugas, tag, otomasi). Dinding logo
klien monokrom. Korsel testimoni dengan foto, kutipan, bintang emas 4,8. Footer hitam, teks
putih, enam kolom tautan.

**Tata letak.** Gulir vertikal satu kolom, isi rata tengah, lebar maksimum ±1140 px dengan
padding mendatar ±24 px. Jarak antar bagian ±80–120 px. Bagian fitur: judul dan paragraf rata
kiri di atas, gambar besar di bawah; sebagian dua kolom (teks kiri, gambar kanan atau
sebaliknya). Dinding logo satu baris berjarak rata. Footer grid enam kolom sempit.

**Fungsi.** Mengenalkan produk, mengarahkan ke uji coba atau demo; petunjuk hover pada tombol
dan menu; tangkapan layar menunjukkan kemampuan produk; bukti sosial lewat logo dan testimoni.

**Catatan untuk SIGAP WARGA.**
- Pola yang relevan: **ritme bagian** (satu judul, satu kalimat, satu gambar besar) dan
  **navigasi teks polos dengan satu tombol aksi**. Ritme ini dapat dipakai bila SIGAP WARGA
  kelak butuh halaman "Tentang" atau pengenalan layanan.
- Serif modern untuk judul adalah pilihan khas Missive; SIGAP WARGA sudah memutuskan condensed
  tebal kapital (Barlow Condensed). Tidak diadopsi.
- Dinding logo, testimoni, dan korsel adalah bahasa pemasaran produk; tidak cocok untuk situs
  layanan publik.

---

## 3. Fibery — Workspace Map (peta hubungan antar-entitas dengan panel rincian kanan)

| | |
|---|---|
| Refero | https://refero.design/pages/a593381f-7d7b-4b68-83b3-fb1303fb73c7 |
| Situs | Fibery · fibery.io · kategori: Collaboration Tools, Communication Tools, Productivity, Project Management |
| Halaman asal | https://crowd.fibery.io/fibery/settings/domain#Public_Roadmap/Roadmap_Item/edit |
| Platform | web (desktop, layar aplikasi) |
| Elemen UI | Action Sheet |
| Huruf | San Francisco, UI Sans Serif |
| Warna | `#C13D63` `#222525` `#3281D2` `#9BA4A8` `#44B6A1` |
| Gambar | https://images.refero.design/screenshots/fibery.io/desktop/544343d6-f24d-444c-836f-b672137d9d58_preview.jpg |

**Deskripsi.** Antarmuka "Workspace Map" di latar putih. Kiri: bilah navigasi vertikal abu
muda (`#F9F9F9`) berisi ikon + teks (Account, Upgrade, Search, Inbox, Favorites, My Space,
To-Do List, Getting Started, Customers, Feedback, Research, Product, Public Roadmap, Settings,
People, New Space). Tengah: judul "Workspace Map" (tebal, ±20 px) di atas diagram simpul:
kartu putih bersudut bulat dengan bayangan halus (Product, Public Roadmap, Research, Feedback,
To-Do List, Getting Started), tiap kartu memuat tag berwarna (PRODUCT ungu, COMPONENT biru,
FEATURE turkis, SUBFEATURE biru muda, RELEASE teal, ROADMAP ITEM cyan, OPPORTUNITY jingga,
PERSONA merah, TASK biru, HABIT hijau, DAILY ACTIVITY pink); garis lengkung tipis
menghubungkan simpul. Kanan: panel "Roadmap Item" berisi formulir (Description, Name,
Component), lalu kelompok Workflow, Files, Relations, Lookups, Buttons; pemisah garis abu
muda; label 14 px, isian 16 px. Grid tiga kolom: nav sempit, peta lebar, panel sedang; padding
±16 px di dalam kartu, ±24 px antar bagian.

**Tata letak.** Tiga kolom sejajar: sidebar navigasi (sempit, item bertumpuk dengan ikon),
area peta bebas (simpul tersebar, dihubungkan garis), panel rincian lebar tetap (formulir
vertikal berkelompok). Banyak ruang kosong; perataan rapi.

**Fungsi.** Berpindah bagian lewat sidebar; melihat dan (kemungkinan) menyeret/mengklik simpul
untuk membuka rincian; menyunting atribut item di panel kanan; mengelola berkas, relasi,
lookup, dan tombol khusus.

**Catatan untuk SIGAP WARGA.**
- Pola yang relevan adalah **"peta di tengah, rincian di panel kanan tanpa meninggalkan
  halaman"**. Ini sudah menjadi prinsip beranda petugas (/ops) dan dapat diperkuat di `/peta`
  warga: klik kelurahan → panel rincian (angka per bulan, kontak Babin) muncul di samping,
  bukan halaman baru.
- Tag kecil berwarna per jenis (TASK, FEATURE, …) adalah padanan `LevelBadge` dan label jenis
  kejahatan; pelajaran yang bisa diambil: warna tag konsisten di seluruh layar.
- Sidebar navigasi vertikal cocok untuk aplikasi kerja, **tidak** untuk sisi warga yang hanya
  punya lima tujuan; tetap navigasi atas + tab bawah di ponsel.
- Kartu bersudut bulat dengan bayangan bertentangan dengan rupa gelap-tegas yang sudah
  diputuskan (radius 2 px, tanpa bayangan). Tidak diadopsi.

---

## Ringkasan pola yang dapat dipindahkan

| Pola | Sumber | Tempat di SIGAP WARGA | Status |
|---|---|---|---|
| Keterangan sekaligus saring, ditaruh di atas peta | Tesla | `/peta` | usulan |
| Navigasi teks polos, satu aksi utama | Tesla, Missive | masthead warga | sudah (3 Nov 2026) |
| Dasar peta redup, warna hanya untuk data | Tesla | kanvas beranda | sudah (rupa gelap) |
| Rincian di panel samping tanpa pindah halaman | Fibery | `/peta` (kelurahan) | usulan |
| Tag warna konsisten lintas layar | Fibery | `LevelBadge`, label jenis | sudah |
| Ritme bagian: judul – kalimat – gambar | Missive | halaman pengenalan (bila ada) | belum dibutuhkan |
| Pin per lokasi, sidebar vertikal, kartu bulat berbayang, testimoni | semua | — | ditolak |
