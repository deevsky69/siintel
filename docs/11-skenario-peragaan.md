# SKENARIO PERAGAAN — PREDIKSI PRESISI

Dokumen ini bukan daftar fitur. Ia adalah **urutan layar** beserta klaim Taskap yang
dibuktikan masing-masing, sehingga peragaan menjawab pertanyaan penguji, bukan sekadar
menunjukkan tampilan.

Dua success criteria yang harus terjawab:

- **#05 WORKING PROTOTYPE** — *"bukan mockup semata"*
- **#06 VALIDATION** — Prediction vs Actual

---

## 0. SEBELUM MULAI

| Hal | Nilai |
|---|---|
| Alamat | `https://<domain>` (lihat `docs/10` §5.5) |
| Akun utama | `demo.pimpinan` — satu-satunya peran yang boleh **memutuskan rekomendasi** |
| Akun tindak lanjut | `demo.commandcenter` — satu-satunya peran yang boleh **menerima dan menyelesaikan peringatan** |
| Akun pembanding | `demo.polsek` — dibatasi Polsek Tebet |
| Waktu acuan | `DEMO_REFERENCE_TIME` wajib diisi, jika tidak seluruh panel "24 jam terakhir" kosong |

> **Ganti password kedua akun sebelum paparan.** Nilai yang dipakai selama pengembangan
> harus dianggap bocor (`docs/10` §7.1).

Siapkan **tiga jendela peramban**: Pimpinan, Command Center, dan Polsek. Peragaan
cakupan kewenangan jauh lebih meyakinkan bila terlihat berdampingan.

> **Pimpinan sengaja tidak dapat menerima atau menyelesaikan peringatan.** Itu bukan
> kelalaian: `warning:acknowledge` dan `warning:resolve` dimiliki Command Center, dan
> `acknowledge` juga oleh Polsek. Kapolres memutuskan rekomendasi; yang menangani
> peringatan harian adalah Command Center. Bila pembagian ini tidak sesuai SOP yang
> berlaku, itu **keputusan pemilik proyek**, bukan perubahan teknis (docs/03, P-1..P-7).

---

## 1. DASHBOARD — "angkanya dari mana?"

Buka `/`.

**Klaim:** setiap angka di layar berasal dari database, bukan dari kode.

Yang layak ditunjuk:

- Indeks keamanan **membawa penjelasan asalnya** — "100 dikurangi rata-rata seluruh sel
  risiko. Indeks resmi belum ditetapkan." Ini bukan kelemahan yang lolos; ini keputusan
  sadar agar angka tidak terbaca sebagai indeks resmi Polri (U-01, U-02).
- Panel yang kosong dinyatakan kosong, tidak diisi nol.

**Bila ditanya "apakah ini data asli?"** — jawabannya: bukan. Data sintetis 1.200 kejadian
yang koheren, dan bobot serta ambangnya berstatus `DEMO / PROPOSED`. Yang nyata adalah
**mekanismenya**: struktur data, aturan kewenangan, dan rantai keputusannya.

---

## 2. PETA — "wilayah mana yang rawan, dan mengapa?"

Buka `/peta`. Arahkan kursor, lalu klik satu kecamatan.

**Klaim:** sistem menjawab WHAT / WHERE / WHEN / RISK / CONFIDENCE / **WHY**.

Yang layak ditunjuk:

- Jenis ancaman berperingkat pada wilayah itu, jam rawannya, dan skor risikonya.
- **Faktor dominan beserta labelnya `RULE`** — bukan `MODEL`. Artinya penjelasan ini
  berasal dari aturan yang dijalankan, bukan temuan model terlatih. Menyembunyikan
  perbedaan itu akan membuat peragaan mengklaim lebih dari yang dimiliki (CLAUDE.md §27).
- Layer prediktif **tidak** memberi kelas risiko, karena ambangnya belum ditetapkan.

---

## 3. PERINGATAN DINI — "lalu apa yang terjadi?"

Buka `/peringatan`, pilih satu peringatan.

**Klaim:** peringatan bukan ujung; ia membuka penjelasan dan tindak lanjut.

Yang layak ditunjuk:

- Prediksi sumbernya beserta faktor dominan yang sama — rantainya dapat ditelusuri.
- Versi ambang (`threshold_version`) tertulis di layar, bukan tersembunyi.

---

## 3b. TINDAK LANJUT PERINGATAN — pindah ke jendela Command Center

Pada peringatan berstatus `ACTIVE`, tekan **Terima Peringatan**.

**Klaim:** peringatan bukan sekadar tampilan; ia berpindah status, mencatat pelakunya,
dan meninggalkan jejak audit.

Yang layak ditunjuk:

- Kembali ke jendela Pimpinan, panel yang sama berbunyi **"tidak memiliki kewenangan"**
  — pembagian tugas ditegakkan mesin, bukan disepakati lisan.
- Menekan tombol yang sama dua kali dijawab penolakan, bukan diterima diam-diam.

---

## 4. KEPUTUSAN PIMPINAN — **INI PUNCAK PERAGAAN**

Buka `/rekomendasi`. Pilih satu rekomendasi yang **menunggu keputusan**.

**Klaim:** AI mengusulkan, **manusia memutuskan**. Sistem ini alat bantu, bukan pengambil
keputusan.

Peragakan berurutan:

