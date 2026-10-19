# 172 — Lima permintaan pemilik proyek, 9 Oktober 2026

1. **Mode gelap lebih terang** — token `.dark` di `globals.css` (latar 17/26/44, panel 25/37/60,
   garis lebih terlihat) dan `PresisiColors` Android; teks tidak berubah, kontras ≥ 5:1.
2. **Sorotan notifikasi** — API `/notifications` memberi `urgent`/`urgent_total` (darurat selalu;
   laporan berkategori `citizen_report_urgent_categories` di taksonomi: tawuran, Kejahatan
   Jalanan/begal). Web: spanduk atas (`PanicBanner`) berkedip untuk darurat **dan** laporan
   mendesak, lonceng berkedip, item disorot; `prefers-reduced-motion` dihormati. Android:
   kartu beranda bernapas merah. Fungsi tidak menerima keduanya (tanpa permission).
3. (tidak ada nomor 3 pada permintaan)
4. **Administrator memutuskan rekomendasi** — `commander_decision:approve` (0014); test
   pemisahan tugas disesuaikan: pemegangnya tepat Pimpinan + Administrator.
5. **Status hanya Administrator** — permission baru `citizen_report:triage`, `crime:triage`
   (0014); dua endpoint status, antrean triase, tombol Android mengikuti.
6. **Perkiraan bulan depan .docx** — `services/outlook.py` + `GET /patrol-plan/outlook`
   (`python-docx`); web: panel "Perkiraan Singkat Bulan Depan" di Rencana Patroli, unduhan
   lewat `/api/perkiraan`. Dasar: bulan kalender yang sama tahun-tahun sebelumnya, aturan slot
   `plan-rules.yaml`, rekomendasi `function-rules.yaml`. PROPOSED, bukan model terlatih.

Uji: suite API penuh, test web, test unit Android, `next build`, `assembleRelease` (2.8.0).

## Tambahan 13 Oktober 2026 — bentuk Kirkat dan nama produk

Pemilik proyek mengunggah `CONTOH FORMAT PERKIRAAN SINGKAT.docx` (Perkiraan Intelijen
Singkat Baintelkam). Yang diambil darinya: A4, Arial 12, margin kiri 2,5 cm dan 2 cm lainnya,
kop satuan + baris nomor naskah, judul "PERKIRAAN INTELIJEN SINGKAT / TENTANG / …", bagian
PENDAHULUAN – KEADAAN SASARAN (Subyek, Situasi Khusus, Data Sasaran) – ANALISA (Kemampuan
Sasaran, Kemampuan Penanggulangan) – KESIMPULAN (Kondisi Sasaran, Kemampuan Satuan) – SARAN,
penomoran bertingkat dengan indentasi gantung, teks rata kiri-kanan, blok tanda tangan, kaki
halaman klasifikasi (`CLASSIFICATION = "RAHASIA"`, satu konstanta). Yang ditambahkan: tabel
bergaris pada Data Sasaran. Nama produk menjadi **SIGAP** (lihat docs/01 §19.2).
