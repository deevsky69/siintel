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
  body: { status: "CONFIRMED" | "CLEARED"; duplicate_of?: string; note?: string },
) => apiPost<StandardRow>(`/crimes/${encodeURIComponent(code)}/duplicate`, body);
