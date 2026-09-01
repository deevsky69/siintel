# RENCANA INTEGRASI MODEL AI — BAHAN KEPUTUSAN

Status: **PROPOSED — memerlukan keputusan pemilik proyek**
Tanggal: 1 September 2026

Dokumen ini menjawab pertanyaan: *apakah PREDIKSI PRESISI dapat memakai Claude, dan
sejauh mana pantas dipakai.* Ia sengaja dibuat sebagai bahan keputusan, bukan sebagai
rencana yang sudah dijalankan, karena dua hal di dalamnya adalah **keputusan kebijakan**
(CLAUDE.md §2D), bukan keputusan teknis.

---

## 1. LANGGANAN CLAUDE MAX **TIDAK** DAPAT DIPAKAI OLEH APLIKASI

Ini perlu diluruskan lebih dulu karena menentukan seluruh perencanaan biaya.

| | Claude Max | Anthropic API |
|---|---|---|
| Untuk apa | Anda memakai Claude lewat claude.ai dan Claude Code | Aplikasi Anda memanggil Claude dari kodenya sendiri |
| Cara membayar | Langganan bulanan | Per token yang dipakai |
| Kredensial | Akun pribadi Anda | **API key** dari `console.anthropic.com` |
| Dapat dipakai server aplikasi | **Tidak** | Ya |

Langganan Max adalah lisensi **perseorangan** untuk Anda memakai Claude. Ia tidak
menerbitkan API key dan tidak memberi kuota kepada aplikasi. Menjadikan langganan
perseorangan sebagai mesin yang melayani banyak pengguna juga bukan pemakaian yang
sesuai ketentuan.

**Kesimpulan:** aplikasi ini **dapat** memakai Claude, tetapi lewat **Anthropic API
dengan penagihan terpisah** — bukan lewat langganan Max Anda. Biayanya kecil untuk
skala prototipe, tetapi harus dianggarkan sendiri.

---

## 2. DI MANA AI BAHASA **TIDAK BOLEH** DIPAKAI

Ini bagian terpenting, dan berlawanan dengan dugaan yang umum.

**Claude tidak boleh menjadi mesin prediksi maupun penilai risiko.** Bukan karena
kemampuannya kurang, melainkan karena tiga syarat yang sudah Anda tetapkan sendiri
tidak dapat dipenuhi olehnya:

| Syarat | Sumber | Mengapa model bahasa gagal memenuhinya |
|---|---|---|
| **Dapat direproduksi** | CLAUDE.md §25 | Keluaran model bahasa tidak deterministik. Pertanyaan sama dapat menghasilkan skor berbeda, sehingga `model_version` kehilangan makna |
| **Dapat dievaluasi** | CLAUDE.md §26, Taskap #06 | Precision dan recall menuntut keluaran yang tetap dan terukur. Angka yang berubah-ubah tidak dapat dinilai dengan jujur |
| **Penjelasan berasal dari mekanisme yang benar-benar dipakai** | CLAUDE.md §27 | Model bahasa menghasilkan penjelasan yang **terdengar** masuk akal, bukan yang benar-benar menjadi sebab angkanya. Inilah "penjelasan fiktif" yang dilarang |

Bahaya nyatanya bukan pada kualitas, melainkan pada **kepercayaan yang tidak dapat
dipertanggungjawabkan**: skor yang tampak berwibawa, dengan alasan yang terdengar
meyakinkan, padahal tidak dapat ditelusuri maupun diuji. Untuk sistem yang menyangkut
kamtibmas, itu lebih berbahaya daripada tidak punya prediksi sama sekali.

Karena itu **penilaian risiko dan prediksi tetap berbasis aturan berbobot sekarang, dan
model statistik terlatih nanti** (TASK 100–104).

---

## 3. DI MANA AI BAHASA JUSTRU UNGGUL

Yang dikerjakan Claude dengan baik adalah hal yang memang pekerjaan bahasa — dan di
situ ia menambah nilai nyata tanpa merusak satu pun syarat di atas.

### A. Menyusun narasi briefing dari angka yang sudah ada

**Masukan:** angka dari basis data — risiko per kecamatan, peringatan aktif, prediksi,
faktor dominan.
**Keluaran:** paragraf briefing harian yang siap dibacakan.

Angkanya tetap berasal dari basis data; Claude hanya menuliskannya sebagai kalimat.
Bila ia salah menulis, kesalahan itu **terlihat** karena angkanya tetap tertera di
layar di sebelahnya.

*Nilainya saat paparan:* menunjukkan sistem tidak berhenti pada dasbor angka.

### B. Mengubah laporan intelijen bebas menjadi data terstruktur

Basis data memuat 120 laporan intelijen berbentuk teks bebas. Claude dapat menariknya
menjadi bidang terstruktur — jenis ancaman, wilayah, rentang waktu, tingkat keandalan.

Ini pemakaian yang **paling aman dan paling berguna**: keluarannya menjadi **masukan**
bagi model yang sesungguhnya, bukan pengganti model itu. Hasilnya juga dapat diperiksa
kebenarannya terhadap teks aslinya.

