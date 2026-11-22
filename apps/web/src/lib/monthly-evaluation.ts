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
  /** Porsi luas kelurahan pilihan; kosong bila ada kelurahan yang luas BPS-nya belum tercantum. */
  area_pct: number | null;
  pai: number | null;
  /** Kelipatan cakupan terhadap pemilihan acak (N dari seluruh kelurahan). */
  vs_random: number | null;
};

export type MonthlyEvaluation = {
  target_month: string;
  top_n: number;
  kelurahan_total: number;
  random_coverage_pct: number | null;
  area_source: string | null;
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
  /** Modul 5: mutu draf dan waktu kerja (naskah Taskap Lampiran L huruf D). */
  work: WorkSummary | null;
  basis: string;
};

export type WorkSummary = {
  recorded: boolean;
  rubric: { key: string; label: string }[];
  quality_sigap: Record<string, number> | null;
  quality_manual: Record<string, number> | null;
  quality_sigap_total: number | null;
  quality_manual_total: number | null;
  quality_max: number;
  received_at: string | null;
  data_ready_at: string | null;
  map_ready_at: string | null;
  draft_ready_at: string | null;
  validated_at: string | null;
  minutes_receive_to_ready: number | null;
  minutes_ready_to_validated: number | null;
  note: string | null;
  recorded_at: string | null;
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
  vs_random: number | null;
};

export type SignTest = {
  against: string;
  against_label: string;
  /** Kosong bila baris model dikutip dari naskah dan hitungan per bulannya tidak tercetak. */
  wins: number | null;
  losses: number | null;
  ties: number | null;
  p_value: number | null;
  /** Bulan dengan PAI model lebih tinggi; kosong bila PAI salah satunya tidak dapat dihitung. */
  pai_wins: number | null;
};

/** Pembanding acak (naskah Lampiran J bagian M): N dari seluruh kelurahan dipilih acak. */
export type RandomBaseline = {
  top_n: number;
  kelurahan_total: number;
  coverage_pct: number;
  expected_covered: number;
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
    random: RandomBaseline;
    sign_tests: SignTest[];
    /** Baris model dikutip dari naskah (Lampiran J bagian K), bukan dihitung ulang. */
    quoted: { source: string; model_covered_by_app: number; against: string | null } | null;
  }[];
  /** Skenario tetap (naskah Tabel 12): informasi berhenti pada akhir masa latih. */
  fixed: {
    span: string | null;
    methods: {
      method: string;
      method_label: string;
      covered: number;
      total: number;
      coverage_pct: number | null;
      area_pct: number | null;
      pai: number | null;
      vs_random: number | null;
    }[];
  };
  area_source: string | null;
  area_total_km2: number | null;
  /** Baris model memakai pilihan kelurahan yang terekam pada naskah (Lampiran J bagian H–J). */
  recorded: {
    source: string | null;
    monthly_months: number;
    monthly_differing: string[];
    fixed_months: number;
    fixed_differing: number;
  } | null;
  /** Ambang pemakaian model (naskah revisi 7 sasaran 3.3.1). */
  criterion: { months: number; min_margin_pct: number; min_pai: number; source: string };
  basis: string;
};

export const getBacktest = (scope: string, topN?: number) => {
  const query = new URLSearchParams();
  if (scope) query.set("scope", scope);
  if (topN) query.set("top_n", String(topN));
  const suffix = query.toString();
  return apiGet<Backtest>(`/evaluation/monthly/backtest${suffix ? `?${suffix}` : ""}`);
};
