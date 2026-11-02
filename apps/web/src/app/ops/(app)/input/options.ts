/**
 * Bentuk data yang dioper dari halaman (server) ke ketiga formulir (klien).
 *
 * Berkas ini sengaja **tidak** mengimpor apa pun dari `@/lib`: modul di sana menarik
 * `@/lib/api`, dan modul itu memuat `next/headers` yang tidak boleh masuk bundel peramban.
 * Karena itu wilayah sudah dikelompokkan dan dilabeli di server, lalu dioper sebagai data
 * biasa — bukan dihitung ulang di klien.
 */

/** Satu pilihan isian: nilai tersimpan beserta labelnya dalam Bahasa Indonesia. */
export type Choice = { value: string; label: string };

/** Wilayah/sel grid, sudah dikelompokkan menurut Polsek untuk `<optgroup>`. */
export type LocationGroup = { polsek: string; options: Choice[] };

/** Gaya isian yang sama untuk ketiga formulir. */
export const FIELD =
  "mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent";

/** Gaya tombol simpan, sama dengan layar keputusan dan operasi. */
export const SUBMIT =
  "mt-4 rounded bg-accent/20 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-40";

export const HINT = "mt-1 block text-[10px] leading-relaxed text-ink-muted";

/**
 * Satu laporan masyarakat yang dapat ditriase, sudah disiapkan untuk ditampilkan.
 *
 * Wilayah dan waktu sudah dirangkai di server: laporan yang belum tertaut ke sel grid
 * dinyatakan "belum terpetakan", bukan ditebak ke sel terdekat (docs/02 §6).
 */
export type TriageReport = {
  code: string;
  label: string;
  status: string;
  statusLabel: string;
};
