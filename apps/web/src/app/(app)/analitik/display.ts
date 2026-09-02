/**
 * Pembantu tampilan layar Crime Analytics — murni, tanpa pemanggilan API.
 *
 * Dipisahkan dari `lib/analytics.ts` dengan sengaja: modul itu memanggil `lib/api.ts`, yang
 * membaca cookie sesi dan hanya hidup di server. Semua yang ada di sini adalah pemilihan,
 * pemformatan, dan penskalaan gambar, sehingga dapat diuji tanpa jaringan maupun sesi.
 *
 * **Tidak ada satu pun fungsi di sini yang menghitung ulang angka.** Jumlah, persentase,
 * rata-rata, dan puncak datang jadi dari backend. Yang dihitung di sini hanya panjang
 * batang dan tingkat warna — keduanya perkara gambar, bukan perkara analisis.
 *
 * Empat pembantu dipakai ulang dari layar Crime Pattern DNA (`../pola/dna`): nama jenis
 * gangguan, panjang batang, kalimat persentase, dan tanggal ringkas. Menyalinnya akan
 * membuat dua layar yang membaca data sama menampilkan nama dan pembulatan berbeda.
 */
export { barWidth, formatDate, shareText, threatLabel } from "../pola/dna";

/** Keadaan layar yang hidup di URL, bukan di state klien. */
export type AnalyticsSelection = {
  /** Jenis gangguan untuk tren dan matriks waktu; `null` berarti seluruh jenis. */
  threatType: string | null;
  dateFrom: string | null;
  dateTo: string | null;
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Membaca keadaan layar dari parameter alamat.
 *
 * Tanggal yang tidak berbentuk `YYYY-MM-DD` diabaikan, bukan diteruskan ke backend:
 * tautan usang atau salah ketik tidak boleh menjatuhkan seluruh halaman ke layar galat di
 * tengah paparan. Jenis gangguan tetap diteruskan apa adanya — backend yang memiliki
 * daftar jenis dalam cakupan pengguna, dan ia menjawab 400 beserta daftarnya.
 */
export function readSelection(
  params: Record<string, string | string[] | undefined>,
): AnalyticsSelection {
  const text = (value: string | string[] | undefined): string | null =>
    typeof value === "string" && value.trim() !== "" ? value.trim() : null;
  const isoDate = (value: string | string[] | undefined): string | null => {
    const candidate = text(value);
    return candidate && ISO_DATE.test(candidate) ? candidate : null;
  };

  return {
    threatType: text(params.jenis)?.toUpperCase() ?? null,
    dateFrom: isoDate(params.dari),
    dateTo: isoDate(params.sampai),
  };
}

/**
 * Apakah rentang tanggalnya terbalik.
 *
 * Diperiksa di layar supaya pengguna menerima kalimat yang dapat ditindaklanjuti, bukan
 * layar galat. Backend tetap memeriksanya sendiri dan menjawab 400 — pemeriksaan di sini
 * bukan penggantinya (CLAUDE.md §21).
 */
export function isReversedRange(selection: AnalyticsSelection): boolean {
  return (
    selection.dateFrom !== null &&
    selection.dateTo !== null &&
    selection.dateFrom > selection.dateTo
  );
}

/** Tautan ke satu keadaan layar, supaya dapat disalin dan dibagikan saat paparan. */
export function analyticsHref(
  current: AnalyticsSelection,
  change: Partial<AnalyticsSelection>,
): string {
  const next = { ...current, ...change };
  const params = new URLSearchParams();
  if (next.threatType) params.set("jenis", next.threatType);
  if (next.dateFrom) params.set("dari", next.dateFrom);
  if (next.dateTo) params.set("sampai", next.dateTo);

  const suffix = params.toString();
  return suffix ? `/analitik?${suffix}` : "/analitik";
}

/** Memilih jenis yang sedang aktif berarti kembali ke seluruh jenis. */
export function toggledThreatType(current: string | null, value: string): string | null {
  return current === value ? null : value;
}

/**
 * Warna deret, dipakai konsisten antara grafik tren dan batang perbandingan wilayah.
 *
 * Ditulis sebagai warna, bukan sebagai kelas Tailwind, karena jumlah dan nama jenis
 * gangguan berasal dari data: kelas yang dirangkai saat berjalan tidak akan pernah ikut
 * terbangun. Sama seperti `components/dashboard/trend-chart.tsx`.
 */
export const SERIES_COLORS = [
  "#38bdf8",
  "#4ade80",
  "#fbbf24",
  "#f87171",
  "#a78bfa",
  "#22d3ee",
] as const;

export function seriesColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length];
}

