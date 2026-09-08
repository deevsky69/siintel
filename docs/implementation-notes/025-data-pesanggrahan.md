# 025 — Melengkapi dataset dengan Kecamatan Pesanggrahan

> **Status:** TECHNICAL DECISION atas KEPUTUSAN PEMILIK PROYEK
> **Keputusan:** 8 September 2026 — "tambahkan data Pesanggrahan"
> **Menutup:** temuan audit **S-12** (`000-specification-audit.md`)

---

## 1. Apa yang kurang, dan bagaimana ketahuannya

Jakarta Selatan memiliki **sepuluh** kecamatan. Dataset peragaan memuat sembilan;
Pesanggrahan beserta kelima kelurahannya — Ulujami, Petukangan Utara, Petukangan Selatan,
Pesanggrahan, dan Bintaro — tidak ada sama sekali.

Kekurangan ini tercatat sejak audit spesifikasi awal sebagai S-12, dengan catatan "perlu
konfirmasi apakah cakupan PoC memang 9 kecamatan". Ia terlihat lagi — kali ini tidak dapat
diabaikan — ketika batas wilayah sungguhan dipasang pada peta (`084-peta-berlapis.md`) dan
sebuah kecamatan tergambar kosong di sisi barat tanpa alasan yang dapat dijelaskan.

**Ini keputusan tentang ISI dataset peragaan, bukan keputusan teknis** (CLAUDE.md §17).
Karena itu ia menunggu pemilik proyek, dan dikerjakan setelah ia memutuskannya.

---

## 2. Berapa banyak yang ditambahkan

| Berkas | Sebelum | Sesudah | Pesanggrahan |
|---|---:|---:|---:|
| `locations.csv` | 33 | 37 | 4 |
| `crime_incidents.csv` | 1.200 | 1.345 | 145 |
| `risk_scores.csv` | 2.019 | 2.264 | 245 |
| `predictions.csv` | 180 | 202 | 22 |
| `early_warnings.csv` | 84 | 94 | 10 |
| `recommendations.csv` | 84 | 94 | 10 |
| `commander_decisions.csv` | 63 | 68 | 5 |
| `operational_actions.csv` | 52 | 56 | 4 |
| `prediction_actual.csv` | 241 | 252 | 11 |
| `patrol_activity.csv` | 180 | 202 | 22 |
| `intelligence_reports.csv` | 120 | 135 | 15 |
| `citizen_reports.csv` | 150 | 150 | 14 |
| `public_alerts.csv` | 25 | 25 | 3 |
| `community_feedback.csv` | 60 | 60 | 4 |

Tiga berkas terakhir jumlah totalnya tidak berubah karena ia **dibangun ulang** dari data
primer, bukan ditambahi — lihat §5.

---

## 3. Empat sel grid, bukan lima

Pesanggrahan punya lima kelurahan dan mendapat **empat** sel grid. Itu mengikuti pola yang
sudah ada, bukan kelalaian: Kebayoran Baru memiliki sepuluh kelurahan dengan lima sel, Tebet
tujuh kelurahan dengan empat sel. Grid peragaan memang tidak menutupi setiap kelurahan, dan
membuat Pesanggrahan satu-satunya yang tertutup penuh akan membuatnya tampak lebih terpantau
daripada tetangganya.

Koordinat tiap sel diambil dari **batas kelurahan sungguhan** (OpenStreetMap, lewat
`data/batas-osm/`), bukan dikira-kira. Titiknya dijamin berada di dalam kelurahannya:
keempat sel dan seluruh 145 kejadian diperiksa jatuh di dalam batas Pesanggrahan.

---

## 4. Angkanya ditiru, bukan dikarang

Setiap sebaran dipelajari dari sembilan kecamatan yang sudah ada, lalu ditiru: jenis
kejadian, modus, sasaran, jam, status, kelas risiko, keandalan intelijen, skor urgensi.
Volumenya mengikuti laju per sel grid — 1.200 kejadian pada 33 sel berarti ±36 per sel.

Hasilnya duduk di tengah-tengah tetangganya pada setiap ukuran:

```text
kecamatan            sel  kejadian  penilaian  prediksi  peringatan  patroli
Kebayoran Baru        5      188       313        33         11        21
Tebet                 4      159       246        24         13        23
Pasar Minggu          4      160       240        17          8        20
Pesanggrahan          4      145       245        22         10        22   ← baru
Cilandak              4      139       243        20         10        24
Jagakarsa             4      122       243        20          9        27
Kebayoran Lama        3       74       181        13          6        12
```

### 4.1 Dua kali salah menebak sebarannya

