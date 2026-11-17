import { apiGet } from "./api";

/** Evaluasi bulanan (Modul 5 mekanisme). */
export type MethodCoverage = {
  method: string;
  method_label: string;
  scope: string;
  frozen: boolean;
  data_cutoff: string;
  top_n: number;
  unmappable: number;
  selected: string[];
  covered: number;
  mappable_total: number;
  coverage_pct: number | null;
  /** Porsi luas kelurahan pilihan; kosong bila luas belum tersedia. */
  area_pct: number | null;
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

/** Uji historis model terhadap peta pembanding (Tabel 12 naskah). */
export type BacktestMethod = {
  method: string;
  method_label: string;
  kind: string;
  covered: number;
  total: number;
  coverage_pct: number | null;
  area_pct: number | null;
  pai: number | null;
};

export type SignTest = {
  against: string;
  against_label: string;
  wins: number;
  losses: number;
  ties: number;
  p_value: number | null;
};

export type Backtest = {
  scope: string;
  top_n: number;
  first_month: string | null;
  last_month: string | null;
  model: { available: boolean; reason?: string; model_version?: string; train_until?: string };
  annual_year: number;
  periods: {
    label: string;
    span: string;
    months: number;
    methods: BacktestMethod[];
    sign_tests: SignTest[];
  }[];
  area_source: string | null;
  basis: string;
};

export const getBacktest = (scope: string) =>
  apiGet<Backtest>(
    `/evaluation/monthly/backtest${scope ? `?scope=${encodeURIComponent(scope)}` : ""}`,
  );
