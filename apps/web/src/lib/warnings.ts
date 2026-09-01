import { apiGet, apiPost } from "./api";
import type { RiskClass } from "./risk";

/**
 * Data peringatan dini dan prediksi sumbernya (TASK 111).
 *
 * Bentuk data mengikuti `apps/api/.../routers/intelligence.py`. Halaman peringatan
 * membutuhkan lebih banyak kolom daripada ringkasan dashboard — antara lain
 * `threshold_version`, `created_at`, dan batas jendela waktu — sehingga tipenya
 * ditulis lengkap di sini, bukan meminjam bentuk ringkas milik dashboard.
 */

export type WarningStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";

/** Asal penjelasan: aturan yang dijalankan, atau kontribusi fitur dari model. */
export type FactorSource = "RULE" | "MODEL";

export type DominantFactor = {
  factor: string;
  contribution: number;
  source: FactorSource | string;
};

export type WarningDetail = {
  code: string;
  severity: string;
  threat_type: string;
  time_window: string | null;
  window_start: string | null;
  window_end: string | null;
  risk_score: number;
  confidence: number | null;
  status: string;
  created_at: string;
  kecamatan: string;
  kelurahan: string | null;
  grid_id: string | null;
  prediction_code: string;
  threshold_version: string | null;
};

export type PredictionDetail = {
  code: string;
  prediction_date: string;
  forecast_horizon: string;
  threat_type: string;
  time_window: string | null;
  risk_score: number;
  confidence: number | null;
  dominant_factors: DominantFactor[] | null;
  model_version: string | null;
  status: string;
  kecamatan: string;
  kelurahan: string | null;
  grid_id: string | null;
};

export type Pagination = {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type Page<T> = { data: T[]; pagination: Pagination };

/** Urutan status pada layar: yang belum ditangani lebih dahulu. */
export const WARNING_STATUSES: readonly WarningStatus[] = [
  "ACTIVE",
  "ACKNOWLEDGED",
  "RESOLVED",
] as const;

export const STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Aktif",
  ACKNOWLEDGED: "Sudah Diterima",
  RESOLVED: "Selesai",
};

/** Keterangan singkat tiap status, supaya pembaca layar tahu artinya tanpa membuka SOP. */
export const STATUS_HINTS: Record<string, string> = {
  ACTIVE: "Belum ditindaklanjuti petugas",
  ACKNOWLEDGED: "Sudah dibaca dan diakui penerimaannya",
  RESOLVED: "Sudah dinyatakan selesai",
};

/** Level peringatan dini pada CLAUDE.md §12: LOW, WATCH, WARNING, CRITICAL. */
export const SEVERITY_LABELS: Record<string, string> = {
  LOW: "Rendah",
  WATCH: "Waspada",
  WARNING: "Peringatan",
  CRITICAL: "Kritis",
};

/**
 * Pemetaan level peringatan ke tangga warna risiko.
 *
 * Level peringatan dan kelas risiko adalah dua tangga yang berbeda (§11 dan §12),
 * tetapi keduanya empat tingkat dan sejajar maknanya; pemetaan ini hanya menyangkut
 * warna di layar, bukan penetapan ambang.
 */
const SEVERITY_RISK: Record<string, RiskClass> = {
  LOW: "LOW",
  WATCH: "MODERATE",
  WARNING: "HIGH",
  CRITICAL: "CRITICAL",
};

export function severityRiskClass(severity: string): RiskClass {
  return SEVERITY_RISK[severity] ?? "MODERATE";
}

/** Label faktor penjelas: nama teknis dijadikan terbaca tanpa mengubah maknanya. */
export const FACTOR_LABELS: Record<string, string> = {
  historical_incident_density: "Kepadatan kejadian historis",
  recent_incident_trend: "Tren kejadian terkini",
  time_window_pattern: "Pola jendela waktu",
  spatial_concentration: "Konsentrasi spasial",
  patrol_coverage_gap: "Celah cakupan patroli",
  intelligence_signal: "Sinyal intelijen",
};

