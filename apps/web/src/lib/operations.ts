import { apiGet, apiPost } from "./api";

/**
 * Tindakan operasional dan hasil nyatanya (TASK 131).
 *
 * Ini lengan umpan balik rantai tertutup pada CLAUDE.md §9 — bagian yang membuat sistem
 * tahu apakah keputusan pejabat benar-benar dijalankan dan apa akibatnya di lapangan:
 *
 * ```
 * … → REKOMENDASI → KEPUTUSAN → TINDAKAN OPERASIONAL → HASIL NYATA → EVALUASI
 * ```
 *
 * Bentuk data mengikuti `apps/api/.../routers/operations.py`; yang ditulis ulang di sini
 * hanya secukupnya untuk menyusun layar. Aturan yang sesungguhnya — tindakan hanya boleh
 * lahir dari keputusan `APPROVED`/`MODIFIED`, dan hasil hanya boleh dicatat sekali —
 * ditegakkan backend beserta trigger database, bukan berkas ini (CLAUDE.md §21).
 */

/** Status tindakan (docs/02 §14), searah dengan `operations.py`. */
export const ACTION_STATUSES = ["PLANNED", "ACTIVE", "COMPLETED", "CANCELLED"] as const;
export type ActionStatus = (typeof ACTION_STATUSES)[number];

/**
 * Status akhir: hasil nyata sudah tercatat dan backend tidak menerima perubahan lagi.
 *
 * Salinan ini **bukan** pengaman — backend menjawab 409 atas percobaan kedua. Gunanya
 * hanya agar layar tidak menawarkan formulir yang sudah pasti ditolak.
 */
export const FINAL_STATUSES: readonly string[] = ["COMPLETED", "CANCELLED"];

/** Dua status yang sah dikirim saat mencatat hasil (`ResultRequest` pada backend). */
export const RESULT_STATUSES = ["COMPLETED", "CANCELLED"] as const;
export type ResultStatus = (typeof RESULT_STATUSES)[number];

export const ACTION_STATUS_LABELS: Record<string, string> = {
  PLANNED: "Direncanakan",
  ACTIVE: "Sedang Berjalan",
  COMPLETED: "Selesai",
  CANCELLED: "Dibatalkan",
};

/** Keterangan singkat tiap status, supaya artinya terbaca tanpa membuka SOP. */
export const ACTION_STATUS_HINTS: Record<string, string> = {
  PLANNED: "Penugasan tercatat, belum dilaksanakan",
  ACTIVE: "Penugasan sedang berjalan di lapangan",
  COMPLETED: "Hasil nyata sudah tercatat",
  CANCELLED: "Penugasan dibatalkan beserta alasannya",
};

export type OperationRow = {
  code: string;
  status: string;
  start_at: string;
  end_at: string | null;
  /**
   * Sebelum berstatus akhir kolom ini berisi catatan penugasan; setelahnya berisi hasil
   * nyata di lapangan. Backend memakai satu kolom untuk keduanya, jadi layar harus
   * memberi label sesuai status — bukan menyebut catatan rencana sebagai "hasil".
   */
  result: string | null;
  unit_code: string;
  unit_name: string;
  unit_function: string;
  kecamatan: string | null;
  kelurahan: string | null;
  polsek: string | null;
  decision_code: string;
  decision: string;
  decision_at: string;
  recommendation_code: string;
  recommended_function: string;
  original_recommendation: string;
  modified_text: string | null;
};

export type PendingDecisionRow = {
  decision_code: string;
  decision: string;
  decision_at: string;
  recommendation_code: string;
  recommended_function: string;
  original_recommendation: string;
  modified_text: string | null;
  priority: string | null;
  kecamatan: string | null;
  polsek: string | null;
};

/**
 * Satuan yang dapat ditugaskan, apa adanya dari `/police-units`.
 *
 * Bentuknya tidak dipetakan ulang dengan sengaja: satu-satunya sumber daftar satuan
 * adalah endpoint ini, dan menyalin ke bentuk lain hanya menciptakan kemungkinan dua
 * daftar yang isinya berbeda.
 */
export type PoliceUnitRow = {
  code: string;
  unit_name: string;
  function: string;
  jurisdiction: string | null;
  status: string;
};

/** Label status satuan mengikuti `docs/02-data-dictionary.md` §`police_units.status`. */
export const UNIT_STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Aktif",
  STANDBY: "Standby",
};

type Pagination = { page: number; page_size: number; total_items: number; total_pages: number };
type Page<T> = { data: T[]; pagination: Pagination };

