import { apiGet } from "./api";

/**
 * Kanal masyarakat (TASK 024) — laporan masyarakat dan ringkasan sinyalnya.
 *
 * Bentuk data mengikuti `apps/api/.../routers/community.py`.
 *
 * Satu hal yang **wajib ikut tampil** di layar dan tidak boleh dihaluskan: laporan
 * masyarakat pada prototipe ini **belum memengaruhi risk score sama sekali**. Spesifikasi
 * §4 mensyaratkan laporan melewati klasifikasi, deteksi duplikasi, deteksi spam,
 * pengelompokan lokasi, penilaian urgensi, dan validasi operator/analis lebih dulu —
 * tidak satu pun tahapan itu sudah dibangun. Karena itu `basis` dari API dibawa apa adanya
 * ke atas seluruh angka, seperti pada Evaluation Center (CLAUDE.md §27).
 *
 * Masyarakat **bukan** peran RBAC: kanalnya tanpa akun dan tanpa identitas pelapor
 * (docs/14 §3 dan §6, keputusan pemilik proyek 1 September 2026). Karena itu tidak ada
 * satu pun bentuk data di berkas ini yang memuat nama, kontak, atau tanda pengenal.
 */

/** Tahapan penanganan laporan (docs/02 §22, config/taxonomy `status_citizen_report`). */
export const REPORT_STATUSES = [
  "RECEIVED",
  "VERIFIED",
  "FORWARDED",
  "IN_PROGRESS",
  "CLOSED",
] as const;

export type ReportStatus = (typeof REPORT_STATUSES)[number];

export const REPORT_STATUS_LABELS: Record<string, string> = {
  RECEIVED: "Diterima",
  VERIFIED: "Diverifikasi",
  FORWARDED: "Diteruskan",
  IN_PROGRESS: "Ditangani",
  CLOSED: "Selesai",
};

/** Arti tiap tahapan, supaya terbaca tanpa membuka SOP. */
export const REPORT_STATUS_HINTS: Record<string, string> = {
  RECEIVED: "Laporan masuk, belum diperiksa petugas",
  VERIFIED: "Isi laporan sudah diperiksa petugas",
  FORWARDED: "Diteruskan ke fungsi atau Polsek terkait",
  IN_PROGRESS: "Sedang ditangani di lapangan",
  CLOSED: "Penanganan laporan ditutup",
};

/**
 * Kelas Tailwind per tahapan, ditulis utuh.
 *
 * Tailwind memindai kode sumber sebagai teks; kelas yang dirangkai saat berjalan
 * (`${x}/15`) tidak akan pernah ikut terbangun.
 */
export const REPORT_STATUS_CLASSES: Record<string, string> = {
  RECEIVED: "bg-risk-high/20 text-risk-high",
  VERIFIED: "bg-accent/15 text-accent",
  FORWARDED: "bg-risk-low/20 text-risk-low",
  IN_PROGRESS: "bg-accent/20 text-accent-soft",
  CLOSED: "bg-risk-moderate/20 text-risk-moderate",
};

export type CitizenReportRow = {
  code: string;
  reported_at: string;
  /** `null` bila pelapor tidak mengetahui waktu kejadian — kolomnya memang nullable. */
  incident_time: string | null;
  category: string;
  description: string | null;
  location_text: string | null;
  /** Nilai sintetis berstatus DEMO, bukan hasil penilaian model. */
  urgency_score: number | null;
  verification_score: number | null;
  status: string;
  /** `null` bila laporan belum tertaut ke sel grid; lokasinya tidak ditebak. */
  kecamatan: string | null;
  kelurahan: string | null;
  polsek: string | null;
  grid_id: string | null;
  /**
   * Dari mana koordinat laporan berasal — `KECAMATAN_CENTROID` atau `REPORTER_GPS`.
   *
   * Wajib ditampilkan di mana pun titiknya dipakai. Sepasang angka tidak menyatakan
   * asal-usulnya, dan titik pusat kecamatan berjarak kilometer dari tempat kejadian.
   */
  coordinate_source: string;
  /** Cacah lampiran yang berkasnya masih ada. Isinya diambil terpisah saat dibuka. */
  attachments: number;
};

export type TopArea = { kecamatan: string; polsek: string | null; total: number };

export type FeedbackBlock = {
  total: number;
  per_type: Record<string, number>;
  per_status: Record<string, number>;
};

export type CommunitySummary = {
  total_reports: number;
  per_status: Record<string, number>;
  per_category: Record<string, number>;
  top_areas: TopArea[];
  recent_reports: CitizenReportRow[];
  unmapped_reports: number;
  unmapped_basis: string;
  /** `null` bila peran pengguna tidak memiliki `community_feedback:read`. */
  feedback: FeedbackBlock | null;
  status: string;
  basis: string;
};

export type CitizenReportPage = {
  data: CitizenReportRow[];
  pagination: { page: number; page_size: number; total_items: number; total_pages: number };
  status: string;
  basis: string;
};

/** Jenis umpan balik (config/taxonomy `feedback_type`). */
export const FEEDBACK_TYPE_LABELS: Record<string, string> = {
  COMPLAINT: "Keluhan",
  INFORMATION: "Informasi",
  CORRECTION: "Koreksi",
  APPRECIATION: "Apresiasi",
};

/** Label yang aman untuk nilai apa pun: nilai tak dikenal ditampilkan apa adanya. */
export function labelOf(labels: Record<string, string>, value: string): string {
  return labels[value] ?? value;
}

/** Waktu ringkas gaya Indonesia; `null` dinyatakan, bukan diisi tanda hubung diam-diam. */
export function formatMoment(value: string | null): string {
  if (!value) return "tidak diketahui";
  return new Date(value).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Jakarta",
  });
}

/** Wilayah laporan; laporan tanpa tautan grid dinyatakan sebagai belum terpetakan. */
export function areaOf(report: CitizenReportRow): string {
  if (!report.kecamatan) return "belum terpetakan";
  return report.kelurahan ? `${report.kelurahan}, ${report.kecamatan}` : report.kecamatan;
}

export const getCommunitySummary = () => apiGet<CommunitySummary>("/community/summary");

/**
 * Daftar laporan sesuai penyaringan pada URL.
 *
 * Nilai penyaring tetap di-encode di sini meskipun halaman sudah memvalidasinya terhadap
 * daftar yang dikenal: penyaringan yang sah adalah urusan backend, dan klien tidak boleh
 * menjadi satu-satunya yang menjaga bentuk permintaan.
 */
export function getCitizenReports(filters: {
  status?: string | null;
  category?: string | null;
  pageSize?: number;
}): Promise<CitizenReportPage> {
  const query = new URLSearchParams({ page_size: String(filters.pageSize ?? 25) });
  if (filters.status) query.set("status", filters.status);
  if (filters.category) query.set("category", filters.category);
  return apiGet<CitizenReportPage>(`/citizen-reports?${query.toString()}`);
}
