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
  incident_time: string;
  location_type: string | null;
  modus: string | null;
  target_type: string | null;
  status: string | null;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string | null;
  grid_id: string | null;
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
