# TASK 070 — EXECUTIVE DASHBOARD

Tanggal: 2026-09-01
Status: **SELESAI — layar terisi data nyata, diverifikasi lewat aplikasi berjalan.**

Layar utama pada `design/gambaran-website.png` kini hidup: seluruh angka berasal dari API,
yang membacanya dari database. **Tidak ada satu pun nilai yang ditanam di kode** — itu syarat
klaim *"working prototype, bukan mockup"* pada success criteria Taskap.

---

## 1. YANG DIBUAT

```text
src/middleware.ts                  melindungi seluruh halaman aplikasi
src/lib/session.ts                 cookie httpOnly untuk token
src/lib/api.ts                     klien API sisi server + penyegaran token otomatis
src/lib/dashboard.ts               bentuk data dan pemanggilan endpoint
src/app/masuk/                     halaman masuk + formulir
src/app/api/auth/login|logout/     route handler yang meneruskan ke backend
src/app/(app)/layout.tsx           shell untuk halaman aplikasi
src/app/(app)/page.tsx             Executive Dashboard
src/components/dashboard/          7 panel + 20 test
```

---

## 2. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | Seluruh pemanggilan API berjalan **dari server Next.js**, bukan dari peramban | Token tidak pernah menyentuh JavaScript klien, dan alamat backend tidak perlu terbuka ke publik saat demo di-deploy |
| 2 | Token pada cookie `httpOnly`, bukan `localStorage` | Skrip pihak ketiga tidak boleh dapat membacanya (CLAUDE.md §23) |
| 3 | Access token kedaluwarsa → **satu kali penyegaran diam-diam** sebelum dialihkan ke halaman masuk | Paparan tidak boleh terputus hanya karena token 15 menit habis |
| 4 | Middleware hanya **kenyamanan**, bukan pengamanan | Otorisasi ditegakkan backend pada setiap permintaan; melewati middleware tidak memberi akses data |
| 5 | Grafik tren digambar sebagai **SVG langsung**, tanpa pustaka grafik | Satu grafik garis tidak sepadan dengan menambah dependensi, dan demo harus jalan tanpa unduhan |
| 6 | Panel kosong menyatakan **"tidak ada"**, bukan menampilkan 0 | Angka nol dan ketiadaan data punya makna berbeda |
| 7 | Indeks keamanan ditampilkan **bersama penjelasan asalnya** | Bukan angka resmi (U-01/U-02) |
| 8 | Mode demo dinyatakan terbuka di atas layar | Pembaca harus tahu "24 jam terakhir" dihitung terhadap waktu acuan dataset |
| 9 | Panel rekomendasi memuat kalimat penegas | Rantai human-in-the-loop harus terbaca di layar, bukan hanya di dokumen (CLAUDE.md §13) |

---

## 3. VERIFIKASI LEWAT APLIKASI BERJALAN

```text
GET  /            (tanpa sesi) → 307 ke /masuk?lanjut=%2F
GET  /masuk                    → halaman masuk tampil
POST /api/auth/login           → 200, cookie predpol_access + predpol_refresh tersimpan
GET  /            (dengan sesi)→ dashboard 60 KB berisi seluruh panel
```

Angka yang benar-benar tampil di layar, cocok dengan API:

```text
Security Index    47 /100   disertai "100 dikurangi rata-rata seluruh sel risiko…"
Kejadian 24 Jam    2        Prediksi 24 Jam  4
High Risk Area     8        Warning Aktif   36
Operasi Berjalan  26        Jam Kritis      18:00-23:59
Top Threat        CURAT 88 (Kritis)
```

### Bukti terkuat: layar berubah menurut kewenangan

Masuk sebagai dua akun berbeda pada aplikasi yang sama:

| | Pimpinan | Polsek |
|---|---|---|
| Kejadian 24 jam | 2 | 1 |
| Prediksi 24 jam | 4 | 0 |
| High risk area | 8 | 1 |
| Risk Index by District | 8 kecamatan | **hanya Tebet** |

Pembatasan itu berasal dari backend, bukan dari menu yang disembunyikan.

```text
biome (36 berkas) → bersih
tsc --noEmit      → bersih
vitest            → 20 test lulus
next build        → Compiled successfully
```

---

## 4. YANG BELUM

Panel peta masih menyatakan dirinya menunggu TASK 080–084. Panel lain sudah hidup.

## 5. BERIKUTNYA

**TASK 080–084 — Peta.** Sesuai penjelasan pemilik proyek: peta wilayah yang ketika
di-*hover* atau diklik menampilkan potensi ancaman kecamatan tersebut beserta rinciannya
(WHAT/WHERE/WHEN/RISK/CONFIDENCE/WHY). Digambar dari data wilayah, tanpa tile server.
