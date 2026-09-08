# 084 — Peta berlapis dan batas wilayah sungguhan

> **Status:** TECHNICAL DECISION
> **Fase:** PHASE 8 (GIS), revisi pemilik proyek 8 September 2026
> **Terakhir diperbarui:** 8 September 2026

---

## 1. Apa yang berubah

Peta lama menggambar **sembilan poligon perkiraan** hasil pembagian Voronoi dari 33 titik
lokasi. Bentuknya cukup untuk membaca sebaran, tetapi ia bukan batas wilayah — dan pada
sistem yang dipakai untuk membicarakan wilayah hukum, "bukan batas wilayah" adalah masalah.

Sekarang ada **tiga lapisan dengan batas administratif sungguhan**:

| Lapisan | Isi | Diwarnai? |
|---|---|---|
| `polda` | 12 kota/kabupaten wilayah hukum Polda Metro Jaya | hanya Jakarta Selatan |
| `kecamatan` | 10 kecamatan Jakarta Selatan | ya, menurut layer yang tampil |
| `kelurahan` | 65 kelurahan, disaring menurut kecamatan | **tidak** |

Beranda membuka pada lapisan `polda`; halaman `/peta` menerima `?tingkat=`.

---

## 2. Sumber data dan lisensi

**OpenStreetMap**, diambil lewat Overpass API oleh `scripts/bangun-batas-wilayah.py`.
Berlisensi **ODbL 1.0**: karya yang menampilkannya wajib mencantumkan "© Kontributor
OpenStreetMap", dan atribusi itu digambar di kaki peta — bukan hanya dicatat di sini.

geoBoundaries (CC-BY 4.0) sempat dipertimbangkan dan ditolak: untuk Indonesia ia hanya
menyediakan sampai ADM2 (kabupaten/kota), tanpa kecamatan maupun kelurahan. Sumber GeoJSON
lain yang beredar di GitHub ditolak karena **tidak menyatakan lisensinya**; menanam data tak
berlisensi ke dalam prototipe untuk instansi bukan risiko yang pantas diambil demi kemudahan.

### 2.1 Tingkat administrasi OSM bergeser di DKI

```text
DKI Jakarta        level 5 = kota administrasi   6 = kecamatan   7 = kelurahan
Depok/Bekasi/Tangerang  level 5 = kota/kabupaten  6 = kecamatan   7 = kelurahan
```

Percobaan pertama mencari kota di `admin_level=6` dan hanya menemukan dua wilayah — keduanya
ternyata **kecamatan** bernama "Depok" dan "Tangerang" di kabupaten lain.

---

## 3. Satu sistem koordinat untuk ketiga lapisan

Proyeksi equirectangular, **1 satuan gambar = 10 meter**, sumbu Y menghadap ke bawah.
Ketiga lapisan memakai proyeksi yang sama, sehingga menyelami peta hanya mengubah `viewBox`.

Kalau tiap lapisan punya sistemnya sendiri, satu titik kejadian akan berpindah tempat ketika
pengguna menyelam — dan tidak ada cara membuktikan mana yang benar. Test
`meletakkan Jakarta Selatan di dalam bidang wilayah hukum Polda Metro Jaya` menjaga ini.

---

## 4. Induk kelurahan: tiga cara, dua gagal

Tiap kelurahan harus tahu kecamatan induknya agar dapat disaring saat menyelam. Urutan
percobaannya dicatat supaya tidak diulang:

| Cara | Hasil |
|---|---|
| Titik pusat massa kelurahan diuji terhadap poligon kecamatan | gagal — pusat poligon cekung dapat jatuh **di luar poligonnya sendiri** ("Pejaten Timur") |
| Menghitung berapa banyak simpul kelurahan yang jatuh di tiap kecamatan | gagal — kelurahan bertetangga berbagi ratusan simpul **persis di garis batas**, dan uji pancaran sinar pada titik di garis hasilnya sembarang. "Bintaro" tercatat di Kebayoran Lama, padahal ia di Pesanggrahan |
| Menanyakan hierarkinya kepada Overpass, satu kueri per kecamatan | benar, tetapi sepuluh kueri beruntun ditolak karena pembatasan laju |
| **Satu titik yang dijamin ada di dalam kelurahan**, diuji terhadap kecamatan yang belum disederhanakan | **dipakai** |

Titik itu dicari dengan menarik garis mendatar melalui tengah poligon dan mengambil tengah
potongan terpanjang yang berada di dalamnya.

