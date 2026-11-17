import { type NextRequest, NextResponse } from "next/server";
import { ACCESS_COOKIE, cookieOptions, REFRESH_COOKIE } from "@/lib/session";
import { tokenExpiringSoon, tokenMaxAge } from "@/lib/token";

/**
 * Penjaga sesi untuk aplikasi kepolisian.
 *
 * - **sudah masuk** → lanjut; bila token akses hampir habis, disegarkan DI SINI, karena hanya
 *   middleware dan route handler yang boleh memasang cookie. Token baru dipasang pada
 *   respons dan sekaligus disuntikkan ke header permintaan, sehingga komponen server pada
 *   render yang sama sudah memakai token baru — tanpa 401, tanpa percobaan ulang.
 * - **belum masuk / tidak dapat disegarkan** → halaman masuk, dengan `?lanjut=` ke tujuan.
 *
 * Latar (audit 15 November 2026): token akses API berlaku 15 menit sedangkan cookie-nya
 * dulu 60 menit. Antara menit 15 dan 60 setiap permintaan halaman ditolak 401 dulu, lalu
 * token disegarkan dari komponen server, dan penyimpanannya gagal ("Cookies can only be
 * modified in a Server Action or Route Handler") — siklus itu berulang pada setiap klik.
 *
 * Sejak 2 November 2026 (SIGAP BERSAMA): seluruh jalur di luar `/ops` adalah halaman warga
 * tanpa akun; `/ops/...` adalah aplikasi kepolisian yang menuntut sesi, kecuali `/ops/masuk`.
 */

const OPS_PREFIX = "/ops";
const OPS_PUBLIC = ["/ops/masuk"];
//: Disegarkan bila sisa umur token kurang dari ini (detik) — satu render jauh di bawahnya.
const REFRESH_WITHIN_SECONDS = 90;
const BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname !== OPS_PREFIX && !pathname.startsWith(`${OPS_PREFIX}/`)) {
    return NextResponse.next();
  }
  if (OPS_PUBLIC.some((path) => pathname === path || pathname.startsWith(`${path}/`))) {
    return NextResponse.next();
  }

  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  if (access && !tokenExpiringSoon(access, REFRESH_WITHIN_SECONDS)) {
    return NextResponse.next();
  }
  if (refresh) {
    const renewed = await refreshAccessToken(refresh);
    if (renewed) return withRenewedToken(request, renewed);
  }

  const target = new URL("/ops/masuk", request.url);
  target.searchParams.set("lanjut", pathname);
  const response = NextResponse.redirect(target);
  response.cookies.delete(ACCESS_COOKIE);
  if (refresh) response.cookies.delete(REFRESH_COOKIE);
  return response;
}

async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  try {
    const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { Cookie: `${REFRESH_COOKIE}=${refreshToken}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { access_token?: string };
    return typeof body.access_token === "string" ? body.access_token : null;
  } catch {
    return null;
  }
}

/** Lanjut dengan token baru: dipasang pada respons DAN pada header permintaan ini. */
function withRenewedToken(request: NextRequest, token: string): NextResponse {
  const headers = new Headers(request.headers);
  const others = request.cookies
    .getAll()
    .filter((cookie) => cookie.name !== ACCESS_COOKIE)
    .map((cookie) => `${cookie.name}=${cookie.value}`);
  headers.set("cookie", [...others, `${ACCESS_COOKIE}=${token}`].join("; "));
  const response = NextResponse.next({ request: { headers } });
  response.cookies.set(ACCESS_COOKIE, token, cookieOptions(tokenMaxAge(token, 15 * 60)));
  return response;
}

export const config = {
  // `api` dikecualikan supaya rute BFF (`/api/auth/*`) tidak ikut dialihkan; backend
  // yang memeriksa kewenangannya.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
