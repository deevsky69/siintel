import { apiGet } from "./api";

/**
 * Jejak audit (TASK 142).
 *
 * Hanya baca — tidak ada fungsi tulis di sini, dan itu bukan kelalaian: jejak audit
 * bersifat hanya-tambah (CLAUDE.md §29). Catatan yang dapat disunting bukan bukti.
 */

export const AUDIT_RESULTS = ["SUCCESS", "DENIED", "FAILED"] as const;
export type AuditResult = (typeof AUDIT_RESULTS)[number];

export const RESULT_LABELS: Record<string, string> = {
  SUCCESS: "Berhasil",
  DENIED: "Ditolak — kewenangan",
  FAILED: "Gagal — aturan",
};

/** Kelas ditulis utuh agar Tailwind membangkitkannya saat memindai berkas ini. */
export const RESULT_BADGE: Record<string, string> = {
  SUCCESS: "bg-risk-low/15 text-risk-low",
  DENIED: "bg-risk-critical/15 text-risk-critical",
  FAILED: "bg-risk-moderate/15 text-risk-moderate",
};

export type AuditRow = {
  code: string | null;
  timestamp: string;
  timestamp_wib: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  result: string;
  detail: Record<string, unknown> | null;
  /** `null` untuk peristiwa sistem yang tidak dipicu pengguna. */
  username: string | null;
  user_code: string | null;
};

export type AuditPage = {
  data: AuditRow[];
  pagination: { total_items: number; page: number; page_size: number };
  filter_basis: string;
  scope_basis: string;
  append_only_basis: string;
};

export type AuditSummary = {
  total: number;
  per_result: Record<string, number>;
  per_action: { key: string; count: number }[];
  per_resource_type: { key: string; count: number }[];
  recent_refusals: {
    code: string | null;
    timestamp_wib: string;
    action: string;
    result: string;
    resource_type: string;
    resource_id: string | null;
    username: string | null;
    detail: Record<string, unknown> | null;
  }[];
  earliest: string | null;
  latest: string | null;
  denied_basis: string;
  scope_basis: string;
  append_only_basis: string;
};

export type AuditFilters = {
  action?: string;
  result?: string;
  resource_type?: string;
  date_from?: string;
  date_to?: string;
};

function query(filters: AuditFilters, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries({ ...filters, ...extra })) {
    if (value) params.set(key, value);
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const getAuditLogs = (filters: AuditFilters) =>
  apiGet<AuditPage>(`/audit-logs${query(filters, { page_size: "50" })}`);

export const getAuditSummary = (filters: AuditFilters) =>
  apiGet<AuditSummary>(
    `/audit-logs/summary${query({ date_from: filters.date_from, date_to: filters.date_to })}`,
  );

/** Menyaring nilai dari URL ke nilai yang sah — nilai asing dibuang, tidak digemakan. */
export function readFilters(params: Record<string, string | string[] | undefined>): AuditFilters {
  const one = (key: string) => (typeof params[key] === "string" ? params[key] : undefined);
  const result = one("hasil");
  return {
    action: one("aksi"),
    result: result && (AUDIT_RESULTS as readonly string[]).includes(result) ? result : undefined,
    resource_type: one("jenis"),
    date_from: one("dari"),
    date_to: one("sampai"),
  };
}
