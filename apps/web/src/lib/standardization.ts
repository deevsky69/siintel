import { apiGet, apiPost } from "./api";

/** Pembakuan laporan kejadian (Modul 1 mekanisme): kelurahan tertunda dan dugaan ganda. */
export type StandardRow = {
  code: string;
  incident_type: string;
  incident_date: string;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string;
  location_code: string;
  street: string | null;
  vehicle_object: boolean;
  area_pending: boolean;
  duplicate_of: string | null;
  duplicate_status: "SUSPECTED" | "CONFIRMED" | "CLEARED" | null;
  data_source: string | null;
};

export type StandardQueue = {
  area_pending: { total: number; data: StandardRow[] };
  suspected_duplicates: { total: number; data: StandardRow[] };
  kelurahan_options: Record<string, { code: string; kelurahan: string }[]>;
  duplicate_basis: string;
};

export const getStandardQueue = () => apiGet<StandardQueue>("/crimes/standardization?limit=100");

export const confirmArea = (code: string, body: { location_code: string; note?: string }) =>
  apiPost<StandardRow>(`/crimes/${encodeURIComponent(code)}/area`, body);

export const resolveDuplicate = (
  code: string,
  body: { status: "CONFIRMED" | "CLEARED"; duplicate_of?: string; note: string },
) => apiPost<StandardRow>(`/crimes/${encodeURIComponent(code)}/duplicate`, body);

/** Mutu data (naskah Taskap 4.1, Tabel 22): kelengkapan, tanda, hitungan, pencocokan. */
export type DataQuality = {
  incidents: number;
  completeness: { field: string; label: string; filled: number; pct: number | null }[];
  flags: { kind: string; label: string; total: number }[];
  counting: {
    official: number;
    linked_reports: number;
    additional_verified: number;
    awaiting_match: number;
    awaiting_verification: number;
  };
  basis: string;
};

export type MatchCandidate = {
  code: string;
  incident_type: string;
  incident_date: string;
  kelurahan: string | null;
  kecamatan: string;
  location_type: string | null;
  target_type: string | null;
  days_apart: number;
  same_kelurahan: boolean;
};

export type MatchRow = {
  code: string;
  category: string;
  status: string;
  reported_at: string;
  kecamatan: string | null;
  kelurahan: string | null;
  description: string | null;
  candidates: MatchCandidate[];
};

export const getDataQuality = () => apiGet<DataQuality>("/data-quality");
export const getMatchQueue = () =>
  apiGet<{ total: number; data: MatchRow[]; window_days: number }>("/data-quality/matches");
export const decideMatch = (
  code: string,
  body: { decision: "MATCHED" | "NOT_MATCHED"; incident_code?: string; reason: string },
) => apiPost<unknown>(`/citizen-reports/${encodeURIComponent(code)}/match`, body);

/** Dampak laporan pada jendela tiga bulan (unsur D pada IKW; naskah Lampiran 9). */
export type ImpactRow = {
  code: string;
  incident_type: string;
  incident_date: string;
  kecamatan: string;
  kelurahan: string | null;
  target_type: string | null;
  impact_status: string | null;
};

export const getImpactQueue = () =>
  apiGet<{
    from: string;
    to: string;
    reports: number;
    verified: number;
    waiting: number;
    data: ImpactRow[];
  }>("/data-quality/impact?limit=30");
export const recordImpact = (
  code: string,
  body: { loss_status: string; injury_level: string; status: string; source: string },
) => apiPost<unknown>(`/crimes/${encodeURIComponent(code)}/impact`, body);
