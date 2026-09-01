# TASK 020 — SEED MASTER DATA

Tanggal: 2026-09-01
Status: **SELESAI — dimuat ke PostgreSQL 17.5 dan diverifikasi.**

Awal PHASE 3. Task ini membangun **kerangka seed** sekaligus memuat master data.

| Tabel | Jumlah | Sumber |
|---|---:|---|
| `locations` | 33 | `data/sample/locations.csv` |
| `police_units` | 6 | `data/sample/police_units.csv` |
| `roles` | 6 | `data/sample/roles.csv` |
| `permissions` | 43 | `config/rbac/permissions.yaml` |
| `role_permissions` | 146 | `config/rbac/permissions.yaml` |
| `users` | 6 | `data/sample/users.csv` |

---

## 1. KEPUTUSAN

| # | Keputusan | Alasan |
|---|---|---|
| 1 | **Password akun demo dikunci** (`!`, konvensi berkas shadow), `must_change_password = true` | Kredensial nyata adalah lingkup TASK 050. Menanam kata sandi yang dapat ditebak ke dalam sistem kepolisian — meskipun "hanya demo" — adalah kebiasaan yang tidak layak dimulai. Login memang belum berfungsi sampai TASK 050 |
| 2 | **`permissions` diambil dari `config/rbac/`, bukan dari `data/sample/permissions.csv`** | Dataset dummy hanya memuat 12 permission tanpa `scope`, sedangkan model otorisasi `docs/03` §2 memuat 43 permission + scope. Ini sudah diantisipasi di `docs/03` §5 |
| 3 | **Nilai taksonomi dipetakan lewat `config/taxonomy/mappings.yaml`** | U-16 belum dijawab; pemetaan di konfigurasi dapat diubah tanpa menyentuh kode maupun migration |
| 4 | **Nilai taksonomi yang tidak dikenal menghentikan seed** | Nilai asing yang diterima diam-diam akan menjadi taksonomi bayangan yang tidak pernah disetujui siapa pun |
| 5 | **Seed idempoten**, berbasis kolom `code` | Menjalankan ulang tidak menggandakan baris; aman dipakai berkali-kali selama pengembangan |
| 6 | **Satu transaksi per perintah** | Satu baris bermasalah membatalkan seluruh seed — tidak ada database setengah terisi |
| 7 | `users.polsek` dan `users.function` diisi nilai demo | Dataset dummy tidak memuat kolom ini, padahal tanpa keduanya scope `OWN_JURISDICTION`/`OWN_FUNCTION` tidak dapat diuji sama sekali. Nilainya sintetis dan ditandai demikian di kode |
| 8 | `roles.level` `"Level 1"` → `1` | Kolomnya `smallint` dengan CHECK 1–6 (docs/02 §16) |
| 9 | Waktu sumber dianggap **WIB** lalu dinormalkan ke UTC | Dataset tidak memuat offset; docs/02 K-3 menetapkan penyimpanan UTC |
| 10 | Kode seed berada **di dalam paket API**, bukan script lepas | Ikut tercakup ruff, mypy, dan pytest. `scripts/seed/` menyimpan dokumentasinya |

---

## 2. BUG YANG DITEMUKAN SAAT PENGERJAAN

`paths.py` semula menghitung akar repository dengan `parents[4]` — meniru `config.py` yang berada
satu tingkat lebih dangkal. Akibatnya seed mencari `apps/config/taxonomy/` dan langsung gagal.

Diperbaiki dengan mencari akar lewat **penanda** (`pnpm-workspace.yaml` + `CLAUDE.md`), bukan
menghitung level, sehingga tidak diam-diam salah lagi bila berkas dipindahkan.

Selain itu dua integration test lama gagal setelah seed berjalan: keduanya menyisipkan permission
`crime:read`/`crime:write` yang kini sudah ada, sehingga menabrak `uq_permissions_resource_action`.
Fixture-nya diganti memakai resource khusus uji. Ini bentrokan fixture, bukan cacat produk.

---

## 3. VERIFIKASI YANG BENAR-BENAR DIJALANKAN

```text
pnpm seed:master (pertama)
  locations         +33     permissions       +43
  police_units      +6      role_permissions  +146
  roles             +6      users             +6

pnpm seed:master (kedua — idempoten)
  seluruh tabel +0

Sebaran scope pemberian permission:
  role_name        ALL   OWN_JURISDICTION   OWN_FUNCTION
  Administrator     27          0                0
  Analyst           28          0                0
  Command Center    26          0                0
  Fungsi             6          0               15
  Pimpinan          21          0                0
  Polsek             1         22                0

ruff check + format (47 berkas) → bersih
mypy (40 berkas)                → no issues
pytest tanpa DATABASE_URL       → 118 lulus, 35 dilewati
pytest dengan DATABASE_URL      → 153 lulus
```

Test baru:

| Test | Menjaga |
|---|---|
| `test_every_dataset_value_is_mappable` | Setiap nilai taksonomi pada **seluruh** CSV punya pemetaan — kekurangan pemetaan ketahuan sekarang, bukan saat seed tahap berikutnya |
| `test_unknown_value_stops_the_seed` | Nilai asing tidak diterima diam-diam |
| `test_datetime_is_normalised_to_utc_from_both_formats` | Dua gaya penulisan waktu menghasilkan nilai yang sama |
| `test_demo_accounts_cannot_be_used_to_log_in` | Akun demo tetap terkunci |
| `test_audit_permission_has_no_write_action` | Audit tetap append-only sampai ke katalog permission |
| `test_master_seed_is_idempotent` | Menjalankan ulang tidak menggandakan data |

---

## 4. YANG BELUM DIKERJAKAN

- Acceptance criteria A-1…A-12 (`docs/08` PHASE 3) baru tersentuh sebagian; sisanya menyusul
  bersama data yang relevan (TASK 021–024).
- Matriks pemberian permission masih `PROPOSED` sampai P-1…P-7 (`docs/03` §4) dijawab.
- Pemetaan taksonomi berstatus `proposed-2026-09-01` sampai B-3 dijawab.

## 5. TASK BERIKUTNYA

**TASK 021 — Seed Crime Data**: `crime_incidents` (1.200), `intelligence_reports` (120),
`patrol_activity` (180).

Di sanalah acceptance **A-2** (setiap `grid_id` terpetakan ke `location_id`) dan **A-11**
(normalisasi waktu) benar-benar diuji pada volume data.
