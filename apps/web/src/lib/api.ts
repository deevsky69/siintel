import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, cookieOptions, REFRESH_COOKIE, readSession } from "./session";

/**
 * Klien API sisi server.
 *
 * Seluruh permintaan ke backend berjalan **dari server Next.js**, bukan dari peramban:
 * token tidak pernah menyentuh JavaScript di sisi klien, dan alamat backend tidak perlu
 * terbuka ke publik saat demo di-deploy.
 *
 * Access token berumur pendek. Bila kedaluwarsa di tengah paparan, satu kali penyegaran
 * dicoba diam-diam sebelum pengguna dialihkan ke halaman masuk — paparan tidak boleh
 * terputus hanya karena token habis.
 */

const BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { Cookie: `predpol_refresh=${refreshToken}` },
    cache: "no-store",
  });
  if (!response.ok) return null;

  const body = (await response.json()) as { access_token: string };
  const store = await cookies();
  store.set(ACCESS_COOKIE, body.access_token, cookieOptions(60 * 60));
  return body.access_token;
}

async function request<T>(path: string, accessToken: string): Promise<T> {
  const response = await fetch(`${BASE_URL}/api/v1${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      error?: { code?: string; message?: string };
    } | null;
    throw new ApiError(
      response.status,
      body?.error?.code ?? "INTERNAL_ERROR",
      body?.error?.message ?? "Permintaan gagal.",
    );
  }

  return (await response.json()) as T;
}

/** Mengambil data dari API sebagai pengguna yang sedang masuk. */
export async function apiGet<T>(path: string): Promise<T> {
  const session = await readSession();
  if (!session) redirect("/masuk");

  try {
    return await request<T>(path, session.accessToken);
  } catch (error) {
    const expired = error instanceof ApiError && error.status === 401;
    if (!expired || !session.refreshToken) throw error;

    const renewed = await refreshAccessToken(session.refreshToken);
    if (!renewed) redirect("/masuk");
    return await request<T>(path, renewed);
  }
}

export { BASE_URL, REFRESH_COOKIE };
