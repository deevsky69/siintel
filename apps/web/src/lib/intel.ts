import { apiGet } from "./api";

/**
 * Laporan intelijen (TASK 033).
 *
 * ```text
 * GET /intelligence-reports?page=&page_size=&status=&category=
 * ```
 *
 * Bentuk data mengikuti `apps/api/.../routers/analytics.py`. Tidak ada satu angka pun yang
 * dihitung di berkas ini: jumlah pada penyaring, paginasi, dan penyaringan wilayah
 * seluruhnya berasal dari backend, karena cakupan wilayah adalah aturan otorisasi dan
 * tempatnya bukan di antarmuka (CLAUDE.md §21).
 *
 * Satu hal yang **wajib ikut terbaca** di layar dan tidak boleh dihaluskan: `reliability`,
 * `confidence`, dan `urgency` pada tabel ini adalah **penilaian yang dicatat pada laporan
 * oleh penyusunnya**, bukan keluaran model dan bukan hitungan sistem. Menampilkannya
 * bersebelahan dengan `confidence` milik prediksi — yang berasal dari mesin — akan membuat
 * keduanya terbaca sebagai hal yang sama (CLAUDE.md §27). Karena itu `assessment_basis`
 * dari API dibawa apa adanya ke layar.
 *
 * Berkas ini memanggil `lib/api.ts`, yang membaca cookie sesi, sehingga hanya boleh dipakai
 * dari server. Pembantu tampilan murni ada di `app/(app)/intelijen/display.ts`.
 */

/** Tahapan penanganan laporan intelijen (docs/02 §22, `status_intelligence`). */
export const INTELLIGENCE_STATUSES = ["NEW", "VERIFIED", "FOLLOWED_UP", "CLOSED"] as const;

export type IntelligenceStatus = (typeof INTELLIGENCE_STATUSES)[number];

export const INTELLIGENCE_STATUS_LABELS: Record<string, string> = {
  NEW: "Baru",
  VERIFIED: "Diverifikasi",
  FOLLOWED_UP: "Ditindaklanjuti",
  CLOSED: "Selesai",
};

/** Arti tiap tahapan, supaya terbaca tanpa membuka SOP. */
export const INTELLIGENCE_STATUS_HINTS: Record<string, string> = {
  NEW: "Laporan masuk, belum diverifikasi",
  VERIFIED: "Isi laporan sudah diperiksa petugas",
  FOLLOWED_UP: "Sudah ditindaklanjuti di lapangan",
  CLOSED: "Penanganan laporan ditutup",
};

/**
 * Kelas Tailwind per tahapan dan per dampak, ditulis utuh.
 *
 * Tailwind memindai kode sumber sebagai teks; kelas yang dirangkai saat berjalan
 * (`${x}/15`) tidak akan pernah ikut terbangun.
 */
export const INTELLIGENCE_STATUS_CLASSES: Record<string, string> = {
  NEW: "bg-risk-high/20 text-risk-high",
  VERIFIED: "bg-accent/15 text-accent",
  FOLLOWED_UP: "bg-accent/20 text-accent-soft",
  CLOSED: "bg-risk-moderate/20 text-risk-moderate",
};

/** Dampak yang dinyatakan pelapor (docs/02 §22, `impact`). */
export const IMPACT_LABELS: Record<string, string> = {
  LOW: "Rendah",
  MEDIUM: "Sedang",
  HIGH: "Tinggi",
  CRITICAL: "Kritis",
};

export const IMPACT_CLASSES: Record<string, string> = {
  LOW: "bg-risk-low/20 text-risk-low",
  MEDIUM: "bg-risk-moderate/20 text-risk-moderate",
  HIGH: "bg-risk-high/20 text-risk-high",
  CRITICAL: "bg-risk-critical/20 text-risk-critical",
};

/**
 * Arti skala keandalan sumber.
 *
 * Ini penjelasan skala A/B/C sebagaimana dicatat pada dataset (docs/02 §4), **bukan**
 * penilaian sistem atas laporannya: tidak ada mekanisme yang memverifikasi nilai ini.
 */
export const RELIABILITY_HINTS: Record<string, string> = {
  A: "Sumber terpercaya",
  B: "Sumber cukup terpercaya",
  C: "Sumber perlu pendalaman",
};

export type IntelligenceRow = {
  code: string;
  report_date: string;
  category: string;
  reliability: string | null;
  confidence: number | null;
  urgency: number | null;
  impact: string | null;
  status: string | null;
  location_code: string;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string | null;
  grid_id: string;
};

/** Satu pilihan penyaring beserta jumlahnya di dalam cakupan pengguna. */
export type IntelligenceFacet = { value: string; reports: number };

export type IntelligencePage = {
  data: IntelligenceRow[];
  pagination: { page: number; page_size: number; total_items: number; total_pages: number };
  filters: {
    status: IntelligenceFacet[];
    category: IntelligenceFacet[];
    reliability: IntelligenceFacet[];
  };
  source: { table: string; reports_in_scope: number; scope: string | null };
  scope_basis: string;
  /** Mengapa jumlah pada penyaring berbeda dari jumlah baris yang tampil. */
  filter_basis: string;
  /** Bahwa reliability/confidence/urgency dicatat manusia, bukan dihitung mesin. */
  assessment_basis: string;
};

export type IntelligenceQuery = {
  status?: string | null;
  category?: string | null;
  page?: number;
  pageSize?: number;
};

/** Mengambil satu halaman laporan intelijen sesuai penyaring yang berlaku. */
export function getIntelligenceReports(query: IntelligenceQuery = {}): Promise<IntelligencePage> {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.category) params.set("category", query.category);
  params.set("page", String(query.page ?? 1));
  params.set("page_size", String(query.pageSize ?? 25));

  return apiGet<IntelligencePage>(`/intelligence-reports?${params.toString()}`);
}
