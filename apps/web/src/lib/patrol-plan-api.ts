import { apiGet, apiPost } from "./api";
import type {
  PatrolPlan,
  PlanDecision,
  PlanDecisionRow,
  PlanEvaluation,
  SlotKey,
} from "./patrol-plan";

/**
 * Pemanggil API rencana patroli — hanya untuk Server Component dan Server Action.
 * Tipe dan pembantunya ada di `patrol-plan.ts` agar dapat dipakai komponen klien.
 */
export const getPatrolPlan = () => apiGet<PatrolPlan>("/patrol-plan");
export const getPatrolPlanEvaluation = () => apiGet<PlanEvaluation>("/patrol-plan/evaluation");
export const getPlanDecisions = () => apiGet<{ data: PlanDecisionRow[] }>("/patrol-plan/decisions");
export const submitPlanDecision = (body: {
  decision: PlanDecision;
  reason?: string;
  kept_slots?: SlotKey[];
}) => apiPost<PlanDecisionRow>("/patrol-plan/decisions", body);

/** Perkiraan singkat satu bulan (JSON) — lampiran Produk Bulanan sejak 10 November 2026. */
export type OutlookSlot = {
  rank: number;
  polsek: string;
  kecamatan: string;
  kelurahan: string;
  block_start: number;
  block_label: string;
  incidents: number;
  share_percent: number;
  function: string;
  recommendation: string;
};
export type MonthlyOutlook = {
  target_month: string;
  target_label: string;
  basis_labels: string[];
  status: string;
  threats: { threat_type: string; slots: OutlookSlot[] }[];
  basis: string;
};
export const getMonthlyOutlook = (month: string) =>
  apiGet<MonthlyOutlook>(`/patrol-plan/outlook?month=${encodeURIComponent(month)}`);
