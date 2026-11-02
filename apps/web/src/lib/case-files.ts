import { apiGet, apiPost } from "./api";

/** Berkas perkara 3C untuk layar petugas (`/case-files`, `case_file:read|write`). */
export type CaseRow = {
  lp_number: string;
  crime_type: string;
  kelurahan: string | null;
  kecamatan: string;
  polsek: string;
  reported_on: string;
  stage: string;
  stage_label: string;
  stage_updated_at: string;
  summary: string | null;
  vehicle_plate: string | null;
  vehicle_vin: string | null;
  vehicle_desc: string | null;
  vehicle_recovered: boolean;
  is_dummy: boolean;
  dummy_pin: string | null;
  history: { stage: string; stage_label: string; changed_at: string; note: string | null }[];
};

export type CaseList = {
  data: CaseRow[];
  total: number;
  stages: { code: string; label: string }[];
};

export const getCaseFiles = (stage: string, q: string) => {
  const query = new URLSearchParams();
  if (stage) query.set("stage", stage);
  if (q) query.set("q", q);
  const suffix = query.toString();
  return apiGet<CaseList>(`/case-files${suffix ? `?${suffix}` : ""}`);
};

export const createCaseFile = (body: Record<string, unknown>) =>
  apiPost<CaseRow & { reporter_pin: string }>("/case-files", body);

export const advanceCaseStage = (lp: string, stage: string, note: string, recovered?: boolean) =>
  apiPost<CaseRow>(`/case-files/${encodeURIComponent(lp)}/stage`, {
    stage,
    note: note || null,
    ...(recovered === undefined ? {} : { vehicle_recovered: recovered }),
  });
