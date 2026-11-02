import { ApiError } from "@/lib/api";
import {
  getEvaluationMetrics,
  getEvaluationSummary,
  getRecommendationOutcome,
  getThresholdSweep,
} from "@/lib/evaluation";
import { EvaluationView } from "./evaluation-view";

export const dynamic = "force-dynamic";

/**
 * Evaluation Center (TASK 150–151).
 *
 * Menopang success criteria #06 Taskap: Prediction vs Actual. Seluruh angka berasal dari
 * `/evaluation/metrics` dan `/evaluation/summary`, lengkap dengan penanda status dan
 * dasar perhitungannya.
 */
export default async function EvaluationCenterPage() {
  const [metrics, summary, sweep, outcome] = await Promise.all([
    getEvaluationMetrics(),
    getEvaluationSummary(),
    getThresholdSweep(),
    // Pencocokan rekomendasi (8 Oktober 2026) adalah pelengkap: bila gagal, halaman tetap
    // menampilkan angka evaluasi lainnya dan menyatakan panel itu tidak termuat.
    getRecommendationOutcome().catch((error: unknown) => {
      if (error instanceof ApiError) return null;
      throw error;
    }),
  ]);

  return <EvaluationView metrics={metrics} summary={summary} sweep={sweep} outcome={outcome} />;
}
