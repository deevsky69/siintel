import { DEFAULT_HISTORICAL_MONTHS } from "@/components/map/area";
import { ApiError, apiGet } from "./api";
import { shapesAt } from "./wilayah";

/**
 * Data untuk halaman peta (TASK 080–084).
 *
 * Peta memakai endpoint peta, bukan hasil agregasi di antarmuka:
 *
 * ```text
 * GET /map/historical                → layer historis + titik kejadian
 * GET /map/current-risk              → layer risiko berjalan
 * GET /map/predictive-heatmap        → layer prediktif
 * GET /map/area/{kecamatan}          → panel rincian satu wilayah
 * ```
 *
 * Sebelumnya berkas ini menarik `/risk-scores` dan `/predictions` lalu meringkasnya
 * sendiri per kecamatan. Peringkasan itu adalah **aturan bisnis** — skor tertinggi antar
 * sel grid, jendela paling rawan, prediksi mana yang dianggap terpublikasi — dan tempatnya
 * di backend, bukan di layar (CLAUDE.md §21, §23). Sejak endpoint `/map/*` tersedia,
 * modul ini hanya menerjemahkan bentuk respons menjadi bentuk yang enak dipakai komponen.
 *
 * Dua hal yang sengaja **tidak** dilakukan di sini:
 *
 * 1. **Tidak menghitung ulang kelas risiko.** `risk_class` selalu berasal dari respons.
 *    Layer prediktif tidak membawa kelas sama sekali (ambang masih DEMO / PROPOSED, U-01),
 *    maka layer itu ditampilkan sebagai skor mentah dan dinyatakan demikian di layar.
 * 2. **Tidak membuang `*_basis`.** Setiap angka turunan dari backend datang bersama
 *    keterangan asalnya; keterangan itu diteruskan apa adanya ke komponen.
 *
 * Pembatasan yurisdiksi tetap ditegakkan backend: pengguna Polsek hanya menerima baris
 * wilayahnya, dan kecamatan lain tampil sebagai "tidak ada data" — bukan disembunyikan
 * dari peta (CLAUDE.md §15, §24).
 *
 * Berkas ini memanggil `lib/api.ts`, yang membaca cookie sesi, sehingga **hanya boleh
 * dipakai dari server**. Pembantu tampilan yang dibutuhkan komponen klien berada di
 * `components/map/area.ts`.
 */

/** Horizon prediksi bawaan peta: jendela terdekat yang masih dapat ditindak. */
export const MAP_HORIZON = "6H";

/* ------------------------------------------------------------------ *
 * Bentuk respons API — disalin dari `apps/api/.../routers/map_view.py`
 * ------------------------------------------------------------------ */

export type CurrentThreat = {
  threat_type: string;
  risk_score: number;
  risk_class: string;
  time_window: string | null;
  cell_count: number;
};

export type CurrentRiskArea = {
  kecamatan: string;
  polsek: string | null;
  risk_score: number;
  risk_class: string | null;
  average_risk_score: number;
  cell_count: number;
  grid_count: number;
  latitude: number;
  longitude: number;
  /** Versi bobot yang menghasilkan skor ini — ketertelusuran, bukan hiasan. */
  weights_version: string | null;
  threats: CurrentThreat[];
};

export type CurrentRiskResponse = {
  reference_time: string;
  demo_clock: boolean;
  assessment_date: string | null;
  areas: CurrentRiskArea[];
  aggregation_basis: string;
};

export type PredictiveThreat = {
  threat_type: string;
  risk_score: number;
  confidence: number | null;
  time_window: string | null;
  cell_count: number;
};

export type PredictiveArea = {
  kecamatan: string;
  polsek: string | null;
  /** Skor prediksi tertinggi wilayah pada horizon ini. **Tanpa kelas risiko** (U-01). */
  risk_score: number;
  confidence: number | null;
  threat_type: string;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  prediction_code: string;
  model_version: string | null;
  cell_count: number;
  threats: PredictiveThreat[];
};

export type PredictiveResponse = {
  reference_time: string;
  demo_clock: boolean;
  horizon: string;
  areas: PredictiveArea[];
  aggregation_basis: string;
};

export type HistoricalArea = {
  kecamatan: string;
  polsek: string | null;
  /** Cacah kejadian mentah pada jendela. **Bukan skor, dan tidak berkelas** — lihat basis. */
  incidents: number;
  by_threat_type: { threat_type: string; incidents: number }[];
};

