import { apiGet, apiPost } from "./api";

/** Kalender SOP (catatan 192): butir berkala SOP, fakta sistem, dan rekap triwulan. */
export type SopItem = {
  key: string;
  section: string;
  rule: string;
  who: string;
  source: "SYSTEM" | "RECORDED";
  done: boolean;
  done_at: string | null;
  done_by: string | null;
  note: string | null;
  fact: string;
  can_record: boolean;
};

export type SopCalendar = {
  period: string;
  items: SopItem[];
  done: number;
  total: number;
  quarter: {
    label: string;
    months: string[];
    products: number;
    recorded: number;
    median_quality_sigap: number | null;
    median_quality_manual: number | null;
    median_minutes_ready_to_validated: number | null;
    quality_max: number;
  };
  basis: string;
};

export const getSopCalendar = (period?: string) =>
  apiGet<SopCalendar>(`/sop/calendar${period ? `?period=${period}` : ""}`);

export const recordSopCheck = (period: string, item: string, note?: string) =>
  apiPost<SopCalendar>(`/sop/calendar/${period}/${item}`, { note });