*Nilainya saat paparan:* menjawab "bagaimana laporan intelijen yang tidak terstruktur
ikut diperhitungkan".

### C. Menyusun draf rekomendasi

Claude menyusun kalimat rekomendasi berdasarkan prediksi dan faktor dominannya.

**Syarat mutlak:** draf itu tetap berstatus *menunggu keputusan* dan tetap melewati
Pimpinan. Rantai human-in-the-loop **tidak berubah sedikit pun** — yang berubah hanya
siapa yang menuliskan kalimat usulannya.

### D. Menjawab pertanyaan atas data

"Apa yang terjadi di Tebet pekan lalu?" dijawab dengan menerjemahkan pertanyaan menjadi
kueri, lalu menuliskan hasilnya. Angka tetap berasal dari basis data.

---

## 4. PAGAR YANG WAJIB DIPASANG BILA INI DIJALANKAN

| # | Pagar | Alasan |
|---|---|---|
| 1 | Claude **tidak pernah** menghasilkan `risk_score`, `risk_class`, maupun `confidence` | Angka itu harus dapat direproduksi dan dievaluasi |
| 2 | Setiap keluaran Claude **ditandai di layar** sebagai susunan AI | Pembaca berhak tahu mana angka terukur dan mana kalimat susunan mesin |
| 3 | Faktor dominan **tidak pernah** berlabel `MODEL` bila berasal dari Claude | Label `RULE`/`MODEL` menyatakan mekanisme sebenarnya (§27). Perlu label ketiga bila dipakai |
| 4 | Tersimpan: nama model, versi, versi prompt, dan rujukan data masukan | Ketertelusuran (§25) |
| 5 | Draf rekomendasi tetap `PENDING_REVIEW` | Human-in-the-loop tidak boleh dilewati |
| 6 | Kegagalan panggilan API **tidak boleh** membuat layar kosong | Sistem harus tetap berfungsi tanpa AI |
| 7 | Data yang dikirim dibatasi seperlunya | Lihat §5 |

---

## 5. DUA KEPUTUSAN YANG HANYA DAPAT ANDA AMBIL

### Keputusan 1 — Bolehkah data dikirim ke layanan di luar Polri?

**REQUIRES HUMAN / POLICY APPROVAL.**

Anthropic API berjalan di luar jaringan Polri. Setiap pemakaian berarti data yang
diproses **keluar** dari kendali organisasi.

| Keadaan | Pertimbangan |
|---|---|
| **Prototipe sekarang** | Data seluruhnya sintetis, tidak ada identitas nyata. Risikonya rendah, tetapi tetap keputusan Anda |
| **Bila kelak memakai data nyata** | Ini menjadi persoalan klasifikasi data, kedaulatan data, dan kepatuhan. **Tidak dapat diputuskan secara teknis** |

Bila jawabannya tidak boleh, jalan keluarnya bukan membatalkan AI, melainkan
**menjalankan model bahasa di dalam jaringan sendiri** (misalnya Llama atau Qwen pada
server ini). Mutunya di bawah Claude, tetapi tidak ada data yang keluar. Arsitektur
yang saya usulkan sengaja menempatkan pemanggilan model di satu lapisan, sehingga
penggantian ini tidak membongkar aplikasi.

### Keputusan 2 — Sejauh mana AI boleh menyusun rekomendasi?

| Pilihan | Konsekuensi |
|---|---|
| **A. Tidak sama sekali** | Rekomendasi tetap dari aturan. Paling konservatif |
| **B. Menyusun draf, wajib diputus manusia** (usulan saya) | Kalimat lebih tajam, rantai kewenangan utuh |
| **C. Menyusun dan langsung berlaku** | **Melanggar CLAUDE.md §13.** Tidak saya sarankan dalam keadaan apa pun |

---

## 6. USULAN LANGKAH PERTAMA

Bila Anda menyetujui, yang paling layak dikerjakan lebih dulu adalah **A — narasi
briefing harian**:

- risikonya paling rendah: tidak menyentuh satu pun angka, prediksi, maupun keputusan;
- nilainya paling terlihat saat paparan;
- bila layanan AI mati, dasbor tetap berfungsi penuh — hanya paragraf briefingnya yang
  tidak muncul;
- menjadi ujian nyata bagi lapisan pemanggilan model, sebelum dipakai untuk hal yang
  lebih berisiko.

Perkiraan pekerjaan: satu lapisan layanan AI di backend, satu endpoint, satu panel di
dasbor, dan berkas konfigurasi prompt yang diberi versi.

**Yang saya butuhkan dari Anda sebelum mulai:**

1. Jawaban Keputusan 1 — boleh atau tidak data dikirim ke layanan luar.
2. Jawaban Keputusan 2 — A, B, atau C.
3. Bila boleh: **API key Anthropic** yang ditaruh langsung di server pada
   `.env.production` (**jangan dikirim lewat percakapan**, dan jangan pernah masuk
   repository).
