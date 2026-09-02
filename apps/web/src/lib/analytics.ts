import { apiGet } from "./api";

/**
 * Crime Analytics (TASK 035) — tren, jam rawan, dan perbandingan antarwilayah.
 *
 * ```text
 * GET /analytics/trend?threat_type=&date_from=&date_to=
 * GET /analytics/time-pattern?threat_type=&date_from=&date_to=
 * GET /analytics/spatial-pattern?date_from=&date_to=
 * ```
 *
 * Bentuk data mengikuti `apps/api/.../routers/analytics.py`. **Tidak ada angka yang
 * dihitung di sini**: seluruh jumlah, persentase, rata-rata, dan puncak berasal dari
 * backend, karena penentuan "apa yang dihitung" adalah aturan analitik dan tempatnya di
 * backend (CLAUDE.md §21).
 *
 * Bedanya dengan Crime Pattern DNA (`lib/patterns.ts`), dan ini yang harus terbaca di
 * layar supaya pengguna tidak mengira keduanya sama:
 *
 * - **Pattern DNA** memprofilkan **satu** jenis gangguan menurut lima dimensi
 *   where–when–how–target–repeat.
 * - **Analytics** membandingkan **antar** jenis, antar bulan, dan antar kecamatan.
 *
 * Keduanya membaca `crime_incidents` lewat agregasi dasar yang sama di backend, sehingga
 * angka yang beririsan — misalnya sebaran jam satu jenis — memang identik.
 *
 * Tiga batas yang dibawa apa adanya dari backend dan tidak boleh dihaluskan:
 *
 * 1. Ini sebaran kejadian yang **sudah terjadi**, bukan prediksi dan bukan skor risiko.
 * 2. **Tidak ada** bulan, sel waktu, atau wilayah yang ditandai "signifikan"; ambangnya
 *    belum ditetapkan siapa pun (CLAUDE.md §11).
 * 3. Perbandingan antarwilayah memakai **jumlah mentah**, bukan angka per penduduk —
 *    lihat `rate_basis`.
 */

/** Jenis gangguan yang ada di dalam cakupan pengguna, beserta jumlahnya. */
export type ThreatTypeCount = { threat_type: string; incidents: number };

/** Asal angka: tabel, rentang tanggal, jumlah baris, dan cakupan wilayahnya. */
export type AnalyticsSource = {
  table: string;
  date_from: string | null;
  date_to: string | null;
  incidents: number;
  /** Polsek pengguna bila cakupannya dibatasi wilayah, `null` bila tidak. */
  scope: string | null;
};

type AnalyticsCommon = {
  incidents: number;
  denominator: number;
  source: AnalyticsSource;
  scope_basis: string;
  analysis_basis: string;
  /** Kaitan dengan Crime Pattern DNA, supaya keduanya tidak tertukar. */
  related_analysis_basis: string;
};

// ---------------------------------------------------------------------------
// Tren per bulan
// ---------------------------------------------------------------------------

/** Satu bulan pada sumbu tren; bulan tanpa kejadian tetap dikirim sebagai nol. */
export type TrendMonth = {
  key: string;
  label: string;
  year: number;
  month: number;
  incidents: number;
  share_percent: number;
};

/** Satu deret jenis gangguan; `monthly` sejajar indeksnya dengan `months`. */
export type TrendSeries = {
  threat_type: string;
  incidents: number;
  share_percent: number;
  monthly: number[];
};

export type TrendResponse = AnalyticsCommon & {
  threat_type: string | null;
  threat_types: ThreatTypeCount[];
  months: TrendMonth[];
  series: TrendSeries[];
  months_counted: number;
  peak_month: { key: string; incidents: number } | null;
  mean_per_month: number;
  /** Penyebut rata-rata: berapa bulan, termasuk bulan tanpa kejadian. */
  mean_basis: string;
  /** Bahwa "bulan terbanyak" adalah maksimum aritmetika, bukan penanda menonjol. */
  peak_basis: string;
};

