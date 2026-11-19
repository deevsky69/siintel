# 180 — Audit 15 November 2026 dan paket pertama: lag navigasi /ops

Keluhan pemilik proyek: klik menu di `/ops` terasa lag/menunggu. Audit dilakukan dengan
pengukuran langsung di server dan tiga penelusuran kode (web, API, kesesuaian spesifikasi).

## Pengukuran

- Beban server rendah (CPU API ±15 % saat idle, memori longgar). Endpoint publik 9–23 ms di
  dalam jaringan, ±100 ms lewat TLS; server di Jakarta.
- Dari log API 10 hari (301 permintaan non-bot): endpoint terberat median 80–120 ms
  (`/map/current-risk` 106, `/notifications` 98, `/dashboard/summary` 81). Per satu
  navigasi (burst ≥3 permintaan): median 6 permintaan, total waktu API median 164 ms,
  p90 837 ms. **API bukan penyebab utama.**
- Log web memuat 11 kali `Cookies can only be modified in a Server Action or Route Handler`,
  dan log API memuat 26 `POST /auth/refresh` berbanding 48 `/auth/me` — bukti siklus token
  yang rusak (lihat penyebab 1).

## Penyebab lag (urut dampak) dan perbaikan paket pertama

1. **Siklus token.** Token akses API 15 menit, cookie 60 menit. Menit 15–60: tiap permintaan
   ditolak 401 → disegarkan dari komponen server → `cookies().set` dilarang Next → token baru
   tidak tersimpan → berulang pada setiap klik, dan panel yang memakai `.catch(() => null)`
   diam-diam kosong.
   **Perbaikan:** `middleware.ts` menyegarkan token bila sisa umurnya < 90 detik (dibaca dari
   klaim `exp` tanpa verifikasi, `lib/token.ts`), memasang cookie baru pada respons DAN
   menyuntikkannya ke header permintaan yang sama; umur cookie akses = umur token (login dan
   refresh); `lib/api.ts` tetap punya jalur cadangan 401→refresh, kini dimemo `cache()` per
   permintaan dan `cookies().set` dibungkus try/catch.
2. **Beranda tanpa `loading.tsx`** padahal terberat (7–15 panggilan, 3–4 gelombang).
   **Perbaikan:** `app/ops/(app)/loading.tsx` (kerangka panel) dan
   `wilayah/[kecamatan]/loading.tsx`.
3. **Tidak ada umpan balik klik menu.** **Perbaikan:** `useLinkStatus` (titik berdenyut) dan
   sorotan optimistik pada item yang diklik di `components/shell/sidebar.tsx`.
4. **Gelombang berurutan & duplikasi.** `getProfile` dipanggil layout dan ±17 halaman tanpa
   dedup; layout menunggu profil sebelum notifikasi; Input dan Produk Bulanan 3 gelombang.
   **Perbaikan:** `getProfile`, `getSessionProfile`, `listProducts`, `getEntryOptions`
   dibungkus `React.cache`; `decisions.getProfile` kini re-export dari `dashboard`;
   notifikasi dimulai sejajar profil di layout; Input dan Produk Bulanan menjadi 2 gelombang.
5. **API:** satu proses uvicorn; YAML konfigurasi di-parse ulang tiap permintaan (termasuk
   di `/notifications`); tanpa `statement_timeout`. **Perbaikan:** `--workers 2`
   (pembatas laju publik per proses → batas efektif ×2, diterima untuk peragaan),
   `services/config_cache.load_yaml` berkunci `(path, mtime_ns)` dengan salinan dalam —
   dipakai risk_engine, patrol_plan, warning_issuance, citizen_advisory, monthly_*,
   public_intake; `connect_args statement_timeout=30000`.

Belum dikerjakan dari daftar audit (paket berikutnya): streaming panel lambat dengan
`<Suspense>`, pengurangan muatan 200 baris + filter di server, Peta 2 gelombang,
penggabungan kueri dashboard/leadership, indeks `crime_incidents.incident_date`, cache hak
akses per peran, ORJSON. Keamanan (paket dua): pembatas login, penegakan ganti sandi, audit
append-only, audit pembacaan sensitif. Dokumen (paket tiga): docs/12 §3–§4, modul.html,
docs/11, docs/15, docs/09.

## Uji

Web: biome, tsc, 423 test vitest (5 baru di `lib/token.test.ts`), `next build` lulus.
API: ruff, mypy bersih untuk berkas yang disentuh (4 galat mypy tersisa di
`notifications.py` sudah ada sebelumnya). Suite API di basis data pengembangan server ini
memuat kegagalan seed data dummy yang sama sebelum dan sesudah perubahan (grid dummy tidak
ada pada master lokasi data asli); CI pada PostGIS bersih yang menjadi acuan.
Verifikasi pasca-deploy: jumlah `POST /auth/refresh` dan 401 di log API harus turun drastis,
dan galat `Cookies can only be modified` tidak muncul lagi.
