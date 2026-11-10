# 177 — Alur /ops diringkas: produk bulanan dua tahap, Kasat dibekukan, beranda bulanan (10 November 2026)

> **Status:** keputusan pemilik proyek 10 November 2026 atas analisis birokrasi /ops.
> Pertanyaan: "untuk paparan/prototipe alur OPS terlalu panjang birokrasinya, misal tambahan
> Kasat". Jawaban: **1B**, **2 i ii iii**.

## Temuan yang mendasari

| # | Yang menumpuk | Bukti di kode sebelum perubahan |
|---|---|---|
| 1 | Produk bulanan 6 status, 7 klik, 4 peran | `DRAFT → ANALYST_REVIEWED → KBO_CHECKED → VALIDATED → DECIDED`; Kasat mengeklik dua kali berturut-turut (`/kbo`, `/kasat`) pada naskah yang sama; Analis dua langkah (susun, periksa) ditambah pembekuan peringkat di layar lain |
| 2 | Tiga rantai persetujuan sejajar | siklus bulanan; rantai harian (prediksi → peringatan → rekomendasi → keputusan komandan) masih mengisi beranda; Rencana Patroli punya `APPROVED/MODIFIED` sendiri |
| 3 | Tiga antrean sisi warga | buletin mingguan, imbauan bulanan, moderasi survey — masing-masing panel/layar |
| 4 | Enam peran, dua kembar | Fungsi = Polsek (mencatat kegiatan, beda cakupan); Analis dan Kasat sama-sama Satintelkam |

## Keputusan dan pelaksanaannya

### 1B — Produk bulanan dua tahap; Kasat Intelkam dibekukan

```
Analis: Susun (membekukan peringkat bulan itu) → periksa tiap usulan → Kirim ke Pimpinan
Pimpinan: tetapkan jumlah dan kelurahan prioritas (lampiran perkiraan ikut ditetapkan)
Fungsi / Polsek: catat kegiatan
```

- `services/monthly_product.draft`: bila peringkat bulan sasaran belum dibekukan, `compute`
  + `freeze` dipanggil di dalam draf (`facts.ranking_frozen_by_draft`); router mencatat audit
  `FREEZE_RANKING` dengan `by: draft` supaya jejaknya sama dengan pembekuan manual. Pembekuan
  manual di layar Peringkat tetap ada.
- `kbo_check` dan `validate` beserta endpoint `/kbo` dan `/kasat` dihapus. `decide` menerima
  `ANALYST_REVIEWED` **dan** `KBO_CHECKED`/`VALIDATED` (tinggalan) — produk yang tertahan di
  tahap lama tidak terkunci (test `test_product_left_in_a_retired_status_can_still_be_decided`).
  `as_dict` menambah `awaiting_decision`; `next_stage` untuk ketiganya = `PIMPINAN`.
- Konstanta `STATUSES`/`STAGES` model dan check constraint `monthly_stage_allowed` tidak
  diubah: baris lama tetap sah.
- RBAC: `monthly_product: [read, draft, decide, execute]`; peran Kasat Intelkam dihapus dari
  `permissions.yaml`, `roles.csv`; `users.csv` memindahkan `demo.kasat` ke ROLE-03 (pola yang
  sama dengan `demo.commandcenter`/`demo.analyst` yang dipindah ke Administrator).
- Migrasi **0023**: cabut + hapus permission `review`/`validate`; kunci `demo.kasat`
  (`password_hash='!'`, `INACTIVE`) — bukan dihapus, jejak audit merujuk padanya; pindahkan
  pemegang peran Kasat ke Analis Intelkam lalu hapus peran (FK RESTRICT menolak menghapus peran
  yang masih dipakai). Downgrade memulihkan peran, permission, dan hak.
- `scripts/sandi-peragaan-produksi.sh`: lima akun. docs/03 dibangkitkan ulang
  (`scripts/matriks-rbac.py --tulis`): Pimpinan 31, Analis Intelkam 19, Fungsi 20, Polsek 31,
  Administrator 56.
- Web: `produk-bulanan` tiga pil tahap (Analis menyusun & memeriksa · Pimpinan menetapkan ·
  Pelaksanaan dicatat); tombol "Susun draf (membekukan peringkat)" dan "Kirim ke Pimpinan";
  `OutcomeForm` dihapus. Lencana sidebar menghitung `AWAITING_DECISION` (tiga status).

