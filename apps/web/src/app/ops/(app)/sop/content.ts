/**
 * Muatan dan desain SOP menurut naskah Taskap revisi — Gambar 4.3, Tabel 4.17, Lampiran I.
 * Dipisahkan dari `page.tsx` karena berkas halaman Next hanya boleh mengekspor komponennya;
 * dengan begitu `sop.test.ts` dapat mengunci teksnya kata demi kata.
 */

type Modul = { no: string; nama: string; sop: string; layar: { href: string; label: string }[] };

export const SUMBER_DATA = [
  "Pusiknas Bareskrim Polri",
  "Satreskrim dan SPKT",
  "Polsek jajaran (10)",
  "Bhabinkamtibmas dan informasi warga terverifikasi",
] as const;

export const MODUL: readonly Modul[] = [
  {
    no: "Modul 1",
    nama: "Pembakuan Data",
    sop: "SOP Pengelolaan Data",
    layar: [
      { href: "/ops/pembakuan", label: "Mutu Data" },
      { href: "/ops/laporan-petugas", label: "Laporan Petugas" },
    ],
  },
  {
    no: "Modul 2",
    nama: "Peta dan Indeks Kerawanan Wilayah",
    sop: "SOP Penilaian Kerawanan",
    layar: [
      { href: "/ops/peta", label: "Peta" },
      { href: "/ops/analitik", label: "Analitik" },
      { href: "/ops/peringkat", label: "IKW (Peringkat)" },
    ],
  },
  {
    no: "Modul 3",
    nama: "Prediksi Kelurahan Prioritas (AI)",
    sop: "SOP Prediksi",
    layar: [{ href: "/ops/peringkat", label: "Peringkat 65 Kelurahan" }],
  },
  {
    no: "Modul 4",
    nama: "Draf Rekomendasi dan Validasi",
    sop: "SOP Validasi dan Penyampaian",
    layar: [{ href: "/ops/produk-bulanan", label: "Produk Bulanan" }],
  },
  {
    no: "Modul 5",
    nama: "Evaluasi Ketepatan",
    sop: "SOP Evaluasi",
    layar: [{ href: "/ops/evaluasi-bulanan", label: "Evaluasi" }],
  },
];

export const VALIDASI = [
  "Analis tim inti",
  "KBO Satintelkam",
  "Wakasatintelkam",
  "Kasatintelkam",
  "Kapolres (keputusan)",
] as const;

export const PENGGUNA_PRODUK = ["Bagops", "Satsamapta", "Satbinmas", "Polsek"] as const;

/** Tabel 4.17 — Muatan SOP dan Modul Aplikasi SIGAP. */
export const MUATAN = [
  {
    bagian: "Pengelolaan data",
    modul: "Modul 1 Pembakuan data",
    isi: "Kamus data, format isian minimal, jadwal pengiriman, penanggung jawab, pemeriksaan data kosong dan ganda",
    kelemahan: "W3",
  },
  {
    bagian: "Penilaian kerawanan",
    modul: "Modul 2 Peta dan IKW",
    isi: "Peta kelurahan, profil rentang jam, bobot frekuensi, dampak, dan keberulangan",
    kelemahan: "W5",
  },
  {
    bagian: "Prediksi",
    modul: "Modul 3 Prediksi AI",
    isi: "Peringkat 65 kelurahan untuk bulan berikutnya beserta pembanding historis",
    kelemahan: "W4",
  },
  {
    bagian: "Validasi dan penyampaian",
    modul: "Modul 4 Rekomendasi",
    isi: "Draf rekomendasi, pemeriksaan berjenjang, keputusan pimpinan, dan distribusi",
    kelemahan: "W4",
  },
  {
    bagian: "Evaluasi",
    modul: "Modul 5 Evaluasi",
    isi: "Cakupan kejadian, mutu draf, waktu kerja, dan catatan tindak lanjut",
    kelemahan: "W5",
  },
  {
    bagian: "Keamanan informasi",
    modul: "Dasbor dan hak akses",
    isi: "Hak akses menurut peran, catatan akses, pencadangan, dan anonimisasi data",
    kelemahan: "W3",
  },
] as const;

/** Lampiran I, Tabel I.1 — Ringkasan SOP Deteksi Dini Kejahatan 3C Berbasis Data. */
export const RINGKASAN_SOP = [
  [
    "Tujuan",
    "Menjadi pedoman Satintelkam, Satreskrim, SPKT, dan Polsek dalam mengelola data kejahatan 3C dan menyusun peringatan dini yang dapat ditelusuri dan dievaluasi",
  ],
  [
    "Ruang lingkup",
    "Penerimaan dan pembakuan data, penilaian kerawanan, prediksi, validasi dan penyampaian produk, evaluasi ketepatan, serta keamanan informasi",
  ],
  [
    "Penerimaan data",
    "Setiap fungsi dan Polsek menunjuk penghubung data dan mengirim data kejadian bulan sebelumnya paling lambat tanggal 5 sesuai format isian minimal",
  ],
  [
    "Pembakuan data",
    "KBO memeriksa data kosong, ganda, dan bertentangan melalui modul pembakuan, mencatat koreksi, dan menyimpan versi data",
  ],
  [
    "Penilaian kerawanan",
    "Peta dan Indeks Kerawanan Wilayah 65 kelurahan diterbitkan pada minggu pertama setiap bulan dari unsur frekuensi, dampak, dan keberulangan",
  ],
  [
    "Prediksi",
    "Aplikasi SIGAP mengurutkan 65 kelurahan untuk bulan berikutnya dan menampilkan pembanding historis pada jumlah kelurahan yang sama",
  ],
  [
    "Validasi dan penyampaian",
    "Draf rekomendasi diperiksa analis, KBO, Wakasatintelkam, dan Kasatintelkam sebelum diajukan kepada Kapolres; produk yang disetujui disampaikan kepada fungsi pelaksana dan Polsek",
  ],
  [
    "Evaluasi",
    "Pada awal bulan, pilihan bulan sebelumnya dibandingkan dengan kejadian aktual; mutu draf, waktu kerja, dan tindak lanjut dicatat dan dilaporkan setiap triwulan",
  ],
  [
    "Keamanan informasi",
    "Hak akses diberikan menurut peran, data dianonimkan, catatan akses diperiksa setiap bulan, dan data dicadangkan secara terjadwal",
  ],
] as const;
