import { apiGet } from "./api";

/**
 * Daftar laporan dari ketiga kanal.
 *
 * Ketiganya dibiarkan **terpisah**, tidak dilebur menjadi satu tipe. Godaannya besar —
 * ketiganya sama-sama "laporan" dan sama-sama punya tanggal, jenis, dan wilayah — tetapi
 * keandalannya berbeda: kejadian sudah terverifikasi petugas, laporan intelijen membawa
 * penilaian keandalan sendiri, dan laporan masyarakat bisa jadi belum diperiksa siapa pun.
 * Tipe gabungan akan membuat perbedaan itu hilang tepat di tempat ia paling penting.
 */

export type CrimeRow = {
  code: string;
  incident_type: string;
  occurred_at: string;
  incident_date: string;
  /** null bila jam tidak tercatat pada Laporan Polisi — 21,9% data asli Pusiknas. */
  incident_time: string | null;
  time_known: boolean;
  location_type: string | null;
  modus: string | null;
  target_type: string | null;
  status: string | null;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string | null;
  grid_id: string | null;
};

export type AttachmentRow = {
  attachment_id: string;
  kind: string;
  media_type: string;
  byte_size: number;
  metadata_stripped_with: string;
  created_at: string;
  purged_at: string | null;
  available: boolean;
};

export type CitizenRow = {
  code: string;
  category: string;
  description: string | null;
  reported_at: string;
  incident_time: string | null;
  status: string;
  kecamatan: string | null;
  kelurahan: string | null;
  location_text: string | null;
  urgency_score: number | null;
  verification_score: number | null;
  /** Dari mana koordinat laporan berasal — `KECAMATAN_CENTROID` atau `REPORTER_GPS`. */
  coordinate_source: string;
  /** Cacah lampiran yang berkasnya masih ada. Isinya diambil terpisah. */
  attachments: number;
};

export type IntelRow = {
  code: string;
  category: string;
  report_date: string;
  reliability: string | null;
  confidence: number | null;
  urgency: number | null;
  impact: string | null;
  status: string | null;
  kecamatan: string | null;
};

export type Page<T> = {
  data: T[];
  pagination: { page: number; page_size: number; total_items: number; total_pages: number };
};

type Query = Record<string, string | number | undefined>;

function search(query: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    // Nilai kosong tidak dikirim: sebagian endpoint memperlakukan string kosong sebagai
    // penyaring yang tidak cocok dengan apa pun, sehingga daftarnya menjadi kosong tanpa
    // ada yang tampak salah di layar.
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text === "" ? "" : `?${text}`;
}

export const getCrimes = (query: Query = {}) => apiGet<Page<CrimeRow>>(`/crimes${search(query)}`);

export const getCitizenReports = (query: Query = {}) =>
  apiGet<Page<CitizenRow>>(`/citizen-reports${search(query)}`);

export const getIntelligenceReports = (query: Query = {}) =>
  apiGet<Page<IntelRow>>(`/intelligence-reports${search(query)}`);

/** Jam kejadian untuk tabel: "13:51", atau tanda bahwa jam memang tidak tercatat. */
export const JAM_TIDAK_TERCATAT = "jam tidak tercatat";

export function jamKejadian(row: Pick<CrimeRow, "incident_time" | "time_known">): string {
  return row.time_known && row.incident_time ? row.incident_time.slice(0, 5) : JAM_TIDAK_TERCATAT;
}