Hasilnya diperiksa silang dengan tag `wikipedia` OSM, yang berbentuk
`id:Duren Tiga, Pancoran, Jakarta Selatan` — komponen keduanya adalah kecamatan. Tag itu ada
pada 46 dari 65 kelurahan; **ketidakcocokan menghentikan pembangunan**.

Sebaran akhirnya cocok persis dengan struktur resmi Jakarta Selatan pada kesepuluh
kecamatan (Kebayoran Baru 10, Setiabudi 8, Pasar Minggu 7, Tebet 7, Jagakarsa 6,
Kebayoran Lama 6, Pancoran 6, Cilandak 5, Mampang Prapatan 5, Pesanggrahan 5).

---

## 5. Keputusan tampilan, dan alasannya

**Kelurahan tidak diwarnai.** Basis data menyimpan lokasi sampai tingkat kecamatan.
Mewarnai kelurahan berarti menampilkan penilaian yang belum pernah dibuat siapa pun
(CLAUDE.md §24). Yang digambar di sana adalah titik kejadian pada koordinat sesungguhnya.

**Sebelas wilayah tetangga tembus pandang, namanya muncul saat disorot.** Dua belas nama
pada bingkai selebar seratus kilometer saling menimpa sampai tidak satu pun terbaca.

**Jakarta Selatan diwarnai aksen, bukan warna risiko.** Pada tingkat itu tidak ada satu skor
untuk seluruh Jakarta Selatan; memberinya warna dari tangga risiko akan menyatakan penilaian
yang tidak pernah dihitung.

**Legenda risiko tidak digambar pada tingkat `polda`.** Legenda yang tidak menjelaskan apa
pun di layar membuat pembaca mencari warna yang tidak ada.

**Kepulauan Seribu digambar tetapi tidak menarik bingkai.** Ia memang wilayah hukum Polda
Metro Jaya — menghapusnya menggambarkan wilayah hukum yang salah — tetapi gugusannya
membentang sekitar 80 kilometer ke utara, seluas seluruh daratan Jabodetabek. Memuat
keduanya dalam satu bingkai mengerutkan daratan tempat seluruh data berada menjadi
seperempat layar. Kakinya menyebutkan hal ini.

**Label digambar sebagai HTML di atas peta.** Ukuran huruf di dalam SVG adalah satuan gambar
yang ikut mengecil bersama `viewBox`; tidak ada satu nilai pun yang terbaca pada tiga
tingkat penyelaman sekaligus.

---

## 6. Test proyeksi: dari angka beku ke kebenaran luar

Test lama membekukan empat koordinat harapan. Test semacam itu hanya membuktikan bahwa kode
masih menghasilkan angka yang sama seperti kemarin — ia lulus dengan gembira meski
proyeksinya salah sejak awal.

Sekarang yang diuji: **setiap lokasi pada `data/sample/locations.csv` harus jatuh di dalam
kecamatan yang disebutnya sendiri.** Kedua sisinya berasal dari luar kode ini — nama
kecamatan dari data contoh, batasnya dari OpenStreetMap.

Toleransinya 500 meter, dan ada alasannya: koordinat data contoh dibulatkan ke tiga angka
desimal (±111 meter) dan letaknya sintetis, sehingga lima dari 33 titik jatuh 38–484 meter
di luar kecamatannya. Proyeksi yang benar-benar rusak tidak menghasilkan simpangan ratusan
meter — ia memindahkan titik berkilo-kilometer, dan test ini menangkapnya.

---

## 7. Temuan: satu kecamatan hilang dari data contoh

Jakarta Selatan memiliki **10 kecamatan**. `data/sample/locations.csv` hanya memuat
sembilan — **Pesanggrahan tidak ada**, beserta kelima kelurahannya.

Peta tetap menggambar Pesanggrahan, dengan warna "tidak ada data". Itu jawaban yang jujur
dan lebih baik daripada menghilangkannya, yang akan menggambarkan Jakarta Selatan bertubuh
sembilan kecamatan.

> **MENUNGGU KEPUTUSAN PEMILIK PROYEK.** Menambahkan lokasi, kejadian, dan penilaian untuk
> Pesanggrahan berarti membangkitkan data sintetis baru. Itu keputusan tentang isi dataset
> peragaan, bukan keputusan teknis (CLAUDE.md §17).

---

## 8. Membangun ulang

```sh
python3 scripts/bangun-batas-wilayah.py
```

Menulis `apps/web/src/lib/wilayah.generated.ts` (113 KB). Jawaban Overpass disinggahkan di
`data/batas-osm/`; hapus isinya untuk mengambil ulang dari OSM.
