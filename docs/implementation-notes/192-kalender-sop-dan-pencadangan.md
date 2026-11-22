# 192 — Kalender SOP, rekap triwulan, dan pencadangan terjadwal (22 November 2026)

**USER DECISION.** Pemilik proyek, 22 November 2026: "sesuaikan juga perbedaan yang masih
tersisa antara naskah dan aplikasi." Yang tersisa menurut catatan 190–191:

| Perbedaan | Penyelesaian |
|---|---|
| Ketentuan berjadwal SOP (Lampiran I) hanya ditampilkan, tidak dijalankan | **Kalender SOP** (migrasi 0034) + rekap triwulan + skrip cadangan harian |
| Lampiran K huruf F menyebut "usulan kecocokan AI"; di aplikasi aturan tertulis | **salinan naskah** diubah menjadi "usulan kecocokan dari aturan tertulis" (perubahan terlacak) — aplikasi tidak diubah, karena menyebut aturan sebagai AI melanggar CLAUDE.md §27 |
| Pencocokan dengan nomor laporan, ciri objek, uraian | **bukan perbedaan**: rincian itu tidak ada di naskah revisi (ralat pada catatan 190) |
| Luas kelurahan untuk PAI masih perkiraan | dibiarkan atas keputusan pemilik proyek (pilihan 1); kalimat keterangan sudah ada di salinan naskah Bab III |
| Uji 4 dan 8 kelurahan, skenario tetap | salinan naskah sudah memakai angka aplikasi (catatan 190 bagian 4) |

## Kalender SOP

`GET /sop/calendar`, `POST /sop/calendar/{period}/{item}`; tabel `sop_checks` (satu baris per
periode dan butir). Delapan butir dari Lampiran I:

| Butir | Sumber | Pencatat (izin) |
|---|---|---|
| Data diterima paling lambat tanggal 5 | dicatat | KBO (`monthly_product:review`) |
| Data kosong, ganda, bertentangan diperiksa | dicatat | KBO |
| Peta, IKW, peringkat terbit | **sistem**: peringkat bulan itu dibekukan | — |
| Draf diperiksa berjenjang | **sistem**: produk berstatus VALIDATED/DECIDED | — |
| Evaluasi awal bulan; mutu draf, waktu kerja dicatat | dicatat | KBO |
| Catatan akses diperiksa tiap bulan | dicatat | pemegang `audit:read` |
| Pencadangan terjadwal diperiksa | dicatat | pemegang `audit:read` |
| Laporan triwulan kepada Kapolres | dicatat | Kasat Intelkam (`monthly_product:validate`) |

**Mengapa dicatat, bukan dinilai.** Aplikasi tidak dapat mengetahui kapan sebuah Polsek
mengirim berkas atau apakah seseorang benar-benar membaca Audit Log, dan jam acuan purwarupa
dikunci (mode demo) sehingga "terlambat" tidak dapat dihitung dengan jujur. Yang disimpan
adalah pernyataan pejabat berwenang — siapa, kapan, catatannya — dan jejak auditnya. Di samping
tiap butir tampil fakta sistem (tanggal data terakhir dimuat, jumlah catatan audit bulan itu
dan yang ditolak, status produk) supaya pencatat membaca angka yang sama dengan yang tersimpan.

**Rekap triwulan** (Lampiran L huruf D): median skor mutu draf SIGAP dan cara kerja biasa, serta
median menit dari data siap olah sampai validasi, atas produk bulanan triwulan itu yang punya
catatan pada Evaluasi.

Tidak ada pencabutan catatan dari layar; satu butir satu kali per periode.

## Pencadangan terjadwal

`infra/cadangan-harian.sh`: `pg_dump` basis data produksi ke
`~/siintel-cadangan-harian/sigap-YYYYMMDD.sql.gz` (mode 600), ditulis ke berkas sementara lalu
diuji `gzip -t` sebelum menggantikan; menghapus hanya berkas buatannya sendiri yang lebih tua
dari 14 hari. Dijalankan lewat crontab pengguna di server; pemasangannya memerlukan izin
pemilik proyek (operasi produksi).

## Verifikasi

Seluruh test API lulus pada basis data sementara berisi data contoh (tiga test baru Kalender
SOP: daftar butir dan fakta, pencatat yang berwenang dan satu kali per periode, butir sistem
tidak dapat dicentang); migrasi 0034 naik-turun; web `tsc`, `biome`, `vitest` 437 lulus,
`next build`; kalender diperiksa lewat potret pada salinan lokal sebagai akun KBO.
