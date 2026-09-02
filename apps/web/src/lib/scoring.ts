import { apiGet, apiPost } from "./api";

/**
 * Mesin penilaian risiko: bobot yang mendasarinya, dan hasil menjalankannya.
 *
 * Layar `/skoring` menampilkan **dasar** perhitungan lebih dulu, baru hasilnya. Angka
 * risiko yang tidak dapat dikembalikan ke bobot yang menghasilkannya tidak dapat
 * diperdebatkan siapa pun — dan seluruh bobot di sini masih berstatus `DEMO`/`PROPOSED`
 * (U-01, U-02), sehingga statusnya wajib ikut tampil (CLAUDE.md §11).
 *
 * Yang dinilai adalah **keadaan berjalan**, bukan ramalan. Tidak ada satu pun kata
 * "prediksi" pada layar ini.
 */

export type ScoringFactor = {
  factor: string;
  weight: number;
  sign: "positive" | "negative";
  /** Benar bila `risk_scores` punya kolom untuk faktor ini. */
  persisted: boolean;
  basis: string | null;
};

export type ScoringProfile = {
  profile: string;
  applies_to: string[];
  positive_weight_total: number;
  factors: ScoringFactor[];
};

export type ScoringVersion = {
  version: string;
  status: string;
  active: boolean;
  profiles: ScoringProfile[];
};

export type RiskBand = { class: string; min: number; max: number };

export type ScoringConfig = {
  active_version: string;
  active_status: string;
  versions: ScoringVersion[];
  thresholds: { version: string; status: string; risk_classes: RiskBand[] };
  time_windows: string[];
  persisted_factors: string[];
  coverage: { locations: number; assessment_dates: number };
  reference_time: string;
  demo_clock: boolean;
  config_basis: string;
  score_basis: string;
  persistence_basis: string;
};

/** Satu faktor pada baris hasil. `value` `null` berarti tidak terukur — bukan nol. */
export type RunFactor = {
  factor: string;
  value: number | null;
  weight: number | null;
  contribution: number;
  /** Selalu `RULE`: tidak ada model terlatih di balik angka ini (CLAUDE.md §27). */
  source: string;
  reason: string | null;
  basis: string | null;
};

export type RunCell = {
  grid_id: string;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string;
  location_type: string | null;
  threat_type: string;
  time_window: string;
  risk_score: number | null;
  risk_class: string | null;
  unscored_reason: string | null;
  factors: RunFactor[];
};

export type RunProfile = {
  profile: string;
  weights_version: string;
  threat_types: string[];
  weights: Record<string, number>;
  combinations: number;
  scored: number;
  unscored: number;
  risk_class_distribution: Record<string, number>;
  by_threat_type: { threat_type: string; cells: number; highest: number; average: number }[];
  unscored_reasons: { reason: string; combinations: number }[];
  sample: RunCell[];
  not_computed_reason: string | null;
  unscored_basis: string;
};

export type RunResult = {
  assessment_date: string;
  dry_run: boolean;
  written: number;
  existing_rows: number;
  reference_time: string;
  demo_clock: boolean;
  weights_version: string;
  weights_status: string;
  threshold_version: string;
  threshold_status: string;
  evidence: { incidents: number; date_from: string | null; date_to: string | null };
  profiles: RunProfile[];
  score_basis: string;
  dry_run_basis: string;
  persistence_basis: string;
};

/**
 * Label, satuan, dan pembentukan teks tinggal di `app/(app)/skoring/display.ts`, bukan di
 * sini: berkas ini menarik `./api` yang memuat `next/headers`, sehingga komponen
 * `"use client"` tidak boleh mengimpornya selain sebagai tipe.
 */
export const getScoringConfig = () => apiGet<ScoringConfig>("/risk-scores/config");

/**
 * Menjalankan penilaian. Kewenangan `risk_score:run` tetap diperiksa backend —
 * menyembunyikan tombolnya hanya kenyamanan (CLAUDE.md §21).
 */
export const runScoring = (body: { assessment_date?: string; dry_run: boolean }) =>
  apiPost<RunResult>("/risk-scores/run", body);
