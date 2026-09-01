import { apiGet } from "./api";
import type { DominantFactor } from "./dashboard";
import { KECAMATAN_SHAPES } from "./geo";
import type { RiskClass } from "./risk";
import { RISK_LABELS, riskClassOf } from "./risk";

/**
 * Data untuk halaman peta (TASK 080–084).
 *
 * Peta tidak punya endpoint khusus: ia menyusun tampilannya dari dua endpoint yang sudah
 * ada — `GET /risk-scores` (layer risiko berjalan) dan `GET /predictions` (layer prediktif).
 * Keduanya sudah menegakkan pembatasan yurisdiksi di sisi backend, sehingga pengguna Polsek
 * memang hanya menerima baris wilayahnya; kecamatan lain tampil sebagai "tidak ada data",
 * bukan sebagai angka yang disembunyikan di antarmuka (CLAUDE.md §15, §24).
 */

const PAGE_SIZE = 200;

/** Batas pengaman perulangan halaman — mencegah permintaan tanpa akhir bila API berubah. */
const MAX_PAGES = 20;

/** Horizon prediksi yang ditampilkan pada peta: jendela terdekat yang masih dapat ditindak. */
export const MAP_HORIZON = "6H";

/** Prediksi berstatus DRAFT belum dipublikasikan, jadi tidak ikut ditampilkan. */
const HIDDEN_PREDICTION_STATUS = "DRAFT";

/** Banyak prediksi teratas yang ditampilkan per kecamatan. */
const PREDICTIONS_PER_DISTRICT = 3;

export type RiskScoreRow = {
  code: string;
  assessment_date: string;
  threat_type: string;
  time_window: string;
  risk_score: number;
  risk_class: string;
  kecamatan: string;
  grid_id: string;
  weights_version: string | null;
};

export type PredictionRow = {
  code: string;
  prediction_date: string;
  forecast_horizon: string;
  threat_type: string;
  time_window: string | null;
  risk_score: number;
  confidence: number | null;
  dominant_factors: DominantFactor[];
  model_version: string | null;
  status: string;
  kecamatan: string;
  kelurahan: string | null;
  grid_id: string;
};

type Page<T> = {
  data: T[];
  pagination: { page: number; page_size: number; total_items: number; total_pages: number };
};

/** Satu baris "jenis ancaman" atau "jendela waktu" pada panel rincian. */
export type ScoreCell = { label: string; score: number; gridId: string };

export type DistrictIntel = {
  kecamatan: string;
  /** Skor tertinggi wilayah pada tanggal penilaian terakhir; `null` bila tidak ada data. */
  riskScore: number | null;
  riskClass: RiskClass | null;
  /** Skor tertinggi per jenis ancaman, terurut menurun. */
  threats: ScoreCell[];
  /** Skor tertinggi per jendela waktu, terurut menurun. */
  windows: ScoreCell[];
  /** Prediksi teratas — terbaru lebih dulu, lengkap dengan `dominant_factors`. */
  predictions: PredictionRow[];
};

export type MapData = {
  /** Tanggal penilaian risiko yang sedang ditampilkan; `null` bila belum ada penilaian. */
  assessmentDate: string | null;
  /** Versi bobot penilaian — bagian dari ketertelusuran (CLAUDE.md §25). */
  weightsVersion: string | null;
  horizon: string;
  districts: DistrictIntel[];
};

function asRiskClass(value: string, score: number): RiskClass {
  // Kelas risiko ditetapkan backend. Nilai tak dikenal diturunkan dari skor sebagai
  // cadangan, supaya perbedaan versi API tidak membuat peta kehilangan warna.
  return value in RISK_LABELS ? (value as RiskClass) : riskClassOf(score);
}

/** Skor tertinggi per kunci, terurut menurun. */
function topPerKey(rows: RiskScoreRow[], key: (row: RiskScoreRow) => string): ScoreCell[] {
  const best = new Map<string, ScoreCell>();
  for (const row of rows) {
    const label = key(row);
    const current = best.get(label);
    if (!current || row.risk_score > current.score) {
      best.set(label, { label, score: row.risk_score, gridId: row.grid_id });
    }
  }
  return [...best.values()].sort((a, b) => b.score - a.score);
}

/**
 * Menyusun rincian per kecamatan dari baris mentah API.
 *
 * Fungsi murni, tanpa pemanggilan jaringan, sehingga dapat diuji langsung.
 * Kecamatan diambil dari `KECAMATAN_SHAPES` supaya seluruh wilayah tetap muncul di peta —
 * yang tanpa data ditandai "tidak ada data", bukan diberi angka nol.
 */
export function buildDistrictIntel(
  scores: RiskScoreRow[],
  predictions: PredictionRow[],
): DistrictIntel[] {
  return KECAMATAN_SHAPES.map((shape) => {
    const rows = scores.filter((row) => row.kecamatan === shape.kecamatan);
    const threats = topPerKey(rows, (row) => row.threat_type);
    const windows = topPerKey(rows, (row) => row.time_window);
    const top = rows.reduce<RiskScoreRow | null>(
      (best, row) => (best === null || row.risk_score > best.risk_score ? row : best),
      null,
    );

    return {
      kecamatan: shape.kecamatan,
      riskScore: top?.risk_score ?? null,
      riskClass: top ? asRiskClass(top.risk_class, top.risk_score) : null,
      threats,
      windows,
      predictions: predictions
        .filter((row) => row.kecamatan === shape.kecamatan)
        .slice(0, PREDICTIONS_PER_DISTRICT),
    };
  });
}

/**
 * Mengambil seluruh baris risiko pada tanggal penilaian **terakhir**.
 *
 * API mengurutkan `assessment_date` menurun, jadi halaman pertama sudah memuat tanggal
 * terbaru. Perulangan hanya berlanjut selama satu halaman penuh berisi tanggal yang sama —
 * pada dataset saat ini tanggal terakhir berisi 133 baris, sehingga satu permintaan cukup.
 */
async function fetchLatestRiskScores(): Promise<RiskScoreRow[]> {
  const rows: RiskScoreRow[] = [];
  let latest: string | null = null;

  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const response: Page<RiskScoreRow> = await apiGet<Page<RiskScoreRow>>(
      `/risk-scores?page=${page}&page_size=${PAGE_SIZE}`,
    );
    if (response.data.length === 0) break;

    latest ??= response.data[0].assessment_date;
    const sameDate = response.data.filter((row) => row.assessment_date === latest);
    rows.push(...sameDate);

    // Halaman sudah memuat tanggal yang lebih lama → seluruh baris terbaru sudah terkumpul.
    if (sameDate.length < response.data.length) break;
    if (page >= response.pagination.total_pages) break;
  }

  return rows;
}

async function fetchPredictions(): Promise<PredictionRow[]> {
  const response = await apiGet<Page<PredictionRow>>(
    `/predictions?horizon=${MAP_HORIZON}&page_size=${PAGE_SIZE}`,
  );
  return response.data.filter((row) => row.status !== HIDDEN_PREDICTION_STATUS);
}

export async function getMapData(): Promise<MapData> {
  const [scores, predictions] = await Promise.all([fetchLatestRiskScores(), fetchPredictions()]);

  return {
    assessmentDate: scores[0]?.assessment_date ?? null,
    weightsVersion: scores[0]?.weights_version ?? null,
    horizon: MAP_HORIZON,
    districts: buildDistrictIntel(scores, predictions),
  };
}