export type HistoricalPoint = {
  location_code: string;
  kecamatan: string;
  kelurahan: string | null;
  latitude: number;
  longitude: number;
  incidents: number;
  dominant_threat_type: string | null;
};

export type HistoricalResponse = {
  reference_time: string;
  demo_clock: boolean;
  months: number;
  window_from: string;
  window_to: string;
  observed_from: string | null;
  observed_to: string | null;
  total_incidents: number;
  areas: HistoricalArea[];
  points: HistoricalPoint[];
  aggregation_basis: string;
};

export type DominantFactor = { factor: string; contribution: number; source: string };

export type AreaPrediction = {
  code: string;
  threat_type: string;
  kecamatan: string;
  kelurahan: string | null;
  grid_id: string;
  latitude: number;
  longitude: number;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  prediction_date: string;
  forecast_horizon: string;
  risk_score: number;
  confidence: number | null;
  dominant_factors: DominantFactor[];
  model_version: string | null;
  status: string;
};

export type AreaHistory = {
  total_incidents: number;
  date_from: string | null;
  date_to: string | null;
  by_threat_type: { threat_type: string; incidents: number }[];
};

export type AreaWarning = {
  code: string;
  severity: string;
  threat_type: string;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  risk_score: number;
  confidence: number | null;
  status: string;
  grid_id: string | null;
  prediction_code: string;
  threshold_version: string | null;
};

export type AreaTimeWindow = {
  time_window: string | null;
  risk_score: number;
  risk_class: string | null;
};

export type AreaDetail = {
  reference_time: string;
  demo_clock: boolean;
  kecamatan: string;
  polsek: string | null;
  grid_count: number;
  assessment_date: string | null;
  weights_version: string | null;
  threats: CurrentThreat[];
  critical_time_window: string | null;
  time_windows: AreaTimeWindow[];
  top_predictions: AreaPrediction[];
  history: AreaHistory;
  active_warnings: AreaWarning[];
  aggregation_basis: string;
  time_window_basis: string;
  active_warnings_basis: string;
};

/* ------------------------------------------------------------------ *
 * Bentuk yang dipakai komponen peta
 * ------------------------------------------------------------------ */

/**
 * Satu kecamatan pada peta.
 *
 * `current` dan `predictive` bernilai `null` bila API tidak mengirim baris untuk wilayah
 * itu — baik karena memang belum ada data, maupun karena berada di luar kewenangan
 * pengguna. Keduanya sama-sama tampil sebagai "tidak ada data": antarmuka tidak
 * mengetahui, dan tidak boleh menebak, mana di antara keduanya yang berlaku.
 */
export type MapDistrict = {
  kecamatan: string;
  historical: HistoricalArea | null;
  current: CurrentRiskArea | null;
  predictive: PredictiveArea | null;
};

export type MapData = {
  referenceTime: string;
  demoClock: boolean;
  assessmentDate: string | null;
  /** Versi bobot penilaian risiko; menjawab "bobotnya dari mana" saat paparan. */
  weightsVersion: string | null;
  horizon: string;
  /** Sembilan kecamatan, urut sesuai bentuk peta — termasuk yang tanpa data. */
  districts: MapDistrict[];
  /** Jendela historis yang sedang tampil, apa adanya dari API. */
  historical: {
    months: number;
    windowFrom: string;
    windowTo: string;
    observedFrom: string | null;
    observedTo: string | null;
    totalIncidents: number;
    points: HistoricalPoint[];
    /** Cacah tertinggi antar kecamatan — dasar skala warna **relatif** layer historis. */
    peakIncidents: number;
    /** Cacah tertinggi satu titik lokasi — dasar ukuran lingkaran. */
    peakPointIncidents: number;
  };
  /** Keterangan asal angka dari backend; ditampilkan, tidak dibuang. */
  historicalBasis: string;
  currentRiskBasis: string;
  predictiveBasis: string;
};

/**
 * Menggabungkan dua layer menjadi satu daftar kecamatan.
 *
 * Fungsi murni tanpa pemanggilan jaringan, sehingga dapat diuji langsung. Daftar
 * kecamatan diambil dari batas wilayah (`lib/wilayah`) supaya seluruh wilayah tetap muncul di peta;
 * yang tanpa data ditandai "tidak ada data", bukan diberi angka nol.
 */
