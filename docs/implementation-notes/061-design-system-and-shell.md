# TASK 061 + 060 — DESIGN SYSTEM & SHELL APLIKASI

Tanggal: 2026-09-01
Status: **SELESAI — halaman terbangun, tersaji, dan diverifikasi.**

Task pertama pada jalur kritis `docs/09`. Prioritas pemilik proyek: **tampilan lebih dulu.**

---

## 1. ACUAN

| Sumber | Yang diambil |
|---|---|
| `design/gambaran-website.png` | Tata letak panel, sidebar 9 menu, topbar, tangga warna risiko |
| Aplikasi acuan `siintel-app` | Next.js App Router + Tailwind, font Chakra Petch / Inter / JetBrains Mono |

Pemeriksaan aplikasi acuan juga menunjukkan **petanya tidak memakai tile basemap** — digambar
sendiri. Temuan itu menghapus B-1 dari jalur kritis (lihat `docs/09` §3).

---

## 2. YANG DIBUAT

```text
apps/web/tailwind.config.ts          tema: base/ink/accent + tangga risiko
apps/web/src/app/globals.css         latar, kilau sudut, kelas .panel dan .stat-*
apps/web/src/app/layout.tsx          font ter-bundle, kerangka topbar + sidebar + konten
apps/web/src/app/page.tsx            kerangka Executive Dashboard
apps/web/src/components/panel.tsx    pembungkus panel baku
apps/web/src/components/data-state.tsx  Loading / Empty / Error baku
apps/web/src/components/shell/       sidebar, topbar, jam WIB, ikon SVG, daftar menu
apps/web/src/lib/risk.ts             kelas risiko, label Indonesia, warna
apps/web/src/components/shell/shell.test.tsx   8 test
```

---

## 3. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | **Tailwind 3**, bukan 4 | Menyamakan dengan aplikasi acuan; ekosistem plugin dan contoh lebih banyak |
| 2 | Font dimuat lewat `next/font` (ter-bundle) | Demo harus berjalan **tanpa internet** saat paparan |
| 3 | Ikon digambar sendiri sebagai SVG | Hanya sembilan ikon; menambah pustaka ikon tidak sepadan, dan tetap bebas unduhan |
| 4 | Warna risiko dinamai menurut **makna** (`risk.low`…`risk.critical`) | Ambang belum final (U-01); saat berubah, nama kelas di seluruh antarmuka tidak ikut berganti |
| 5 | Ambang di `lib/risk.ts` ditandai sepadan `config/risk/` dan **DEMO/PROPOSED** | Antarmuka tidak boleh menjadi tempat ambang tersembunyi kedua |
| 6 | Jam memakai zona `Asia/Jakarta` eksplisit, bukan zona perangkat | Waktu disimpan UTC dan ditampilkan WIB (docs/02 K-3) |
| 7 | Render pertama jam sengaja kosong | Menghindari hydration mismatch antara server dan klien |
| 8 | Panel dashboard **dibiarkan kosong** dengan penanda task | Dashboard berisi angka karangan justru merusak klaim "working prototype, bukan mockup" |
| 9 | Identitas pengguna ditulis "belum masuk — TASK 050" | Identitas palsu yang tampak nyata menyesatkan saat paparan |
| 10 | Seluruh menu ditampilkan meski RBAC belum hidup | Menyembunyikan menu bukan pengganti otorisasi (CLAUDE.md §15); pembatasan dipasang di TASK 052 |

---

## 4. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
pnpm build          → Compiled successfully
next start :3100    → GET /      200, judul "PREDIKSI PRESISI — Polres Metro Jakarta Selatan"
                      halaman memuat Situation Overview, Live Kamtibmas Map,
                      Early Warning, AI Recommendation, dan sidebar Dashboard
                      GET /peta  404 (memang belum dibuat)

CSS terbangun       → body berlatar rgb(5 11 24) dengan kilau radial,
                      warna risiko dan kelas .panel-title ikut ter-compile

biome check         → 19 berkas bersih
tsc --noEmit        → tanpa error
vitest              → 8 test lulus
```

Test menjaga: seluruh sembilan menu tersedia sebagai tautan, menu aktif menandai dirinya untuk
pembaca layar, identitas sistem dan satuan wilayah tampil, keterangan "belum masuk" tetap ada,
judul panel berupa heading, serta pemetaan skor ke kelas risiko.

---

## 5. YANG BELUM

Panel masih kosong. Angka baru muncul setelah API domain hidup — itu urutan yang disengaja
supaya tidak ada satu pun angka di layar yang tidak berasal dari database.

## 6. BERIKUTNYA

`docs/09` Tahap B: **TASK 030** (fondasi API) lalu **050–053** (login, role, otorisasi, audit),
kemudian API baca dan **TASK 070** untuk mengisi dashboard ini dengan data nyata.
