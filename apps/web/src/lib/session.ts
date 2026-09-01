import { cookies } from "next/headers";

/**
 * Sesi peramban.
 *
 * Token disimpan pada cookie `httpOnly` yang hanya dibaca server Next.js, bukan pada
 * `localStorage` maupun variabel JavaScript: skrip pihak ketiga tidak boleh dapat
 * membacanya (CLAUDE.md §23 — frontend tidak menyimpan secret).
 */

export const ACCESS_COOKIE = "predpol_access";
export const REFRESH_COOKIE = "predpol_refresh";

export type Session = {
  accessToken: string;
  refreshToken?: string;
};

export async function readSession(): Promise<Session | null> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value;
  if (!accessToken) return null;

  return { accessToken, refreshToken: store.get(REFRESH_COOKIE)?.value };
}

/** Atribut cookie yang dipakai seragam untuk kedua token. */
export function cookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: maxAgeSeconds,
  };
}