1. Tunjukkan usulan sistem, dan bahwa layar menyebutnya **opsi, bukan perintah**.
2. Pilih **Modifikasi**, ubah isinya, beri pertimbangan, lalu catat keputusan.
3. Setelah tersimpan: layar menampilkan **usulan asli** dan **rekomendasi setelah
   disesuaikan** berdampingan. Usulan sistem tidak pernah tertimpa.
4. Tunjukkan bahwa rekomendasi itu **tidak dapat diputus ulang** — jejak siapa memutuskan
   apa tidak boleh kabur.

**Bila ditanya "apa yang mencegah sistem bertindak sendiri?"** — jawabannya ada di
database, bukan di aplikasi: sebuah trigger PostgreSQL menolak setiap tindakan operasional
yang tidak berasal dari keputusan `APPROVED` atau `MODIFIED`. Menonaktifkan aplikasi tidak
melonggarkan aturan itu.

---

## 5. KEWENANGAN — "apakah pembatasannya nyata?"

Pindah ke jendela `demo.polsek`, buka layar yang sama.

**Klaim:** otorisasi ditegakkan di backend, bukan dengan menyembunyikan menu.

| Layar | Pimpinan | Polsek |
|---|---|---|
| `/peta` | 9 kecamatan | 1 kecamatan (Tebet); delapan lainnya tertulis "tidak ada data" |
| Rincian `?wilayah=Cilandak` | terbuka penuh | "tidak dapat ditampilkan untuk kewenangan Anda" — bukan melompat diam-diam ke Tebet |
| `/map/area/Pasar Minggu` | 200 | **404** — bukan 403 |
| `/rekomendasi` | 84 rekomendasi | 13 |
| Riwayat keputusan | 64 baris | 9 |
| Tombol keputusan | ada | tidak ada |

Dua hal yang layak dijelaskan:

- Delapan kecamatan tetap **terlihat** sebagai "tidak ada data". Pembatasan dinyatakan
  terbuka, bukan disamarkan menjadi wilayah yang seolah tidak ada.
- Data di luar wilayah dijawab **404, bukan 403**. Menjawab "terlarang" akan membocorkan
  bahwa datanya memang ada di wilayah lain.

---

## 6. EVALUASI — success criteria #06

Buka `/evaluasi`.

**Klaim:** prediksi ini dapat dinilai, bukan hanya ditampilkan.

| Angka | Nilai |
|---|---|
| Precision | 0,397 |
| Recall | 0,400 |
| Baris evaluasi | 241 |

Yang layak ditunjuk:

- Seluruh angka bertanda **`PROPOSED`** karena aturan pencocokan prediksi-kejadian belum
  ditetapkan (U-03). Metrik tanpa definisi pencocokan tidak dapat dipertanggungjawabkan.
- **Recall dapat dihitung** karena dataset memuat 90 *false negative* — kejadian yang
  tidak diprediksi. Tanpa baris itu, recall mustahil dihitung dan angka precision saja
  akan menyesatkan (CLAUDE.md §26).

---

## 7. MENU YANG BELUM DIBANGUN

Bila penguji mengklik `/prediksi`, `/analitik`, `/intelijen`, atau `/admin`, layar
menyatakan terus terang bahwa bagian itu belum dibangun, menyebut nomor task-nya, dan
menunjukkan apa yang **sudah ada** dan menopangnya.

Ini bukan kekurangan yang perlu dihindari saat peragaan — justru pantas ditunjukkan.
Sistem yang menyatakan batasnya sendiri lebih dapat dipercaya daripada sistem yang
tampak selesai seluruhnya.

---

## 8. PERTANYAAN YANG MUNGKIN MUNCUL

| Pertanyaan | Jawaban jujur |
|---|---|
| Apakah ini memakai machine learning? | Belum. Prediksi berasal dari aturan berbobot; setiap faktor dilabeli `RULE` di layar. Model terlatih adalah TASK 100–104 |
| Dari mana bobot risikonya? | `config/risk/risk-weights.yaml`, versi `dummy-v1`, ditetapkan pemilik proyek 9 September 2026. Ditetapkan berarti berlaku sebagai ketentuan; ketepatannya tetap urusan evaluasi |
| Apakah datanya asli? | Tidak. Data sintetis yang koheren. Data resmi tidak pernah dimasukkan ke repository |
| Siapa yang boleh menyetujui? | Saat ini hanya peran Pimpinan. Kewenangan resmi dan pendelegasiannya masih menunggu keputusan (docs/03, P-1..P-7) |
| Apakah keputusan bisa dianulir? | Belum bisa, dan itu disengaja. Aturannya menunggu SOP |
| Berapa besar sistemnya? | 20 tabel, 7 migration, 43 permission, 6 peran, ±4.400 baris data, 246 test API dan 107 test web |

---

## 9. YANG HARUS DISIAPKAN SEHARI SEBELUMNYA

- [ ] Password kedua akun demo sudah diganti
- [ ] `DEMO_REFERENCE_TIME` terisi, dan dashboard menunjukkan angka 24 jam yang tidak nol
- [ ] Satu rekomendasi **sengaja disisakan** berstatus menunggu keputusan untuk diperagakan
- [ ] Dua jendela peramban sudah masuk sebagai Pimpinan dan Polsek
- [ ] Sertifikat HTTPS sudah terbit (`docs/10` §5.4)
- [ ] Satu peringatan **berstatus ACTIVE** disisakan untuk diperagakan tindak lanjutnya
- [ ] Peta dibuka sekali pada tiap peran untuk memastikan tidak ada layar kosong
