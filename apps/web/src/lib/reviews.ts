import { apiGet, apiPost } from "./api";

/** Moderasi Survey Rasa Aman (`/reviews`, `review:moderate`). */
export type ModerationRow = {
  code: string;
  kelurahan: string;
  kecamatan: string;
  rating: number;
  comment: string | null;
  submitted_at: string;
  status: "PENDING" | "PUBLISHED" | "REJECTED";
  moderated_at: string | null;
  moderated_by: string | null;
  moderation_note: string | null;
};

export const getModerationQueue = (status: string) =>
  apiGet<{ data: ModerationRow[]; pending_total: number }>(
    `/reviews?status=${encodeURIComponent(status)}&limit=200`,
  );

export const moderateReview = (code: string, decision: "PUBLISH" | "REJECT", note: string) =>
  apiPost<ModerationRow>(`/reviews/${encodeURIComponent(code)}/moderate`, {
    decision,
    note: note || null,
  });

/** Hasil triwulanan dengan rincian per kecamatan (`/reviews/quarterly`, `review:moderate`). */
export type QuarterDetail = {
  label: string;
  from: string;
  to: string;
  running: boolean;
  respondents: number;
  submitted: number;
  average: number | null;
  kelurahan_covered: number;
  kelurahan_total: number;
  coverage_pct: number | null;
  kecamatan: {
    kecamatan: string;
    respondents: number;
    average: number | null;
    kelurahan_covered: number;
  }[];
};

export const getQuarterlyDetail = () =>
  apiGet<{ quarters: QuarterDetail[]; basis: string }>("/reviews/quarterly");
