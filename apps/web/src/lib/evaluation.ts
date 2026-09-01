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
