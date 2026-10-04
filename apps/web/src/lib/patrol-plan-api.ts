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
