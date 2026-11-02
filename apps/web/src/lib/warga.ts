/**
 * SIGAP WARGA — data publik (tanpa akun). Dipanggil dari Server Component; tidak membawa
 * sesi apa pun. Bentuk respons mengikuti `routers/public_areas.py` dan `routers/reviews.py`.
 */

const BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export type AreaLevel = "RENDAH" | "SEDANG" | "TINGGI";

export type AreaSummary = {
  kelurahan: string;
  kecamatan: string;
  polsek: string | null;
  total: number;
  level: AreaLevel;
  by_threat: Record<string, number>;
  by_month: number[];
  rating: number | null;
  rating_count: number;
};

export type KecamatanSummary = {
  kecamatan: string;
  total: number;
  kelurahan: number;
  by_threat: Record<string, number>;
  level: AreaLevel;
};

export type PublicSummary = {
  window_from: string;
  window_to: string;
  months: string[];
  threat_types: string[];
  level_edges: { low_max: number; high_min: number };
  areas: AreaSummary[];
  kecamatan: KecamatanSummary[];
  status: string;
  basis: string;
};

export type PublicReview = {
  code: string;
  kelurahan: string;
  kecamatan: string;
  rating: number;
  comment: string | null;
  submitted_at: string;
};

export type ReviewPage = {
  kelurahan: string;
  average: number | null;
  count: number;
  data: PublicReview[];
  basis: string;
};

export const LEVEL_LABEL: Record<AreaLevel, string> = {
  RENDAH: "Rendah",
  SEDANG: "Sedang",
  TINGGI: "Tinggi",
};

/** Kelas Tailwind per tingkat — tiga warna saja, supaya mudah dibaca sekilas. */
export const LEVEL_CLASS: Record<AreaLevel, string> = {
  RENDAH: "bg-risk-low/12 text-risk-low border-risk-low/30",
  SEDANG: "bg-risk-moderate/12 text-risk-moderate border-risk-moderate/30",
  TINGGI: "bg-risk-high/12 text-risk-high border-risk-high/30",
};

export const LEVEL_FILL: Record<AreaLevel, string> = {
  RENDAH: "rgb(18 120 86)",
  SEDANG: "rgb(196 110 10)",
  TINGGI: "rgb(184 30 52)",
};

export const THREAT_LABEL: Record<string, string> = {
  CURANMOR: "Pencurian kendaraan",
  CURAT: "Pencurian dengan pemberatan",
  CURAS: "Pencurian dengan kekerasan",
};

export function threatLabel(code: string): string {
  return THREAT_LABEL[code] ?? code;
}

const MONTHS_ID = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "Mei",
  "Jun",
  "Jul",
  "Agu",
  "Sep",
  "Okt",
  "Nov",
  "Des",
];

export function monthLabel(key: string): string {
  const month = Number(key.slice(5, 7));
  return MONTHS_ID[month - 1] ?? key;
}

export function longMonth(key: string): string {
  const long = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
  ]; // biome-ignore format: tabel bulan
  return `${long[Number(key.slice(5, 7)) - 1]} ${key.slice(0, 4)}`;
}

async function publicGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}/api/v1${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`API ${response.status} pada ${path}`);
  return (await response.json()) as T;
}

export const getPublicSummary = () => publicGet<PublicSummary>("/public/areas/summary");

export const getPublicReviews = (kelurahan: string) =>
  publicGet<ReviewPage>(`/public/reviews?kelurahan=${encodeURIComponent(kelurahan)}`);

/** Kelurahan dengan ulasan terbanyak dan terbaik — untuk sorotan beranda. */
export function highlightAreas(summary: PublicSummary, limit = 3): AreaSummary[] {
  return [...summary.areas]
    .filter((area) => area.rating_count > 0)
    .sort((a, b) => b.rating_count - a.rating_count || (b.rating ?? 0) - (a.rating ?? 0))
    .slice(0, limit);
}

// ---------------------------------------------------------------------------------------
// Berkas perkara (tahap 2, 2 November 2026): lacak laporan dan cek kendaraan.
// ---------------------------------------------------------------------------------------

export type CaseHistory = {
  stage: string;
  stage_label: string;
  changed_at: string;
  note: string | null;
};

export type CaseTrack = {
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
  vehicle: { plate: string | null; description: string | null; recovered: boolean } | null;
  history: CaseHistory[];
  is_dummy: boolean;
  basis: string;
};

export type VehicleCheck = {
  found: boolean;
  records: {
    crime_type: string;
    reported_month: string;
    kecamatan: string;
    recovered: boolean;
    is_dummy: boolean;
  }[];
  advice: string;
  basis: string;
};

export const CASE_STAGES = ["DITERIMA", "LIDIK", "SIDIK", "P21", "SP3", "SELESAI"] as const;