### 2.i — Beranda menjadi papan "Bulan ini"

`components/monthly/board.tsx` (`buildCards` murni, dapat diuji tanpa render): kartu produk
bulanan (posisi naskah + giliran siapa), kegiatan di kelurahan prioritas, evaluasi cakupan,
persetujuan warga. Kartu yang menunggu pembaca berbingkai aksen; judul papan menyebut
"N menunggu Anda". Peta tetap isi utama. Sorotan harian, "yang menonjol", dan panel terlipat
(peringatan dini, prediksi, rekomendasi, tren) keluar dari beranda — komponennya tidak dihapus
dan layarnya tetap di alamat lama. Bulan yang dipapankan = produk terbaru, atau bulan yang
disarankan API bila belum ada produk.

### 2.ii — Rencana Patroli dilebur

`/ops/rencana-patroli` keluar dari menu (`screens.test.tsx`: masuk daftar `keptOffMenu`) dan
`canDecide={false}` — tidak ada formulir persetujuan tersendiri lagi. Produk Bulanan memuat
panel **Lampiran: perkiraan jam rawan {bulan}** dari `GET /patrol-plan/outlook?month=` (JSON),
disaring ke kelurahan dalam draf (atau kelurahan prioritas setelah ditetapkan), dengan tautan
unduh .docx (`/api/perkiraan?bulan=`). Endpoint keputusan rencana patroli tidak dihapus
(keputusan yang sudah tercatat tetap terbaca di brief), hanya tidak lagi dipanggil dari UI.

### 2.iii — Satu antrean persetujuan warga

`/ops/buletin`: panel **Menunggu persetujuan** memuat seluruh buletin `DRAFT` lintas minggu,
masing-masing dengan tombol setujui; panel **Susun Buletin** (Administrator) tetap; **Riwayat**
per minggu hanya yang disetujui/terkirim.

**Revisi di hari yang sama — imbauan bulanan otomatis, perintah `/info`.** Pemilik proyek
mencabut 3A: imbauan ke grup WhatsApp warga tidak lagi menunggu persetujuan Pimpinan.
`GET /messaging/advisory` dan `/messaging/advisories/pending` tidak lagi memeriksa
`advisory_approvals` (tabel 0022 dibiarkan, tidak dibaca); endpoint `/advisories/approvals`
dihapus, diganti `GET /advisories/preview` (contoh teks, grup terdaftar, grup yang sudah
menerima) untuk panel pratinjau di `/ops/buletin`. Bot: `COMMAND_ADVISORY` dipimpin `/info`;
`/rekomendasi` dan `/imbauan` tetap dikenali supaya pesan pengenalan lama tidak mati. Kartu
"Persetujuan warga" di beranda hanya menghitung buletin draf.

## Yang sengaja tidak diubah

- Rantai harian (peringatan, rekomendasi, keputusan komandan, operasi) dan datanya.
- Endpoint `POST /patrol-plan/decisions`.
- Moderasi Survey Rasa Aman (tetap Administrator, layar sendiri).
- Rute `/ops/rencana-patroli` dan rute harian lain (tautan lama).

## Verifikasi

- API: `pytest` berkas produk bulanan, evaluasi bulanan, peringkat, RBAC — lulus. Suite penuh
  pada DB pengembangan lokal: **tidak ada test yang gagal hanya di branch ini** (77 kegagalan
  yang sama sudah ada di `main` pada DB yang sama — data sample/`police_units` tidak dimuat
  lokal; `test_seeding_master` menghitung 11 pengguna karena tiga akun `uji.smoke.*` tertinggal).
- Web: `tsc --noEmit`, `biome check`, `vitest run` (421 test), `next build` — lulus.
- Migrasi 0023 diterapkan ke DB lokal: lima peran, `demo.kasat` INACTIVE di Analis Intelkam,
  permission produk bulanan tinggal `read/draft/decide/execute`.

## Produksi

Deploy biasa (`scripts/deploy-produksi.sh`) menjalankan `alembic upgrade head` → 0023 mengunci
`demo.kasat` dan menghapus perannya. Baris `demo.kasat` di `~/siintel-demo-passwords.txt`
tidak lagi berlaku; jalankan ulang `scripts/sandi-peragaan-produksi.sh` bila berkas itu ingin
dirapikan (kini lima akun).
