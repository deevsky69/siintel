import { apiGet } from "./api";

/**
 * Data evaluasi Prediction vs Actual (TASK 150–151).
 *
 * Menopang success criteria #06 Taskap. Setiap bentuk data di sini membawa `status`
 * dan `basis` dari API, dan keduanya **wajib ikut tampil**: aturan pencocokan antara
 * prediksi dan kejadian nyata belum ditetapkan (U-03), sehingga angka precision/recall
 * belum boleh dibaca sebagai hasil final (CLAUDE.md §26).
 */

export type EvaluationMetrics = {
  hits: number;
  false_positives: number;
  false_negatives: number;
  /** `null` berarti tidak dapat dihitung — berbeda maknanya dari nol. */
  precision: number | null;
  recall: number | null;
  evaluated_rows: number;
  /** Sejak evaluasi mundur data asli (1 Oktober 2026); absen pada respons lama. */
  unevaluable_incidents?: number;
  evaluated_from?: string | null;
  evaluated_to?: string | null;
  warning_floor?: number;
  threshold_version?: string;
  threat_types?: string[];
  status: string;
  basis: string;
};

/** Hasil pencocokan satu baris evaluasi. */
export type MatchType = "HIT" | "FALSE_POSITIVE" | "FALSE_NEGATIVE";

export type EvaluationSummary = {
  /** Jenis ancaman → jumlah baris per hasil pencocokan. */
  per_threat: Record<string, Partial<Record<MatchType, number>>>;
  model_versions: string[];
  status: string;
  basis: string;
};

export const MATCH_TYPES: readonly MatchType[] = [
  "HIT",
  "FALSE_POSITIVE",
  "FALSE_NEGATIVE",
] as const;

export const MATCH_LABELS: Record<MatchType, string> = {
  HIT: "Terbukti",
  FALSE_POSITIVE: "Positif Palsu",
  FALSE_NEGATIVE: "Negatif Palsu",
};

export const MATCH_HINTS: Record<MatchType, string> = {
  HIT: "Diprediksi dan benar-benar terjadi",
  FALSE_POSITIVE: "Diprediksi, tetapi tidak terjadi",
  FALSE_NEGATIVE: "Terjadi, tetapi tidak diprediksi",
};

/** Angka rasio dalam gaya Indonesia (koma desimal). Nilai kosong dinyatakan, bukan diisi nol. */
export function formatRatio(value: number | null): string {
  if (value === null) return "tidak dapat dihitung";
  return value.toLocaleString("id-ID", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

/** Bentuk persen untuk pembaca non-teknis. */
export function formatPercent(value: number | null): string | null {
  if (value === null) return null;
  return `${(value * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
}

export const getEvaluationMetrics = () => apiGet<EvaluationMetrics>("/evaluation/metrics");

export const getEvaluationSummary = () => apiGet<EvaluationSummary>("/evaluation/summary");

/** Satu baris "bila ambang dinaikkan menjadi T". */
export type SweepRow = {
  threshold: number;
  hits: number;
  false_positives: number;
  false_negatives: number;
  precision: number | null;
  recall: number | null;
  warnings_per_day: number | null;
};

export type ThresholdSweep = {
  current_floor: number;
  evaluated_days: number;
  rows: SweepRow[];
  status: string;
  basis: string;
};

export const getThresholdSweep = () => apiGet<ThresholdSweep>("/evaluation/threshold-sweep");

/** Putusan pencocokan satu rekomendasi dengan kenyataan tahun sasaran (PROPOSED). */
export type OutcomeVerdict = "SEJALAN" | "SEBAGIAN" | "TIDAK_SEJALAN" | "BELUM_DAPAT_DINILAI";

export const VERDICT_LABELS: Record<OutcomeVerdict, string> = {
  SEJALAN: "Sejalan",
  SEBAGIAN: "Sebagian",
  TIDAK_SEJALAN: "Tidak sejalan",
  BELUM_DAPAT_DINILAI: "Belum dapat dinilai",
};

export type RecommendationOutcomeRow = {
  code: string;
  status: string;
  priority: string | null;
  recommended_function: string;
  prediction_code: string;
  threat_type: string;
  kecamatan: string | null;
  kelurahan: string | null;
  time_window: string | null;
  window_start: string;
  window_end: string;
  risk_score: number;
  target_year: number;
  /** Ada kejadian pada enam jam yang persis diprediksi. */
  literal_window_hit: boolean;
  area_incidents: number;
  area_timed_incidents: number;
  area_unknown_time: number;
  block_incidents: number;
  block_share_percent: number | null;
  expected_share_percent: number | null;
  area_rank: number | null;
  area_rank_of: number;
  verdict: OutcomeVerdict;
};

export type RecommendationOutcome = {
  target_years: number[];
  observed_to: string | null;
  rows: RecommendationOutcomeRow[];
  summary: {
    total: number;
    aligned: number;
    partial: number;
    not_aligned: number;
    unevaluable: number;
    literal_window_hits: number;
    aligned_percent: number | null;
  };
  status: string;
  basis: string;
};

export const getRecommendationOutcome = () =>
  apiGet<RecommendationOutcome>("/evaluation/recommendations");
