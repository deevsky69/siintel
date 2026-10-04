import { apiGet } from "./api";

/**
 * Rencana patroli tahunan (permintaan pemilik proyek 4 Oktober 2026).
 *
 * Dari pola kejadian tahun dasar (2025), backend mengusulkan slot patroli — kelurahan ×
 * blok jam × jenis — untuk tahun sasaran (2026), lalu mencocokkannya dengan kejadian nyata
 * tahun sasaran. Seluruh angka datang dari `/patrol-plan` dan `/patrol-plan/evaluation`
 * lengkap dengan `status` dan `*_basis`; keduanya wajib ikut tampil karena ukuran kemiripan
 * resminya belum ditetapkan (PROPOSED).
 */

export type PlanSlot = {
  rank: number;
  threat_type: string;
  polsek: string;
  kecamatan: string;
  kelurahan: string;
  block_start: number;
  block_label: string;
  incidents: number;
  share_percent: number;
  cumulative_share_percent: number;
  why: string;
};

export type ThreatPlan = {
  threat_type: string;
  basis_incidents: number;
  basis_with_hour: number;
  basis_unknown_time: number;
  basis_unknown_kelurahan: number;
  slots: PlanSlot[];
  covered_share_percent: number;
};

export type PatrolPlan = {
  version: string;
  status: string;
  basis_from: string;
  basis_to: string;
  target_year: number;
  scope: string | null;
  rules: { basis_months: number; max_slots_per_threat: number; minimum_incidents: number };
  threats: ThreatPlan[];
  plan_basis: string;
  reference_time: string;
  demo_clock: boolean;
};

export type SlotResult = PlanSlot & { actual_incidents: number; hit: boolean };

export type ThreatEvaluation = {
  threat_type: string;
  slots: number;
  slots_hit: number;
  slot_hit_rate_percent: number | null;
  actual_incidents: number;
  actual_evaluable: number;
  actual_unknown_time: number;
  actual_unknown_kelurahan: number;
  covered_incidents: number;
  coverage_percent: number | null;
  hour_similarity_percent: number | null;
  area_similarity_percent: number | null;
  hour_profile: {
    block_start: number;
    block_label: string;
    basis_incidents: number;
    actual_incidents: number;
  }[];
  slot_results: SlotResult[];
};

export type PlanEvaluation = {
  version: string;
  status: string;
  target_year: number;
  target_observed_from: string;
  target_observed_to: string | null;
  scope: string | null;
  overall: {
    slots: number;
    slots_hit: number;
    slot_hit_rate_percent: number | null;
    actual_evaluable: number;
    covered_incidents: number;
    coverage_percent: number | null;
    hour_similarity_percent: number | null;
    area_similarity_percent: number | null;
  };
  per_threat: ThreatEvaluation[];
  similarity_basis: string;
  partial_year_basis: string;
  reference_time: string;
  demo_clock: boolean;
};

export const getPatrolPlan = () => apiGet<PatrolPlan>("/patrol-plan");
export const getPatrolPlanEvaluation = () => apiGet<PlanEvaluation>("/patrol-plan/evaluation");

/** "84,3%" — atau tanda bahwa angkanya memang tidak dapat dihitung. */
export function percentText(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
}

/** "27 Desember 2025" dari `YYYY-MM-DD`. */
export function longDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(`${value}T00:00:00+07:00`).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Jakarta",
  });
}