export function buildMapData(
  current: CurrentRiskResponse,
  predictive: PredictiveResponse,
  historical: HistoricalResponse,
): MapData {
  const currentByName = new Map(current.areas.map((area) => [area.kecamatan, area]));
  const predictiveByName = new Map(predictive.areas.map((area) => [area.kecamatan, area]));
  const historicalByName = new Map(historical.areas.map((area) => [area.kecamatan, area]));

  return {
    referenceTime: current.reference_time,
    demoClock: current.demo_clock,
    assessmentDate: current.assessment_date,
    // Diambil dari wilayah mana pun yang punya: seluruh sel satu tanggal penilaian
    // memakai bobot yang sama, dan backend sudah menyatakannya bila ternyata bercampur.
    weightsVersion: current.areas.find((area) => area.weights_version)?.weights_version ?? null,
    horizon: predictive.horizon,
    districts: shapesAt("kecamatan").map((shape) => ({
      kecamatan: shape.name,
      historical: historicalByName.get(shape.name) ?? null,
      current: currentByName.get(shape.name) ?? null,
      predictive: predictiveByName.get(shape.name) ?? null,
    })),
    historical: {
      months: historical.months,
      windowFrom: historical.window_from,
      windowTo: historical.window_to,
      observedFrom: historical.observed_from,
      observedTo: historical.observed_to,
      totalIncidents: historical.total_incidents,
      points: historical.points,
      // Puncak dihitung sekali di sini, bukan di dalam komponen: menghitungnya ulang saat
      // menggambar akan menjadikan warna satu wilayah bergantung pada urutan penggambaran.
      peakIncidents: historical.areas.reduce((peak, area) => Math.max(peak, area.incidents), 0),
      peakPointIncidents: historical.points.reduce(
        (peak, point) => Math.max(peak, point.incidents),
        0,
      ),
    },
    historicalBasis: historical.aggregation_basis,
    currentRiskBasis: current.aggregation_basis,
    predictiveBasis: predictive.aggregation_basis,
  };
}

/**
 * Kecamatan yang harus dibuka panel rinciannya.
 *
 * Aturannya sengaja dibedakan supaya pembatasan kewenangan tetap terbaca:
 *
 * - nama yang **dikenal peta** dipakai apa adanya, meskipun kelak rinciannya dijawab 404
 *   karena berada di luar kewenangan pengguna — panel lalu menyatakan "tidak ada data"
 *   untuk wilayah itu, bukan melompat diam-diam ke wilayah lain (CLAUDE.md §15);
 * - nama yang **tidak dikenal** (tautan usang, salah ketik) jatuh kembali ke wilayah
 *   berisiko tertinggi, supaya paparan tidak pernah dibuka dengan layar kosong.
 *
 * Wilayah berisiko tertinggi dicari sendiri dari daftar, bukan diambil dari urutan respons:
 * daftar di sini sudah diurutkan menurut bentuk peta, bukan menurut skor.
 */
export function resolveSelectedDistrict(data: MapData, requested: string | null): string | null {
  if (requested !== null) {
    const known = data.districts.find((district) => district.kecamatan === requested);
    if (known) return known.kecamatan;
  }

  const highest = data.districts
    .filter((district) => district.current !== null)
    .reduce<MapDistrict | null>(
      (best, district) =>
        best === null || (district.current?.risk_score ?? 0) > (best.current?.risk_score ?? 0)
          ? district
          : best,
      null,
    );

  return highest?.kecamatan ?? null;
}

/* ------------------------------------------------------------------ *
 * Pemanggilan API
 * ------------------------------------------------------------------ */

export async function getMapData(
  horizon: string = MAP_HORIZON,
  months: number = DEFAULT_HISTORICAL_MONTHS,
): Promise<MapData> {
  const [current, predictive, historical] = await Promise.all([
    apiGet<CurrentRiskResponse>("/map/current-risk"),
    apiGet<PredictiveResponse>(`/map/predictive-heatmap?horizon=${encodeURIComponent(horizon)}`),
    apiGet<HistoricalResponse>(`/map/historical?months=${encodeURIComponent(String(months))}`),
  ]);

  return buildMapData(current, predictive, historical);
}

/**
 * Rincian satu kecamatan.
 *
 * Backend menjawab **404** baik untuk kecamatan yang tidak ada maupun untuk kecamatan di
 * luar kewenangan pengguna — dengan sengaja, agar keberadaan data di wilayah lain tidak
 * bocor. Antarmuka menghormati itu: keduanya menjadi `null`, dan panel menyatakan tidak
 * ada rincian yang dapat ditampilkan tanpa menebak alasannya.
 */
export async function getAreaDetail(kecamatan: string): Promise<AreaDetail | null> {
  try {
    return await apiGet<AreaDetail>(`/map/area/${encodeURIComponent(kecamatan)}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
