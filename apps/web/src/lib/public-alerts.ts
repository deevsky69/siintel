import { apiGet, apiPost } from "./api";
import type { Page } from "./reports";

/**
 * Kanal imbauan kepada masyarakat (TASK 111).
 *
 * Bentuk data mengikuti `apps/api/.../routers/public_alerts.py`. Layar ini menutup lengan
 * terakhir rantai pada CLAUDE.md §9: prediksi → peringatan → imbauan kepada yang
 * berkepentingan. Sampai 9 September 2026 lengan itu tidak ada sama sekali — tabelnya
 * berisi 25 baris tanpa satu pun endpoint.
 */

export type PublicAlertStatus = "ACTIVE" | "RESOLVED" | "EXPIRED";

export type PublicAlert = {
  code: string;
  severity: string;
  threat_type: string;
  area_text: string;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  status: string;
  public_message: string;
  /** Peringatan dini yang menjadi dasarnya — jalan pulang dari imbauan ke prediksinya. */
  warning_code: string | null;
  published_at: string;
};

export type AlertCandidate = {
  warning_code: string;
  severity: string;
  threat_type: string;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  kecamatan: string;
  /** RANCANGAN yang diturunkan aturan. Bukan isi tersimpan — lihat `draft_basis`. */
  suggested_message: string;
};

export type CandidateList = {
  data: AlertCandidate[];
  severity_gate_basis: string;
  draft_basis: string;
  reference_time: string;
  demo_clock: boolean;
};

export type AlertPage = Page<PublicAlert> & {
  basis: string;
  severity_gate_basis: string;
};

export const getPublicAlerts = () => apiGet<AlertPage>("/public-alerts?page_size=50");

export const getAlertCandidates = () => apiGet<CandidateList>("/public-alerts/candidates");

export const publishAlert = (warningCode: string, message: string) =>
  apiPost<{ data: PublicAlert }>("/public-alerts", {
    warning_code: warningCode,
    public_message: message,
  });

export const withdrawAlert = (code: string) =>
  apiPost<{ data: PublicAlert }>(`/public-alerts/${encodeURIComponent(code)}/resolve`, {});

/** Urutan status pada layar: yang sedang beredar lebih dahulu. */
export const ALERT_STATUS_ORDER: PublicAlertStatus[] = ["ACTIVE", "RESOLVED", "EXPIRED"];

export const ALERT_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Sedang berlaku",
  RESOLVED: "Dicabut",
  EXPIRED: "Kedaluwarsa",
};
