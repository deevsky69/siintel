/**
 * Pengamanan tujuan pengalihan setelah masuk.
 *
 * Parameter `lanjut` berasal dari URL, sehingga penyerang dapat mengirim tautan seperti
 * `https://domain-resmi/masuk?lanjut=https://situs-palsu` — korban masuk dengan benar,
 * lalu dilempar ke situs tiruan. Itu jalur phishing yang justru meyakinkan karena
 * berawal dari domain yang sah.
 *
 * Karena itu hanya lintasan **relatif satu origin** yang diterima. Bentuk yang ditolak:
 *
 * - `https://situs-lain`  — origin lain
 * - `//situs-lain`        — protokol-relatif, tetap keluar origin
 * - `/\situs-lain`        — sebagian peramban memperlakukannya seperti `//`
 * - `javascript:…`        — bukan lintasan sama sekali
 */
export const DEFAULT_PATH = "/";

export function safeNextPath(candidate: string | null | undefined): string {
  if (!candidate) return DEFAULT_PATH;

  const path = candidate.trim();
  if (!path.startsWith("/")) return DEFAULT_PATH;
  if (path.startsWith("//") || path.startsWith("/\\")) return DEFAULT_PATH;

  return path;
}