/**
 * Kelas warna sel matriks waktu, ditulis utuh.
 *
 * Enam tingkat, bukan gradasi bebas: Tailwind memindai kode sumber sebagai teks, sehingga
 * kelas yang dirangkai saat berjalan (`bg-accent-deep/${x}`) tidak akan pernah terbangun.
 * Indeks 0 khusus untuk sel tanpa kejadian — ia harus terlihat berbeda dari sel yang
 * berisi sedikit kejadian.
 */
export const HEAT_CLASSES = [
  "bg-base-800",
  "bg-accent-deep/25",
  "bg-accent-deep/45",
  "bg-accent-deep/65",
  "bg-accent-deep/85",
  "bg-accent-deep",
] as const;

/**
 * Tingkat warna satu sel, **relatif terhadap sel terbanyak** — bukan terhadap ambang.
 *
 * Tidak ada ambang "rawan" yang ditetapkan siapa pun (CLAUDE.md §11), sehingga skala ini
 * murni perkara keterbacaan gambar: lima tingkat yang membagi rentang 0 sampai puncak.
 * Karena itu layar wajib menyatakan berapa kejadian yang diwakili tingkat tertinggi, dan
 * setiap sel tetap membawa angkanya sendiri.
 */
export function heatLevel(incidents: number, peak: number): number {
  if (incidents <= 0 || peak <= 0) return 0;
  const level = Math.ceil((incidents / peak) * (HEAT_CLASSES.length - 1));
  return Math.min(Math.max(level, 1), HEAT_CLASSES.length - 1);
}

/**
 * Label sumbu bulan yang cukup jarang untuk tetap terbaca.
 *
 * Sumbu tiga tahun berisi 36 bulan; menuliskan seluruhnya membuat teksnya bertumpuk.
 * Yang ditampilkan hanya tiap kelipatan `every`, dengan bulan terakhir selalu ikut supaya
 * ujung sumbu tidak menggantung tanpa keterangan.
 */
export function monthTicks(count: number, every: number): number[] {
  if (count <= 0) return [];
  const ticks = [];
  for (let index = 0; index < count; index += Math.max(every, 1)) ticks.push(index);
  if (ticks[ticks.length - 1] !== count - 1) ticks.push(count - 1);
  return ticks;
}

/**
 * Titik-titik satu deret sebagai path SVG.
 *
 * Digambar sendiri, bukan dengan pustaka grafik: satu grafik garis tidak sepadan dengan
 * menambah dependensi, dan paparan harus berjalan tanpa mengunduh apa pun.
 */
export function linePath(values: number[], peak: number, width: number, height: number): string {
  if (values.length === 0) return "";
  if (values.length === 1)
    return `M0,${height.toFixed(1)} L${width.toFixed(1)},${height.toFixed(1)}`;

  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = peak === 0 ? height : height - (value / peak) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

/** Nilai terbesar pada sekumpulan deret — dasar penskalaan grafik tren. */
export function peakOfSeries(series: { monthly: number[] }[]): number {
  return series.reduce(
    (peak, row) => row.monthly.reduce((inner, value) => Math.max(inner, value), peak),
    0,
  );
}

/** Angka desimal dengan koma sesuai kaidah Bahasa Indonesia. */
export function decimalText(value: number): string {
  return value.toFixed(1).replace(".", ",");
}
