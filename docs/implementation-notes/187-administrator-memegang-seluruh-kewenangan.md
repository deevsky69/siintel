# 187 — Administrator memegang seluruh kewenangan (19 November 2026)

**USER DECISION.** Pemilik proyek, 19 November 2026: "untuk seluruh privilege yang dimiliki
akun lain, baik pimpinan, humas, fungsi dll harus bisa dilakukan oleh admin."

## Yang berubah

Administrator sebelumnya memegang 55 dari 64 permission. Sembilan sisanya kini diberikan
(cakupan ALL), lewat `config/rbac/permissions.yaml` dan migrasi **0030**:

| Permission | Pemegang lain | Dahulu dijauhkan dari Administrator karena |
|---|---|---|
| `monthly_product:draft` | Analis Intelkam | rantai tidak boleh dilewati lewat akun admin (catatan 183) |
| `monthly_product:review` | KBO | idem (catatan 186) |
| `monthly_product:validate` | Kasat Intelkam | idem |
| `monthly_product:decide` | Pimpinan | penetapan adalah keputusan komando (catatan 176) |
| `monthly_product:execute` | Fungsi, Polsek | pelaksanaan dicatat pelaksananya |
| `bulletin:approve` | Pimpinan | penerbitan ke masyarakat (2 November 2026) |
| `public_info:approve` | Humas | informasi publik disetujui Humas (catatan 186) |
| `public_alert:publish` | Pimpinan | U-10, keputusan 9 September 2026 |
| `evaluation:run` | Pimpinan | yang menghasilkan angka tidak menilainya (1 September 2026) |

Tidak ada perubahan tabel, endpoint, atau layar: seluruh pemeriksaan sudah berbasis
permission, sehingga tombol peran lain otomatis tampil pada akun Administrator. Peran lain
tidak berubah.

## Yang TIDAK berubah

- **Urutan tahap** produk bulanan tetap ditegakkan layanan (draf → analis → KBO → Kasat →
  Pimpinan → pelaksanaan); Administrator tidak dapat melompati tahap, hanya dapat menjalankan
  semuanya.
- **Jejak audit** dan riwayat tahap tetap mencatat akun pelaku setiap langkah.
- Peran sendiri tetap tidak dapat diubah oleh akunnya sendiri (`administration.py`).

## Akibat yang perlu diketahui

1. Lewat akun Administrator **satu orang dapat menyusun, memeriksa, menelaah, dan menetapkan**
   produk bulanan, menyetujui imbauan dan buletin, menerbitkan peringatan publik, dan
   menjalankan evaluasi atas angka yang dihasilkannya sendiri. Pemisahan tugas kini hanya
   ditegakkan antarperan selain Administrator.
2. **Berbeda dari naskah Taskap final** (Bab IV B.4.4, Lampiran 9 D, Tabel 24), yang
   menyatakan keempat hak dipegang empat peran dan informasi publik disetujui Humas. Bila
   penguji bertanya, jawabannya: pemisahan berlaku untuk peran operasional; Administrator
   adalah akun pengelola yang seluruh tindakannya tercatat di Audit Log.
3. Notifikasi lonceng Administrator kini memuat antrean produk bulanan.

## Test

`test_rbac_separation_of_duties.py` ditulis ulang: Administrator memegang seluruh katalog
(dijaga dua arah), dan di antara peran LAIN pemisahan lama tetap berlaku. Enam test API yang
memakai Administrator sebagai contoh penolakan kini memakai peran yang memang tidak berwenang;
ditambah `test_administrator_can_run_every_stage_of_the_chain`. Seluruh test API lulus pada
basis data sementara berisi data contoh; migrasi 0030 naik-turun; web `vitest` 430 lulus.

## Cara membalik

`alembic downgrade 0029`, hapus sembilan baris pada blok Administrator di
`config/rbac/permissions.yaml`, dan kembalikan test.
