# 173 — SIGAP WARGA: rencana perombakan sisi masyarakat (2 November 2026)

Keputusan pemilik proyek tercatat di docs/01 §19.2 (baris "SIGAP WARGA"). Catatan ini
menuliskan tahapannya supaya setiap tahap satu perubahan koheren (CLAUDE.md §7).

## Dua wajah, satu domain

```text
sigap.awansurya.com/           SIGAP WARGA — publik, tanpa akun, mode terang
sigap.awansurya.com/ops/...    SIGAP — Pimpinan/Administrator/Polsek/Fungsi (yang ada sekarang)
```

Jalur `/ops` dipilih atas subdomain karena: satu sertifikat dan satu blok nginx (mesin depan
tidak dapat dihubungi dari sini), satu deploy, dan middleware yang sudah memisahkan publik
dari aplikasi tinggal dipindahkan awalannya. Yang harus dijaga: cookie sesi dibatasi
`Path=/ops`, tautan internal diprefiks, Android petugas menunjuk `/api/v1` yang tidak berubah.

## Tahap 1 — dasbor warga (data sudah ada)

- Halaman muka baru: imbauan berlaku, peta wilayah (kecamatan → kelurahan) dengan jumlah
  3C historis per bulan dan tingkat kerawanan kasar (rendah/sedang/tinggi dari kuantil
  kejadian historis — bukan dari prediksi), Lapor, Darurat, Survey Rasa Aman.
- API publik baru `GET /public/areas/summary` — agregat historis per kelurahan (12 bulan
  terakhir sampai batas tampilan), tanpa koordinat kejadian.
- Survey Rasa Aman: tabel `area_reviews` (kelurahan, nilai 1–5, komentar ≤300, status
  PENDING/PUBLISHED/REJECTED, pembatas laju per alamat), moderasi di `/ops/survey`
  (`review:moderate` — Administrator; Binmas lewat peran Fungsi menunggu keputusan RBAC),
  nilai rata-rata dihitung dari yang tayang.

## Tahap 2 — berkas perkara (data dummy berlabel)

- Entitas `case_files`: nomor LP, jenis 3C, tahap (SP2HP: Lidik/Sidik/P21/SP3/Selesai),
  plat, nomor rangka/mesin, kelurahan, kontak pelapor (hash), `is_dummy`.
- `GET /public/cases/track` (nomor LP + 4 digit terakhir telepon pelapor) → tahap + riwayat.
- `GET /public/vehicles/check` (plat atau nomor rangka) → hanya "tercatat/tidak" + saran.
- Operator (`case_file:write`, Administrator/Reskrim) mengelola di `/ops/perkara`.
- Label **DUMMY** tampil di setiap hasil selama datanya sintetis.

## Tahap 3 — kontak Babinkamtibmas dan buletin kelurahan

- Entitas `babinkamtibmas` (kelurahan, polsek, nama, nomor dinas, tautan grup, `is_dummy`),
  CRUD di `/ops/babin`, ditampilkan di bot (menu "Kontak Babin") dan dasbor warga.
- Buletin mingguan per kelurahan: disusun sistem (kejadian + rekomendasi minggu lalu),
  **disetujui** di `/ops` sebelum terkirim; bot Telegram mengirim ke grup kelurahan,
  WhatsApp perorangan ke nomor Babin (API resmi tidak menjangkau grup).
- Menu bot: tautan dasbor warga.

## Tema

Dasbor warga memakai tema sendiri, terang sebagai bawaan; arah visual ditentukan pemilik
proyek dari refero.design. Komponen sisi polisi tidak dipakai ulang di sisi warga.
