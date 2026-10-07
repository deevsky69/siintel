import { apiGet, apiPost } from "./api";

/**
 * Rekomendasi dan keputusan komandan (TASK 121, 130).
 *
 * Ini rantai human-in-the-loop pada CLAUDE.md §13: sistem mengusulkan, manusia memutuskan,
 * dan baru setelah itu tindakan operasional boleh lahir. Bentuk data di sini sengaja
 * membawa **usulan asli** bersama hasil modifikasi, supaya layar dapat menyandingkan
 * "apa yang diusulkan sistem" dengan "apa yang diputuskan pejabat".
 */

export const DECISIONS = ["APPROVED", "MODIFIED", "REJECTED"] as const;
export type Decision = (typeof DECISIONS)[number];

/** Status rekomendasi = cerminan keputusan terakhir; `PENDING_REVIEW` berarti belum diputus. */
export const PENDING = "PENDING_REVIEW";

export const DECISION_LABELS: Record<string, string> = {
  PENDING_REVIEW: "Menunggu Keputusan",
  APPROVED: "Disetujui",
  MODIFIED: "Disetujui dengan Modifikasi",
  REJECTED: "Ditolak",
};

export const FUNCTION_LABELS: Record<string, string> = {
  SAMAPTA: "Samapta",
  BINMAS: "Binmas",
  INTELKAM: "Intelkam",
  RESKRIM: "Reskrim",
  LANTAS: "Lantas",
};

export const PRIORITY_LABELS: Record<string, string> = {
  HIGH: "Tinggi",
  MEDIUM: "Sedang",
  LOW: "Rendah",
};

export type RecommendationRow = {
  code: string;
  recommended_function: string;
  recommendation_text: string;
  priority: string | null;
  status: string;
  created_at: string;
  prediction_code: string;
  warning_code: string | null;
  /** Apa, di mana, kapan, seberapa besar — dari prediksi sumbernya (7 Oktober 2026). */
  threat_type?: string | null;
  time_window?: string | null;
  risk_score?: number | null;
  kecamatan?: string | null;
  kelurahan?: string | null;
};

export type DecisionRow = {
  code: string;
  decision: string;
  reason: string | null;
  modified_text: string | null;
  decided_at: string;
  recommendation_code: string;
  recommended_function: string;
  original_recommendation: string;
  kecamatan: string | null;
};

export type Profile = {
  full_name: string | null;
  username: string;
  role: string;
  permissions: string[];
};

type Page<T> = { data: T[]; pagination: { total_items: number } };

export const getRecommendations = () =>
  apiGet<Page<RecommendationRow>>("/recommendations?page_size=200");

export const getDecisions = () => apiGet<{ data: DecisionRow[] }>("/commander-decisions");

export const getProfile = () => apiGet<Profile>("/auth/me");

/** Mengirim keputusan. Kewenangan tetap diperiksa backend — lihat `routers/decisions.py`. */
export const submitDecision = (
  code: string,
  body: { decision: Decision; reason?: string; modified_text?: string },
) => apiPost<DecisionRow>(`/recommendations/${encodeURIComponent(code)}/decisions`, body);

/** Keputusan menurut kode rekomendasi, untuk menyandingkannya dengan usulan asli. */
export function indexDecisions(rows: DecisionRow[]): Map<string, DecisionRow> {
  return new Map(rows.map((row) => [row.recommendation_code, row]));
}

/**
 * Membagi rekomendasi menjadi yang menunggu keputusan dan yang sudah diputus.
 *
 * Yang menunggu diletakkan lebih dulu: itulah yang menuntut tindakan pejabat.
 */
export function splitByDecision(rows: RecommendationRow[]) {
  return {
    pending: rows.filter((row) => row.status === PENDING),
    decided: rows.filter((row) => row.status !== PENDING),
  };
}

const PRIORITY_RANK: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

/**
 * Urutan baca Pimpinan: prioritas tinggi lebih dahulu, lalu skor risiko terbesar, lalu
 * yang paling lama menunggu. Daftar dari server berurut waktu; itu urutan arsip, bukan
 * urutan memutuskan.
 */
export function sortForDecision(rows: RecommendationRow[]): RecommendationRow[] {
  return [...rows].sort(
    (a, b) =>
      (PRIORITY_RANK[a.priority ?? ""] ?? 3) - (PRIORITY_RANK[b.priority ?? ""] ?? 3) ||
      (b.risk_score ?? 0) - (a.risk_score ?? 0) ||
      a.created_at.localeCompare(b.created_at),
  );
}

/** "CURANMOR · Tebet Timur, Tebet · 18:00-23:59" — satu baris yang menjawab apa/di mana/kapan. */
export function headlineOf(row: RecommendationRow): string {
  const where = [row.kelurahan, row.kecamatan].filter(Boolean).join(", ");
  return [row.threat_type, where, row.time_window].filter(Boolean).join(" · ");
}