// ---------------------------------------------------------------------------
// Matriks hari x jam
// ---------------------------------------------------------------------------

export type TimeCell = {
  hour: number;
  label: string;
  incidents: number;
  share_percent: number;
};

export type TimeRow = {
  day: number;
  label: string;
  incidents: number;
  share_percent: number;
  cells: TimeCell[];
};

export type TimePatternResponse = AnalyticsCommon & {
  threat_type: string | null;
  threat_types: ThreatTypeCount[];
  days: TimeRow[];
  /** Total per jam, gabungan seluruh hari — kolom marginal matriks. */
  hours: TimeCell[];
  cells: number;
  peak_cell: {
    day: number;
    day_label: string;
    hour: number;
    label: string;
    incidents: number;
    share_percent: number;
  } | null;
  /** Berapa isi tiap sel bila kejadian tersebar rata — pembanding, bukan ambang. */
  cell_basis: string;
  /** Bahwa jam dihitung dari waktu setempat (WIB), bukan dari UTC. */
  time_basis: string;
};

// ---------------------------------------------------------------------------
// Perbandingan antarwilayah
// ---------------------------------------------------------------------------

/**
 * Satu sel matriks wilayah x jenis, dengan **dua** persentase berbeda penyebut:
 * `share_of_area_percent` terhadap kejadian kecamatannya sendiri (komposisi gangguan di
 * sana), `share_of_threat_percent` terhadap kejadian jenis itu di seluruh cakupan (di mana
 * jenis tersebut terkumpul).
 */
export type SpatialCell = {
  threat_type: string;
  incidents: number;
  share_of_area_percent: number;
  share_of_threat_percent: number;
};

export type SpatialArea = {
  kecamatan: string;
  polsek: string | null;
  incidents: number;
  share_percent: number;
  denominator: number;
  by_threat: SpatialCell[];
};

export type SpatialPatternResponse = AnalyticsCommon & {
  threat_types: { threat_type: string; incidents: number; share_percent: number }[];
  areas: SpatialArea[];
  areas_compared: number;
  /** Penyebut mana untuk persentase yang mana. */
  share_basis: string;
  /** Berapa wilayah yang benar-benar dibandingkan — satu, bila cakupan dibatasi polsek. */
  comparison_basis: string;
  /** Bahwa perbandingan ini jumlah mentah, bukan angka per penduduk. */
  rate_basis: string;
};

// ---------------------------------------------------------------------------
// Pengambilan data
// ---------------------------------------------------------------------------

export type AnalyticsQuery = {
  threatType?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
};

function queryString(query: AnalyticsQuery, withThreatType: boolean): string {
  const params = new URLSearchParams();
  if (withThreatType && query.threatType) params.set("threat_type", query.threatType);
  if (query.dateFrom) params.set("date_from", query.dateFrom);
  if (query.dateTo) params.set("date_to", query.dateTo);
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
}

export function getTrend(query: AnalyticsQuery = {}): Promise<TrendResponse> {
  return apiGet<TrendResponse>(`/analytics/trend${queryString(query, true)}`);
}

export function getTimePattern(query: AnalyticsQuery = {}): Promise<TimePatternResponse> {
  return apiGet<TimePatternResponse>(`/analytics/time-pattern${queryString(query, true)}`);
}

/**
 * Perbandingan antarwilayah **tidak** menerima `threat_type`: seluruh jenis justru menjadi
 * kolom matriksnya. Menyaringnya ke satu jenis akan mengubahnya menjadi sebaran WHERE
 * milik Crime Pattern DNA, yang sudah ada di `/pola`.
 */
export function getSpatialPattern(query: AnalyticsQuery = {}): Promise<SpatialPatternResponse> {
  return apiGet<SpatialPatternResponse>(`/analytics/spatial-pattern${queryString(query, false)}`);
}
