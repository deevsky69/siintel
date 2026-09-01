import { getEvaluationMetrics, getEvaluationSummary } from "@/lib/evaluation";
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
  const [metrics, summary] = await Promise.all([getEvaluationMetrics(), getEvaluationSummary()]);

  return <EvaluationView metrics={metrics} summary={summary} />;
}
