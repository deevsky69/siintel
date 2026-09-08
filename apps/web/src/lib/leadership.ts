import { apiGet } from "./api";

/**
 * Layar Pimpinan — bentuk respons `GET /dashboard/leadership`.
 *
 * Berkas ini hanya menyalin bentuk respons dan meneruskannya. Tidak ada agregasi, tidak
 * ada pemeringkatan, dan **tidak ada satu pun ambang** yang hidup di sini: nama status
 * wilayah dan tingkat volume laporan sudah datang dari API, yang membacanya dari
 * `config/risk/warning-thresholds.yaml` (CLAUDE.md §12).
 *
 * Setiap blok membawa `basis` dari backend. Keterangan itu diteruskan apa adanya ke layar,
 * tidak diringkas dan tidak dibuang — ia yang menjelaskan mengapa sebuah angka berbunyi
 * demikian, dan tanpanya angka di layar Pimpinan menjadi klaim tanpa asal.
 *
 * Memanggil `lib/api.ts` yang membaca cookie sesi, jadi **hanya boleh dipakai dari server**.
 */

export type Reports24h = {
  crime_incidents: number;
  citizen_reports: number;
  intelligence_reports: number;
  total: number;
  /** Laporan masyarakat tanpa lokasi yang cocok dengan master lokasi. */
  citizen_reports_without_location: number;
  window_start: string;
  window_end: string;
  intelligence_date: string;
  basis: string;
};

export type AreaStatusRow = {
  kecamatan: string;
  risk_score: number;
  risk_class: string | null;
  average_risk_score: number;
  cell_count: number;
  /** `null` bila kelas risikonya tidak dipetakan — ditampilkan apa adanya, bukan "Aman". */
  status: string | null;
  label: string;
};

export type AreaStatus = {
  assessment_date: string | null;
  areas: AreaStatusRow[];
  tally: { status: string; label: string; areas: number }[];
  mapping: { status: string; label: string; risk_classes: string[] }[];
  mapping_status: string;
  basis: string;
};

export type AttentionItem = {
  kind: "EARLY_WARNING" | "RECOMMENDATION" | "CITIZEN_REPORT";
  code: string | null;
  headline: string;
  kecamatan: string | null;
  detail: string;
  why: string;
  since: string | null;
  rank: number;
  href: string;
};

export type TopReportArea = {
  kecamatan: string;
  crime_incidents: number;
  intelligence_reports: number;
  citizen_reports: number;
  reports: number;
  level: string;
  level_label: string;
  share_of_peak: number;
};

export type ProminentIssue = {
  threat_type: string;
  incidents: number;
  previous_incidents: number;
  change: number;
};

export type PolicyItem = {
  action: string;
  function: string;
  basis: string;
  /** Selalu `RULE` selama belum ada model — lihat CLAUDE.md §27. */
  source: string;
  /** Layar yang memuat angka asal butir ini — bukan sekadar layar yang berkaitan. */
  href: string;
};

export type LeadershipBoard = {
  reference_time: string;
  demo_clock: boolean;
  reports_24h: Reports24h;
  area_status: AreaStatus;
  needs_attention: { items: AttentionItem[]; basis: string };
  priority_areas: AreaStatusRow[];
  top_report_areas: {
    days: number;
    window_from: string;
    window_to: string;
    peak_reports: number;
    unattributed_reports: number;
    areas: TopReportArea[];
    level_status: string;
    basis: string;
  };
  prominent_issues: {
    days: number;
    window_from: string;
    window_to: string;
    previous_from: string;
    previous_to: string;
    issues: ProminentIssue[];
    basis: string;
  };
  policy: { recommendations: PolicyItem[]; basis: string };
};

export const getLeadership = () => apiGet<LeadershipBoard>("/dashboard/leadership");

/**
 * Warna status wilayah.
 *
 * Dipetakan dari nama status yang **dikirim API**, bukan dihitung dari skor: menghitungnya
 * di sini akan menaruh salinan ambang di layar. Status yang tidak dikenal antarmuka
 * dijawab warna netral, bukan warna teraman.
 */
export const AREA_STATUS_TONE: Record<string, string> = {
  AMAN: "text-risk-moderate border-risk-moderate/40 bg-risk-moderate/10",
  WASPADA: "text-risk-high border-risk-high/40 bg-risk-high/10",
  SIAGA: "text-risk-critical border-risk-critical/40 bg-risk-critical/10",
};

export const REPORT_LEVEL_TONE: Record<string, string> = {
  KRITIS: "text-risk-critical border-risk-critical/40 bg-risk-critical/10",
  SEDANG: "text-risk-high border-risk-high/40 bg-risk-high/10",
  RENDAH: "text-ink-muted border-base-800 bg-base-950/40",
};

export function toneOf(table: Record<string, string>, key: string | null): string {
  return (key !== null && table[key]) || "text-ink-muted border-base-800 bg-base-950/40";
}
