import { apiGet } from "./api";
import type { CitizenReportPage, CommunitySummary } from "./community-format";

export * from "./community-format";

export const getCommunitySummary = () => apiGet<CommunitySummary>("/community/summary");

/**
 * Daftar laporan sesuai penyaringan pada URL.
 *
 * Nilai penyaring tetap di-encode di sini meskipun halaman sudah memvalidasinya terhadap
 * daftar yang dikenal: penyaringan yang sah adalah urusan backend, dan klien tidak boleh
 * menjadi satu-satunya yang menjaga bentuk permintaan.
 */
export function getCitizenReports(filters: {
  status?: string | null;
  category?: string | null;
  pageSize?: number;
}): Promise<CitizenReportPage> {
  const query = new URLSearchParams({ page_size: String(filters.pageSize ?? 25) });
  if (filters.status) query.set("status", filters.status);
  if (filters.category) query.set("category", filters.category);
  return apiGet<CitizenReportPage>(`/citizen-reports?${query.toString()}`);
}
