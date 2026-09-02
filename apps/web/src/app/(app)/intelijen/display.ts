import type { IntelligenceRow } from "@/lib/intel";

/**
 * Pembantu tampilan layar Laporan Intelijen — murni, tanpa pemanggilan API.
 *
 * Dipisahkan dari `lib/intel.ts` dengan sengaja: modul itu memanggil `lib/api.ts`, yang
 * membaca cookie sesi dan hanya hidup di server. Semua yang ada di sini adalah pemilihan
 * dan pemformatan, sehingga dapat diuji langsung tanpa jaringan maupun sesi.
 *
 * Tidak ada satu pun fungsi di sini yang menghitung ulang angka atau menilai laporan.
 * Jumlah pada penyaring, paginasi, dan penyaringan wilayah datang jadi dari backend.
 */

/** Keadaan layar yang hidup di URL, bukan di state klien. */
export type IntelligenceSelection = {
  status: string | null;
  category: string | null;
  page: number;
  selected: string | null;
};

/** Membaca keadaan layar dari parameter alamat, dengan nilai jatuhan yang aman. */
export function readSelection(
  params: Record<string, string | string[] | undefined>,
): IntelligenceSelection {
  const text = (value: string | string[] | undefined): string | null =>
    typeof value === "string" && value.trim() !== "" ? value.trim() : null;

  const requestedPage = Number.parseInt(text(params.halaman) ?? "", 10);

  return {
    status: text(params.status)?.toUpperCase() ?? null,
    category: text(params.kategori),
    // Halaman di luar akal (0, negatif, bukan angka) dikembalikan ke 1, bukan diteruskan
    // ke backend sebagai galat di tengah paparan.
    page: Number.isFinite(requestedPage) && requestedPage > 0 ? requestedPage : 1,
    selected: text(params.dipilih),
  };
}

/**
 * Tautan ke satu keadaan layar.
 *
 * Mengubah penyaring selalu mengembalikan daftar ke halaman pertama dan melepas laporan
 * yang sedang dibuka: laporan itu bisa saja tidak lagi termasuk hasil penyaringan, dan
 * membiarkannya terbuka akan menampilkan rincian yang tidak ada di daftar sebelahnya.
 */
export function intelligenceHref(
  current: IntelligenceSelection,
  change: Partial<IntelligenceSelection>,
): string {
  const filterChanged = "status" in change || "category" in change;
  const next: IntelligenceSelection = {
    ...current,
    ...(filterChanged ? { page: 1, selected: null } : {}),
    ...change,
  };

  const params = new URLSearchParams();
  if (next.status) params.set("status", next.status);
  if (next.category) params.set("kategori", next.category);
  if (next.page > 1) params.set("halaman", String(next.page));
  if (next.selected) params.set("dipilih", next.selected);

  const suffix = params.toString();
  return suffix ? `/intelijen?${suffix}` : "/intelijen";
}

/** Memilih nilai penyaring yang sedang aktif berarti melepasnya. */
export function toggled(current: string | null, value: string): string | null {
  return current === value ? null : value;
}

/**
 * Laporan yang rinciannya ditampilkan.
 *
 * Tautan usang atau laporan di luar halaman yang dimuat jatuh kembali ke laporan pertama —
 * layar tidak pernah terbuka dengan panel rincian kosong saat paparan.
 */
export function selectReport(
  rows: IntelligenceRow[],
  requested: string | null,
): IntelligenceRow | null {
  return rows.find((row) => row.code === requested) ?? rows[0] ?? null;
}

/** Nama wilayah selengkap yang tercatat. */
export function areaOf(row: IntelligenceRow): string {
  return row.kelurahan ? `${row.kecamatan} — ${row.kelurahan}` : row.kecamatan;
}

/** Nilai kamus, dengan nilai mentah sebagai jatuhan bila belum punya padanan Indonesia. */
export function labelOf(labels: Record<string, string>, value: string | null): string {
  if (!value) return "Tidak dicatat";
  return labels[value] ?? value;
}

/** Tanggal laporan dalam bentuk yang enak dibaca. */
export function formatDate(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

/**
 * Angka penilaian 0–100 beserta satuannya.
 *
 * Selalu disertai penyebut "/100" karena angka telanjang seperti "78" akan terbaca sebagai
 * jumlah, bukan sebagai skala. Nilai yang tidak dicatat ditulis sebagai "—", bukan 0:
 * tidak dicatat berbeda dari dinilai nol.
 */
export function scoreText(value: number | null): string {
  return value === null ? "—" : `${value}/100`;
}

/** Kalimat cakupan halaman: baris ke berapa sampai ke berapa, dari berapa. */
export function pageRangeText(page: number, pageSize: number, total: number): string {
  if (total === 0) return "tidak ada laporan yang cocok";
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return `laporan ${first}–${last} dari ${total}`;
}