export function factorLabel(factor: string): string {
  return FACTOR_LABELS[factor] ?? factor.replaceAll("_", " ");
}

const WIB: Intl.DateTimeFormatOptions = {
  timeZone: "Asia/Jakarta",
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

/** Waktu WIB yang terbaca. Nilai kosong dijawab tanda pisah, bukan tanggal karangan. */
export function formatWib(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return `${parsed.toLocaleString("id-ID", WIB)} WIB`;
}

export const getWarningsByStatus = (status: WarningStatus) =>
  apiGet<Page<WarningDetail>>(`/warnings?status=${status}&page_size=50`);

/**
 * Seluruh prediksi yang dapat dimuat sekali jalan, dipakai untuk mencari prediksi
 * sumber sebuah peringatan.
 *
 * `/predictions` belum menyediakan penyaring `code`, sehingga penjelasan dicari dari
 * halaman yang dimuat. Bila prediksi sumbernya berada di luar halaman ini, layar
 * menyatakannya apa adanya — tidak menampilkan penjelasan pengganti.
 */
export const getPredictions = () => apiGet<Page<PredictionDetail>>("/predictions?page_size=200");

export function indexPredictions(rows: PredictionDetail[]): Map<string, PredictionDetail> {
  return new Map(rows.map((row) => [row.code, row]));
}

/* ------------------------------------------------------------------------- *
 * Tindak lanjut peringatan (acknowledge / resolve)
 * ------------------------------------------------------------------------- */

/**
 * Dua transisi status yang disediakan backend.
 *
 * Sumber kebenarannya `apps/api/.../routers/warning_actions.py`; yang ditulis ulang di
 * sini hanya cukup untuk memutuskan tombol mana yang pantas ditawarkan.
 */
export const WARNING_ACTIONS = ["acknowledge", "resolve"] as const;
export type WarningAction = (typeof WARNING_ACTIONS)[number];

/** Permission yang diperiksa backend untuk tiap transisi. */
export const ACTION_PERMISSIONS: Record<WarningAction, string> = {
  acknowledge: "warning:acknowledge",
  resolve: "warning:resolve",
};

/**
 * Status asal yang masih sah bagi tiap transisi — cerminan `ACKNOWLEDGEABLE_FROM` dan
 * `RESOLVABLE_FROM` pada backend.
 *
 * Salinan ini **bukan** pengaman: backend tetap menjawab 409 atas transisi yang tidak sah
 * (CLAUDE.md §21). Gunanya hanya agar layar tidak menawarkan tombol yang sudah pasti
 * ditolak. `ACTIVE` ikut boleh di-resolve karena kewajiban menerima lebih dahulu adalah
 * aturan SOP yang belum ditetapkan — lihat docstring `warning_actions.py`.
 */
const ALLOWED_FROM: Record<WarningAction, readonly string[]> = {
  acknowledge: ["ACTIVE"],
  resolve: ["ACTIVE", "ACKNOWLEDGED"],
};

/** Apakah sebuah transisi masih mungkin dari status saat ini. */
export function allowsTransition(status: string, action: WarningAction): boolean {
  return ALLOWED_FROM[action].includes(status);
}

/**
 * Bentuk respons kedua endpoint transisi (`_serialize` pada `warning_actions.py`).
 *
 * Hanya dipakai untuk memastikan panggilan berhasil; isi layar tetap dimuat ulang dari
 * `/warnings` setelah `revalidatePath`, bukan ditambal dari respons ini.
 */
export type WarningTransition = {
  code: string;
  status: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
};

/**
 * Mengirim transisi status peringatan.
 *
 * Kedua endpoint tidak menerima badan permintaan; objek kosong dikirim semata karena
 * `apiPost` selalu mengirim badan, dan FastAPI mengabaikannya (diperiksa: kode yang tidak
 * ada tetap dijawab 404, bukan 400).
 */
export const submitWarningAction = (code: string, action: WarningAction) =>
  apiPost<WarningTransition>(`/warnings/${encodeURIComponent(code)}/${action}`, {});
