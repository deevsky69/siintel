import { apiGet, apiPost } from "./api";

/**
 * Tombol darurat warga — bentuk `GET /panic` dan tindakan atasnya (8 Oktober 2026).
 *
 * "Memberi tahu" pada kanal ini berarti peristiwa muncul paling atas di antrean dan pada
 * spanduk merah setiap halaman — bukan dering ke ponsel yang aplikasinya tertutup.
 */
export type PanicRow = {
  code: string;
  pressed_at: string;
  status: "OPEN" | "ACKNOWLEDGED" | "CLOSED" | string;
  latitude: number | null;
  longitude: number | null;
  accuracy_m: number | null;
  kecamatan: string | null;
  kelurahan: string | null;
  polsek: string | null;
  note: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  closed_at: string | null;
  closed_by: string | null;
  closing_note: string | null;
};

export type PanicPage = { data: PanicRow[]; open_total: number; basis: string };

export const PANIC_ACTIONS = ["acknowledge", "close"] as const;
export type PanicAction = (typeof PANIC_ACTIONS)[number];

export const PANIC_STATUS_LABELS: Record<string, string> = {
  OPEN: "Belum diterima",
  ACKNOWLEDGED: "Sedang ditangani",
  CLOSED: "Selesai",
};

export const getPanicEvents = () => apiGet<PanicPage>("/panic?limit=200");

export const submitPanicAction = (code: string, action: PanicAction, note?: string) =>
  apiPost<PanicRow>(
    `/panic/${encodeURIComponent(code)}/${action}`,
    action === "close" ? { note: note?.trim() || null } : {},
  );

/** Tautan OpenStreetMap ke titik peranti — tanpa pustaka peta, cukup untuk menuju lokasi. */
export function mapLink(row: PanicRow): string | null {
  if (row.latitude === null || row.longitude === null) return null;
  return `https://www.openstreetmap.org/?mlat=${row.latitude}&mlon=${row.longitude}#map=17/${row.latitude}/${row.longitude}`;
}
