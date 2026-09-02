import { apiGet, apiPost } from "./api";

/**
 * AI Prediction Center: daftar prediksi, penjalanannya, dan publikasinya.
 *
 * Bentuk data mengikuti `apps/api/.../routers/prediction_center.py` dan
 * `routers/intelligence.py`. Yang perlu diingat pembaca berkas ini: **tidak ada model
 * terlatih di balik angka-angka ini**. Prediksi dihasilkan dari proyeksi persistensi
 * berbasis aturan atas `risk_scores` yang sudah ada — `model_version` menyebut versi
 * aturan, bukan nama model, dan setiap faktor penjelas berlabel `RULE` (CLAUDE.md §25,
 * §27). Layar wajib menyatakannya sendiri, bukan menyembunyikannya.
 *
 * Label, satuan, dan pembentukan teks tinggal di `app/(app)/prediksi/display.ts`, bukan di
 * sini: berkas ini menarik `./api` yang memuat `next/headers`, sehingga komponen
 * `"use client"` tidak boleh mengimpornya selain sebagai tipe.
 */

/**
 * Daftar horizon, status, dan permission tinggal di `app/(app)/prediksi/display.ts`.
 *
 * Bukan di sini: berkas ini menarik `./api` yang memuat `next/headers`, sehingga komponen
 * `"use client"` tidak boleh mengimpornya — bahkan hanya untuk sebuah konstanta.
 */

/**
 * Satu faktor penjelas. `source` selalu `RULE`: penjelasan berasal dari aturan yang
 * benar-benar dijalankan, bukan dari kontribusi fitur sebuah model.
 */
export type PredictionFactor = {
  factor: string;
  value?: number | null;
  weight?: number | null;
  contribution: number;
  source: string;
  reason?: string | null;
  basis?: string | null;
};

/** Baris pada `GET /predictions`. */
export type PredictionRow = {
  code: string;
  prediction_date: string;
  forecast_horizon: string;
  threat_type: string;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  risk_score: number;
  confidence: number | null;
  dominant_factors: PredictionFactor[] | null;
  model_version: string | null;
  status: string;
  kecamatan: string;
  kelurahan: string | null;
  grid_id: string | null;
};

export type Pagination = {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type Page<T> = { data: T[]; pagination: Pagination };

/** Baris contoh pada respons penjalanan — belum tersimpan selama `dry_run`. */
export type RunForecast = {
  grid_id: string;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string;
  threat_type: string;
  time_window: string;
  window_start: string;
  window_end: string;
  risk_score: number | null;
  risk_class: string | null;
  confidence: number | null;
  confidence_reason: string;
  supporting_incidents: number;
  baseline_code: string | null;
  baseline_assessment_date: string | null;
  baseline_age_days: number | null;
  weights_version: string | null;
  dominant_factors: PredictionFactor[];
  not_predicted_reason: string | null;
};

export type RunResult = {
  prediction_date: string;
  horizon: string;
  dry_run: boolean;
  written: number;
  existing_rows: number;
  status_written: string;
  /** Hari yang diprediksi = tanggal prediksi + jarak horizon. */
  target_date: string;
  /** Batas terluar keempat jendela pada hari sasaran. */
  window_from: string;
  window_to: string;
  time_windows: string[];
  threat_types: string[];
  combinations: number;
  predicted: number;
  not_predicted: number;
  reference_time: string;
  demo_clock: boolean;
  /** Versi **aturan**, bukan nama model. */
  rule_version: string;
  weights_versions: string[];
  threshold_version: string;
  threshold_status: string;
  evidence: { incidents: number; date_from: string | null; date_to: string | null };
  not_computed_reason: string | null;
  risk_class_distribution: Record<string, number>;
  by_threat_type: {
    threat_type: string;
    windows: number;
    highest: number;
    average: number;
    average_confidence: number;
  }[];
  not_predicted_reasons: { reason: string; combinations: number }[];
  sample: RunForecast[];
  horizon_basis: string;
  projection_basis: string;
  confidence_basis: string;
  not_predicted_basis: string;
  model_disclaimer: string;
  publication_basis: string;
  dry_run_basis: string;
  status_basis: string;
};

export type PublishResult = PredictionRow & {
  reference_time: string;
  demo_clock: boolean;
  publication_basis: string;
  model_disclaimer: string;
};

/** Daftar prediksi, disaring horizon dan status di **query**, bukan setelah data terambil. */
export function getPredictions(filter: { horizon?: string; status?: string } = {}) {
  const query = new URLSearchParams({ page_size: "200" });
  if (filter.horizon) query.set("horizon", filter.horizon);
  if (filter.status) query.set("status", filter.status);
  return apiGet<Page<PredictionRow>>(`/predictions?${query.toString()}`);
}

/**
 * Menjalankan prediksi. Kewenangan `prediction:run` tetap diperiksa backend —
 * menyembunyikan tombolnya hanya kenyamanan (CLAUDE.md §21).
 */
export const runPrediction = (body: {
  prediction_date?: string;
  horizon: string;
  dry_run: boolean;
}) => apiPost<RunResult>("/predictions/run", body);

/**
 * Mempublikasikan satu prediksi: `DRAFT` → `PUBLISHED`.
 *
 * Tindakan tersendiri, bukan efek samping menjalankan prediksi: hanya prediksi
 * terpublikasi yang boleh melahirkan peringatan dini.
 */
export const publishPrediction = (code: string) =>
  apiPost<PublishResult>(`/predictions/${encodeURIComponent(code)}/publish`, {});
