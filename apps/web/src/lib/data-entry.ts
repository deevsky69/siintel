import { apiGet, apiPost } from "./api";

/**
 * Pintu masuk data (TASK 132) — kejadian, laporan intelijen, dan triase laporan masyarakat.
 *
 * Sampai layar `/input` ada, satu-satunya jalan data masuk ke sistem adalah proses seed.
 * Bentuk data di sini mengikuti `apps/api/.../routers/data_entry.py`.
 *
 * Dua hal yang **tidak** ditiru di berkas ini, dan sengaja:
 *
 * - **Kewenangan.** Yang menolak adalah backend. Menyembunyikan formulir dari peran yang
 *   tidak berwenang hanyalah kenyamanan (CLAUDE.md §21).
 * - **Daftar nilai yang sah.** Jenis ancaman, status, dan dampak diambil dari
 *   `/data-entry/options`, yang membacanya dari `config/taxonomy/mappings.yaml`. Menyalin
 *   daftarnya ke sini akan melahirkan taksonomi kedua yang diam-diam berbeda dari
 *   konfigurasi — persis yang dicegah oleh berkas taksonomi itu.
 *
 * Identitas korban/pelaku/saksi **tidak ada** pada bentuk data mana pun di sini.
 * Spesifikasi §6.1 menyatakan identitas tidak diperlukan untuk PoC, dan backend akan
 * membuang bidang seperti itu seandainya terkirim (CLAUDE.md §16).
 */

/** Satu pilihan isian: nilai tersimpan beserta labelnya dalam Bahasa Indonesia. */
export type Option = { value: string; label: string };

/**
 * Kosakata yang berasal dari basis data, bukan dari taksonomi.
 *
 * Setiap kunci bisa saja tidak ada: backend hanya memberikan saran dari tabel yang boleh
 * dibaca peran pengguna, dan sudah disaring menurut cakupan wilayahnya. Karena itu
 * tipenya opsional, bukan array kosong yang dipaksakan.
 */
export type EntrySuggestions = {
  location_type?: string[];
  modus?: string[];
  target_type?: string[];
  intelligence_category?: string[];
  reliability?: string[];
};

export type EntryOptions = {
  incident_type: Option[];
  crime_status: Option[];
  intelligence_status: Option[];
  citizen_report_status: Option[];
  impact: Option[];
  suggestions: EntrySuggestions;
  taxonomy_version: string;
  /** `FINAL` atau `PROPOSED` — dibaca dari konfigurasi, bukan ditulis di layar. */
  taxonomy_status: string;
  reference_time: string;
  demo_clock: boolean;
  /** Mengapa verifikasi laporan masyarakat bermakna; dibawa apa adanya ke layar. */
  verification_basis: string;
  /** Mengapa perpindahan status tidak dibatasi urutannya. */
  transition_basis: string;
};

export type LocationOption = {
  code: string;
  grid_id: string;
  polsek: string;
  kecamatan: string;
  kelurahan: string | null;
  latitude: number;
  longitude: number;
  location_type: string | null;
};

type Page<T> = {
  data: T[];
  pagination: { page: number; page_size: number; total_items: number; total_pages: number };
};

export type CrimeInput = {
  incident_type: string;
  incident_date: string;
  incident_time: string;
  location_code: string;
  location_type?: string;
  modus?: string;
  target_type?: string;
  status?: string;
};

export type CrimeCreated = {
  code: string;
  incident_type: string;
  occurred_at: string;
  status: string | null;
  location_code: string;
  kecamatan: string;
  kelurahan: string | null;
  polsek: string;
  grid_id: string;
};

export type IntelligenceInput = {
  report_date: string;
  category: string;
  location_code: string;
  reliability?: string;
  confidence?: number;
  urgency?: number;
  impact?: string;
  status?: string;
};

export type IntelligenceCreated = {
  code: string;
  report_date: string;
  category: string;
  status: string | null;
  impact: string | null;
  location_code: string;
  kecamatan: string;
  polsek: string;
  grid_id: string;
};

export type TriageResult = {
  code: string;
  status_before: string;
  status: string;
  category: string;
  kecamatan: string | null;
  polsek: string | null;
  verification_basis: string;
  transition_basis: string;
};

export const getEntryOptions = () => apiGet<EntryOptions>("/data-entry/options");

/**
 * Seluruh wilayah/grid yang boleh dibaca pengguna.
 *
 * Dataset PoC memuat 33 sel, jadi satu halaman cukup. Perlu diketahui saat membaca layar:
 * `location:read` bercakupan `ALL` untuk keempat peran (`config/rbac/permissions.yaml`),
 * sehingga akun Polsek pun menerima seluruh sel Jakarta Selatan di sini. Yang membatasi
 * penulisan adalah cakupan `crime:write`/`intelligence:write` di backend — dan sel di
 * luar wilayahnya dijawab "tidak ditemukan", bukan "tidak berwenang".
 */
export const getLocations = () => apiGet<Page<LocationOption>>("/locations?page_size=200");

export const createCrime = (body: CrimeInput) => apiPost<CrimeCreated>("/crimes", body);

export const createIntelligenceReport = (body: IntelligenceInput) =>
  apiPost<IntelligenceCreated>("/intelligence-reports", body);

export const updateReportStatus = (code: string, body: { status: string; note?: string }) =>
  apiPost<TriageResult>(`/citizen-reports/${encodeURIComponent(code)}/status`, body);

/**
 * Wilayah dikelompokkan menurut Polsek untuk `<optgroup>`.
 *
 * Bukan hiasan: daftar 33 sel yang datar membuat petugas Polsek Tebet mudah memilih sel
 * milik polsek lain, lalu menerima penolakan yang tampak seperti kesalahan sistem.
 * Mengelompokkannya membuat batas wilayah terlihat sebelum tombol ditekan.
 */
export function byPolsek(
  locations: LocationOption[],
): { polsek: string; rows: LocationOption[] }[] {
  const groups = new Map<string, LocationOption[]>();
  for (const row of locations) {
    const rows = groups.get(row.polsek);
    if (rows) rows.push(row);
    else groups.set(row.polsek, [row]);
  }

  return [...groups.entries()]
    .map(([polsek, rows]) => ({ polsek, rows }))
    .sort((a, b) => a.polsek.localeCompare(b.polsek, "id-ID"));
}

/** Label sebuah sel grid: cukup untuk dikenali tanpa membuka peta. */
export function locationLabel(row: LocationOption): string {
  const area = row.kelurahan ? `${row.kelurahan}, ${row.kecamatan}` : row.kecamatan;
  return `${area} · ${row.grid_id}`;
}

/**
 * Tanggal `YYYY-MM-DD` menurut waktu acuan aplikasi, untuk batas atas isian tanggal.
 *
 * Jam acuan demo beku pada 31 Desember 2025 (SDL-16). Memakai tanggal peramban akan
 * membuat isian yang wajar tampak "di masa depan" bagi backend — atau sebaliknya,
 * mengizinkan tanggal yang pasti ditolak. Backend tetap yang memutuskan; ini hanya agar
 * pemilih tanggal tidak menawarkan hari yang sudah pasti ditolak.
 */
export function referenceDate(referenceTime: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Jakarta",
  }).format(new Date(referenceTime));
}
