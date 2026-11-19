/**
 * Pembacaan masa berlaku JWT TANPA verifikasi — hanya untuk menjadwalkan penyegaran.
 *
 * Tanda tangan diverifikasi backend pada setiap permintaan; di sini token hanya dibaca
 * untuk tahu kapan ia kedaluwarsa, supaya middleware menyegarkannya SEBELUM komponen server
 * menerima 401. Tidak memakai `next/headers` agar dapat dipakai di middleware (edge runtime)
 * maupun di route handler.
 */

/** Detik Unix pada klaim `exp`, atau `null` bila token tidak terbaca. */
export function tokenExpiresAt(token: string): number | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
    const json = JSON.parse(decodeBase64(padded)) as { exp?: unknown };
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

/** Sisa umur token dalam detik (dibulatkan ke bawah, minimal 0); `fallback` bila tidak terbaca. */
export function tokenMaxAge(token: string, fallback: number, now = Date.now()): number {
  const exp = tokenExpiresAt(token);
  if (exp === null) return fallback;
  return Math.max(0, Math.floor(exp - now / 1000));
}

/** Benar bila token sudah habis atau akan habis dalam `withinSeconds`. */
export function tokenExpiringSoon(token: string, withinSeconds: number, now = Date.now()): boolean {
  const exp = tokenExpiresAt(token);
  if (exp === null) return true;
  return exp - now / 1000 <= withinSeconds;
}

function decodeBase64(value: string): string {
  if (typeof atob === "function") {
    const binary = atob(value);
    const bytes = Uint8Array.from(binary, (ch) => ch.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }
  return Buffer.from(value, "base64").toString("utf8");
}
