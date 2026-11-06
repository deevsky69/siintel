import { apiGet } from "./api";

/** Evaluasi bulanan (Modul 5 mekanisme). */
export type MethodCoverage = {
  method: string;
  scope: string;
  frozen: boolean;
  data_cutoff: string;
  top_n: number;
  unmappable: number;
  selected: string[];
  covered: number;
  mappable_total: number;
  coverage_pct: number | null;
  pai: number | null;
};

export type MonthlyEvaluation = {
  target_month: string;
  top_n: number;
  methods: MethodCoverage[];
  decision: {
    status: string;
    priority_count: number | null;
    selected: string[];
    covered: number;
    mappable_total: number;
    coverage_pct: number | null;
    items: {
      kelurahan: string;
      kecamatan: string;
      actual: number;
      actions: number;
      decided_action: string | null;
    }[];
  } | null;
  quality: {
    analyst: Record<string, number>;
    reasons: { kelurahan: string; status: string; reason: string }[];
    returned: { stage: string; reason: string | null; acted_at: string }[];
  } | null;
  basis: string;
};

export const getMonthlyEvaluation = (month: string) =>
  apiGet<MonthlyEvaluation>(`/evaluation/monthly?month=${encodeURIComponent(month)}`);