**Percobaan pertama** membangkitkan lima faktor risiko acak lalu menjumlahkannya. Sebarannya
jauh lebih sempit daripada aslinya — rata-rata lima peubah acak selalu lebih memusat — dan
hanya menghasilkan **dua** peringatan dini dari 22 prediksi, karena hampir tidak ada skor
yang mencapai ambang 70. Diperbaiki dengan membalik arahnya: skor diambil dari sebaran skor
nyata, faktornya disusun agar berjumlah tepat.

**Percobaan kedua** mengambil prediksi acak dari penilaian Moderate ke atas, dan menghasilkan
tujuh peringatan — masih separuh dari yang semestinya. Sebabnya prediksi ternyata condong
jauh ke atas: tidak satu pun dari 180 prediksi berkelas Low, dan 47% melewati ambang
peringatan dibanding 18% pada penilaian. Yang diterbitkan sebagai prediksi memang sel yang
sudah menonjol. Diperbaiki dengan meniru sebaran skor prediksi secara langsung.

Keduanya dicatat karena keduanya **lolos tanpa galat apa pun**. Data yang sebarannya salah
tidak merusak apa-apa — ia hanya membuat satu kecamatan tampak lebih tenang daripada
tetangganya tanpa ada yang pernah menilainya demikian.

---

## 5. Yang dibangkitkan, dan yang diserahkan

Skrip hanya membangkitkan **data primer**:

```text
locations   crime_incidents   risk_scores   predictions
early_warnings   recommendations   commander_decisions
patrol_activity   intelligence_reports
```

Sisanya diserahkan kepada `seeding regenerate`, yang sudah ada dan sudah menjadi
satu-satunya tempat aturannya ditulis:

```text
regenerate()              → risk_scores, predictions, early_warnings dinormalkan
regenerate_operational()  → operational_actions, prediction_actual diturunkan
regenerate_public()       → citizen_reports, public_alerts, community_feedback dibangun ulang
```

Percobaan pertama membangkitkan semuanya sendiri dan melanggar empat aturan sekaligus:
keputusan menyetujui tanpa tindakan, evaluasi atas prediksi yang belum terbit, false negative
pada ancaman yang tidak pernah dinilai, dan laporan warga yang berubah begitu mesin
normalisasi dijalankan. Menyalin aturan ke tempat kedua selalu berakhir begitu.

**Keputusan komandan tetap dibangkitkan skrip**, dan itu bukan pengecualian yang malas:
keputusan adalah perbuatan manusia — komandan memilih rekomendasi mana yang ia putuskan dan
mana yang dibiarkan menunggu, dan tidak ada aturan yang dapat menurunkannya dari data lain.
Tindakan operasional sebaliknya mengikuti keputusan secara pasti.

---

## 6. Yang menangkap kesalahan, dan apa yang ditangkapnya

Empat lapis pemeriksaan menolak data yang tidak koheren, seluruhnya sudah ada sebelum
pekerjaan ini:

| Penangkap | Yang ditangkapnya |
|---|---|
| Kunci unik basis data | 245 penilaian diundi bebas → tabrakan pada (sel, ancaman, jendela, tanggal) |
| Validator seeding | false negative tanpa kejadian nyata yang ditunjuk |
| Validator taksonomi | status peringatan publik disalin dari peringatan dini (`Acknowledged` bukan domainnya) |
| Test seeding | horizon prediksi tidak sesuai jendela; evaluasi atas prediksi `Draft` |

Satu test diperbaiki, bukan datanya: `test_time_pattern_uses_local_time_not_utc`
membandingkan "jam tersibuk" sebagai satu nilai, padahal jam 18 dan 21 kini seri persis pada
106 kejadian. `max()` di Python dan `order by … limit 1` di SQL memutus seri dengan cara
berbeda, sehingga uji itu gagal karena aritmetika pemutus seri — bukan karena yang hendak
dibuktikannya. Kini keduanya dibandingkan sebagai himpunan.

Tiga test audit juga diperbaiki. Ketiganya menegaskan adanya penolakan pada jejak audit
tetapi tidak pernah menimbulkannya sendiri — mereka bergantung pada penolakan yang kebetulan
sudah ada di basis data. Pada basis data yang baru di-seed tidak ada satu pun:
`data/sample/audit_logs.csv` tidak dimuat perintah seed mana pun, dan seluruh 400 barisnya
berstatus SUCCESS. Uji yang hasilnya bergantung pada riwayat pemakaian tidak menguji apa pun.

---

## 7. Membangun ulang

```sh
python3 scripts/tambah-pesanggrahan.py    # menolak berjalan bila Pesanggrahan sudah ada
pnpm seed                                  # memuat ulang ke basis data
```

Deterministik: dua penjalanan pada data yang sama menghasilkan berkas yang **identik byte per
byte**. Itu bukan kenyamanan melainkan syarat — data peragaan yang tidak dapat dibangun ulang
persis sama bukan data yang asal-usulnya dapat diperiksa.
