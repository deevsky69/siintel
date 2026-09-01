import { apiGet } from "./api";
import { RISK_LABELS, type RiskClass } from "./risk";

/**
 * Executive Brief harian (modul MVP #14).
 *
 * Bentuk data mengikuti `apps/api/.../routers/brief.py`. Yang perlu diketahui pembaca
 * berkas ini ada tiga:
 *
 * 1. **Angka dan kalimat dipisah.** API hanya mengembalikan angka beserta `*_basis`-nya.
 *    Kalimat pada brief disusun oleh fungsi template di berkas ini — bukan oleh model
 *    bahasa, dan tidak ada model bahasa di sistem ini (`docs/13-rencana-integrasi-ai.md`).
 *
 * 2. **Setiap angka di dalam kalimat juga tertera sebagai angka** pada halaman yang sama.
 *    Bila templatenya keliru menyusun kalimat, kekeliruan itu terlihat di sebelahnya —
 *    bukan tersembunyi di balik prosa yang terdengar meyakinkan (CLAUDE.md §27).
 *
 * 3. **Bagian yang tidak boleh dibaca pengguna bernilai `null`,** bukan nol. Kalimat
 *    ringkasan melewatkannya, dan halaman menampilkan alasannya dari `*_basis`.
 */

export type BriefArea = {
  kecamatan: string;
  risk_score: number;
  risk_class: string;
  threat_type: string;
  time_window: string | null;
};

export type BriefThreat = {
  threat_type: string;
  kecamatan: string;
  time_window: string | null;
  risk_score: number;
  risk_class: string;
};

export type SeverityCount = { severity: string; count: number };

export type FunctionCount = { recommended_function: string; count: number };

export type PendingActionItem = {
  decision_code: string;
  decision: string;
  decided_at: string;
  recommendation_code: string;
  recommended_function: string;
  priority: string | null;
  kecamatan: string;
  original_recommendation: string;
  modified_text: string | null;
};

export type BriefAccuracy = {
  hits: number;
  false_positives: number;
  false_negatives: number;
  /** `null` berarti tidak dapat dihitung — berbeda maknanya dari nol. */
  precision: number | null;
  recall: number | null;
  evaluated_rows: number;
  status: string;
};

export type DailyBrief = {
  reference_time: string;
  demo_clock: boolean;
  brief_date: string;
  brief_time: string;
  window_hours: number;
  scope_polsek: string | null;
  scope_basis: string;
  clock_basis: string;

  incidents_recent: number | null;
  incidents_basis: string;

  active_warnings: number | null;
  warnings_by_severity: SeverityCount[];
  warnings_basis: string;

  assessment_date: string | null;
  top_area: BriefArea | null;
  top_area_basis: string;
  top_threats: BriefThreat[];
  top_threats_basis: string;

  pending_recommendations: number | null;
  pending_by_function: FunctionCount[];
  pending_recommendations_basis: string;

  pending_actions: number | null;
  pending_action_items: PendingActionItem[];
  pending_actions_basis: string;

  accuracy: BriefAccuracy | null;
  accuracy_basis: string;
};

const MONTHS = [
  "Januari",
  "Februari",
  "Maret",
  "April",
  "Mei",
  "Juni",
  "Juli",
  "Agustus",
  "September",
  "Oktober",
  "November",
  "Desember",
];

/**
 * Tanggal `YYYY-MM-DD` menjadi "27 Desember 2025".
 *
 * Diurai sebagai teks, bukan lewat `new Date`: tanggal brief sudah dihitung backend dalam
 * WIB, dan menguraikannya sebagai waktu akan menggesernya satu hari pada server yang
 * zona waktunya bukan WIB.
 */
export function formatBriefDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day || month < 1 || month > 12) return value;
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** Label kelas risiko; nilai di luar tangga baku ditampilkan apa adanya, bukan ditebak. */
export function riskLabel(riskClass: string): string {
  return RISK_LABELS[riskClass as RiskClass] ?? riskClass;
}

/** Isi perintah yang berlaku: hasil modifikasi bila ada, selain itu usulan aslinya (U-07). */
export function effectiveInstruction(item: PendingActionItem): string {
  const modified = item.modified_text?.trim();
  return modified ? modified : item.original_recommendation;
}

/** Merangkai daftar menjadi frasa: "a, b, dan c". */
function joinPhrases(parts: string[]): string {
  if (parts.length <= 1) return parts.join("");
  return `${parts.slice(0, -1).join(", ")}, dan ${parts[parts.length - 1]}`;
}

/**
 * Kalimat pembuka bagian situasi.
 *
 * Susunannya tetap; yang berubah hanya angkanya, dan seluruh angka itu diulang sebagai
 * angka pada tabel di bawah kalimat ini. Bagian yang tidak boleh dibaca pengguna
 * dilewatkan, bukan diisi nol.
 */
export function situationSentence(brief: DailyBrief): string | null {
  const parts: string[] = [];
  if (brief.incidents_recent !== null) {
    parts.push(`tercatat ${brief.incidents_recent} kejadian`);
  }
  if (brief.active_warnings !== null) {
    parts.push(`${brief.active_warnings} peringatan dini masih berstatus aktif`);
  }
  if (brief.top_area) {
    parts.push(
      `wilayah dengan sel risiko tertinggi adalah ${brief.top_area.kecamatan} ` +
        `pada skor ${brief.top_area.risk_score} (${riskLabel(brief.top_area.risk_class)})`,
    );
  }
  if (parts.length === 0) return null;

  return (
    `Dalam ${brief.window_hours} jam terakhir sampai ${formatBriefDate(brief.brief_date)} ` +
    `pukul ${brief.brief_time} WIB, ${joinPhrases(parts)}.`
  );
}

/** Kalimat pembuka bagian ancaman menonjol, beserta jam rawannya. */
export function threatSentence(brief: DailyBrief): string | null {
  const first = brief.top_threats[0];
  if (!first) return null;

  const hours = first.time_window ? ` pada jam ${first.time_window}` : "";
  return (
    `Ancaman paling menonjol adalah ${first.threat_type} di ${first.kecamatan}${hours}, ` +
    `dengan skor ${first.risk_score} (${riskLabel(first.risk_class)}).`
  );
}

/** Kalimat pembuka bagian yang menuntut keputusan pimpinan. */
export function decisionSentence(brief: DailyBrief): string | null {
  if (brief.pending_recommendations === null) return null;
  if (brief.pending_recommendations === 0) {
    return "Tidak ada rekomendasi yang menunggu keputusan.";
  }

  const functions = brief.pending_by_function.map((row) => row.recommended_function);
  const forWhom = functions.length > 0 ? ` untuk fungsi ${joinPhrases(functions)}` : "";
  return `${brief.pending_recommendations} rekomendasi menunggu keputusan${forWhom}.`;
}

/** Kalimat pembuka bagian yang menuntut tindakan lapangan. */
export function actionSentence(brief: DailyBrief): string | null {
  if (brief.pending_actions === null) return null;
  if (brief.pending_actions === 0) {
    return "Seluruh keputusan yang telah disetujui sudah ditindaklanjuti di lapangan.";
  }

  return (
    `${brief.pending_actions} keputusan sudah disetujui atau dimodifikasi, ` +
    "tetapi belum memiliki tindakan operasional."
  );
}

export const getDailyBrief = () => apiGet<DailyBrief>("/brief/daily");
