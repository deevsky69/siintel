# 201 — Keterangan ringkas di atas tabel rekap Polda (25 November 2026)

**USER DECISION.** Pemilik proyek, 25 November 2026: penjelasan atribut tabel (CT, CC, dan
seterusnya) dibuat ringkas dalam bentuk butir, dan tidak ditaruh di bawah.

- Komponen `Keterangan` pada `/ops/polda`: butir pendek CT, CC, CR, 3C, Perubahan (atau, pada
  halaman satu Polres, "3C dari keseluruhan" dan "Porsi 3C Polda"), tanda *, dan Sumber —
  ditaruh di atas tabel.
- Dihapus: panel "Dasar angka" di kaki halaman, paragraf catatan kaki di bawah ringkasan, dan
  kalimat penutup di bawah peta kecamatan. Keterangan peta dipendekkan; atribusi sumber peta
  tetap ada karena diwajibkan lisensinya.
- Butir "Sumber" tetap menyebut bahwa ini rekap per satuan, bukan data per kejadian. Field
  `basis` pada API tidak berubah.

**Verifikasi.** Web `tsc`, `biome`, `vitest` 441 lulus, `next build`; kedua tampilan diperiksa
lewat potret pada salinan lokal.
