import { apiGet, apiPost } from "./api";

/** Peringkat bulanan 65 kelurahan (Modul 2–3 mekanisme). */
export type RankedArea = {
  rank: number;
  kelurahan: string;
  kecamatan: string;
  polsek: string;
  predicted_count: number;
  ikw: number | null;
  ikw_category: "RENDAH" | "SEDANG" | "TINGGI" | null;
  basis: {
    basis_total?: number;
    total_12m?: number;
    trend?: number;
    consistency_months?: number;
    /** Hanya pada metode MODEL: kontribusi tiap masukan, dihitung dari pohon model. */
    factors?: { label: string; contribution: number; effect_pct?: number }[];
  };
};

/** Metode yang menjadi dasar usulan, dan bukti penjaga di baliknya. */
export type MethodChoice = { method: string; reason: string; evidence: Record<string, unknown> };

export type ModelCard = {
  available: boolean;
  reason?: string;
  model_version?: string;
  algorithm?: string;
  train_until?: string;
  training_targets?: string;
  training_rows?: number;
  training_incidents?: number;
  features?: { name: string; label: string; importance: number }[];
};

export type Ranking = {
  frozen: boolean;
  ranking_id?: string;
  target_month: string;
  method: string;
  method_label: string;
  scope: string;
  data_cutoff: string;
  model_version: string;
  basis_from: string;
  basis_to: string;
  pending_count: number;
  generated_at?: string;
  ikw_status: string;
  data: RankedArea[];
};

export type RankingOptions = {
  version: string;
  status: string;
  /** Metode dasar usulan bulan yang disarankan (hasil penjaga). */
  default_method: string;
  configured_method: string;
  method_choice: MethodChoice;
  methods: { value: string; label: string; kind: string; available: boolean }[];
  model: ModelCard | null;
  scopes: string[];
  default_scope: string;
  suggested_month: string;
  frozen: { target_month: string; method: string; scope: string }[];
  basis: string;
};

export const getRankingOptions = () => apiGet<RankingOptions>("/rankings/options");

export const getRanking = (month: string, method: string, scope: string) => {
  const query = new URLSearchParams();
  if (month) query.set("month", month);
  if (method) query.set("method", method);
  if (scope) query.set("scope", scope);
  const suffix = query.toString();
  return apiGet<Ranking>(`/rankings${suffix ? `?${suffix}` : ""}`);
};

export const freezeRanking = (body: { month: string; method?: string; scope?: string }) =>
  apiPost<Ranking>("/rankings/freeze", body);