/**
 * Seluruh tindakan yang dapat dimuat sekali jalan.
 *
 * Dataset PoC berisi puluhan baris, sehingga satu halaman besar lebih sederhana daripada
 * paginasi di layar (CLAUDE.md §37). Bila kelak melewati batas ini, yang benar adalah
 * menambahkan paginasi — bukan menaikkan angkanya tanpa batas.
 */
export const getOperations = () => apiGet<Page<OperationRow>>("/operations?page_size=200");

/** Antrean kerja: keputusan `APPROVED`/`MODIFIED` yang belum melahirkan tindakan. */
export const getPendingDecisions = () =>
  apiGet<{ data: PendingDecisionRow[] }>("/operations/pending-decisions");

/**
 * Satuan yang dapat ditugaskan (`police_unit:read`).
 *
 * Diambil tanpa penyaring status: satuan berstatus `STANDBY` tetap boleh ditugaskan, dan
 * menyembunyikannya justru membuat petugas mengira satuan itu tidak ada. Yang benar
 * adalah menampilkan statusnya, bukan memangkas pilihannya.
 *
 * `scope_basis` ikut dibawa ke layar. Bagi pengguna Polsek, daftar ini memuat satuan yang
 * jurisdiction-nya bukan polseknya sendiri — dan alasannya harus terbaca, bukan tampak
 * seperti kebocoran cakupan.
 */
export const getPoliceUnits = () =>
  apiGet<{ data: PoliceUnitRow[]; scope_basis: string | null }>("/police-units");

/** Mencatat penugasan. Kewenangan `operation:write` diperiksa backend. */
export const createOperation = (body: {
  decision_code: string;
  unit_code: string;
  start_at?: string;
  notes?: string;
}) => apiPost<{ code: string; status: string; start_at: string }>("/operations", body);

/** Mencatat hasil nyata. Backend menolak perubahan kedua dengan 409. */
export const recordOperationResult = (
  code: string,
  body: { status: ResultStatus; result: string; end_at?: string },
) =>
  apiPost<{ code: string; status: string; result: string; end_at: string }>(
    `/operations/${encodeURIComponent(code)}/result`,
    body,
  );

/**
 * Isi perintah yang benar-benar berlaku di lapangan.
 *
 * Bila pejabat memodifikasi usulan, yang dijalankan adalah teks hasil penyesuaiannya —
 * bukan usulan mentah sistem. Usulan asli tidak ditimpa dan tetap ditampilkan
 * berdampingan, karena jejak "sistem mengusulkan apa, manusia memutuskan apa" adalah inti
 * rantai human-in-the-loop (CLAUDE.md §13).
 */
export function effectiveOrder(row: {
  decision: string;
  original_recommendation: string;
  modified_text: string | null;
}): { text: string; adjusted: boolean } {
  const modified = row.modified_text?.trim();
  if (row.decision === "MODIFIED" && modified) return { text: modified, adjusted: true };
  return { text: row.original_recommendation, adjusted: false };
}

/**
 * Membagi tindakan menurut ada-tidaknya hasil nyata.
 *
 * Pembagian ini yang paling berarti bagi rantai tertutup: yang belum berhasil dicatat
 * adalah lengan umpan balik yang masih menganga, dan itulah yang harus terlihat lebih
 * dahulu — bukan sekadar urutan tanggal.
 */
export function splitByProgress(rows: OperationRow[]): {
  awaitingResult: OperationRow[];
  withResult: OperationRow[];
} {
  return {
    awaitingResult: rows.filter((row) => !FINAL_STATUSES.includes(row.status)),
    withResult: rows.filter((row) => FINAL_STATUSES.includes(row.status)),
  };
}

/**
 * Mengubah nilai `<input type="datetime-local">` menjadi ISO ber-offset WIB.
 *
 * Kolom `start_at`/`end_at` bertipe `timestamptz`, sehingga waktu tanpa zona akan
 * dibandingkan dengan waktu berzona di backend dan gagal. Petugas mengisi jam dinding
 * WIB — itu yang dinyatakan eksplisit di sini, bukan disimpulkan dari zona waktu server
 * yang kebetulan menjalankan Next.
 *
 * Mengembalikan `null` bila bentuknya tidak dikenali, supaya pemanggilnya dapat meminta
 * pengguna memperbaiki isian alih-alih mengirim waktu karangan.
 */
export function wibIso(local: string): string | null {
  const trimmed = local.trim();
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(trimmed)) return null;
  return `${trimmed.length === 16 ? `${trimmed}:00` : trimmed}+07:00`;
}
