import { apiGet } from "./api";

/** Bentuk data yang dikembalikan API dashboard (lihat `apps/api/.../routers/dashboard.py`). */

export type ThreatScore = { threat_type: string; risk_score: number };
export type DistrictRisk = { kecamatan: string; risk_score: number };
export type UnitCount = { status: string; count: number };

export type DashboardSummary = {
  reference_time: string;
  demo_clock: boolean;
  assessment_date: string | null;
  security_index: number;
  security_index_basis: string;
  high_risk_basis: string;
  incidents_24h: number;
  predictions_24h: number;
  high_risk_areas: number;
  active_warnings: number;
  active_operations: number;
  critical_time_window: string | null;
  top_threats: ThreatScore[];
  risk_by_district: DistrictRisk[];
  units: UnitCount[];
};

export type DominantFactor = { factor: string; contribution: number; source: string };

export type WarningRow = {
  code: string;
  severity: string;
  threat_type: string;
  time_window: string | null;
  risk_score: number;
  confidence: number | null;
  status: string;
  kecamatan: string;
  kelurahan: string | null;
  prediction_code: string;
};

export type RecommendationRow = {
  code: string;
  recommended_function: string;
  recommendation_text: string;
  priority: string | null;
  status: string;
  warning_code: string | null;
};

export type OutlookRow = {
  horizon: string;
  kecamatan: string | null;
  risk_score: number | null;
  threat_type: string | null;
};

export type TrendSeries = { year: number; monthly: number[] };

type Page<T> = { data: T[]; pagination: { total_items: number } };

export const getSummary = () => apiGet<DashboardSummary>("/dashboard/summary");

export const getTrends = () =>
  apiGet<{ years: number[]; series: TrendSeries[] }>("/dashboard/trends");

export const getOutlook = () =>
  apiGet<{ reference_time: string; outlook: OutlookRow[] }>("/dashboard/predictive-outlook");

export const getActiveWarnings = () =>
  apiGet<Page<WarningRow>>("/warnings?status=ACTIVE&page_size=5");

export const getRecommendations = (warningCode: string) =>
  apiGet<Page<RecommendationRow>>(
    `/recommendations?warning_code=${encodeURIComponent(warningCode)}&page_size=10`,
  );

export type Profile = {
  full_name: string | null;
  username: string;
  role: string;
  /** Permission efektif pengguna — dipakai menyaring menu, **bukan** menegakkan izin. */
  permissions: string[];
};

export const getProfile = () => apiGet<Profile>("/auth/me");

/**
 * Jumlah rekomendasi yang menunggu keputusan.
 *
 * Diambil dari `pagination.total_items`, bukan dengan menghitung baris: satu halaman berisi
 * satu baris sudah cukup, dan menarik seluruh rekomendasi hanya untuk mencacahnya akan
 * membebani setiap pemuatan halaman.
 */
export async function getPendingDecisionCount(): Promise<number> {
  const page = await apiGet<Page<RecommendationRow>>(
    "/recommendations?status=PENDING_REVIEW&page_size=1",
  );
  return page.pagination.total_items;
}
