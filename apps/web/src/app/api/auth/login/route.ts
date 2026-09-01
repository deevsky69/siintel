import { type NextRequest, NextResponse } from "next/server";
import { BASE_URL } from "@/lib/api";
import { ACCESS_COOKIE, cookieOptions, REFRESH_COOKIE } from "@/lib/session";

/**
 * Meneruskan permintaan masuk ke backend, lalu menyimpan token pada cookie httpOnly.
 *
 * Kredensial tidak pernah singgah di JavaScript peramban dan tidak pernah masuk log
 * Next.js: badan permintaan hanya diteruskan.
 */
export async function POST(request: NextRequest) {
  const credentials = await request.json();

  const upstream = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
    cache: "no-store",
  });

  const body = await upstream.json().catch(() => null);

  if (!upstream.ok) {
    return NextResponse.json(body ?? { error: { message: "Gagal masuk." } }, {
      status: upstream.status,
    });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(ACCESS_COOKIE, body.access_token, cookieOptions(60 * 60));

  // Refresh token milik backend diteruskan apa adanya agar sesi dapat diperpanjang.
  const upstreamCookie = upstream.headers.getSetCookie?.() ?? [];
  const refresh = upstreamCookie
    .find((entry) => entry.startsWith("predpol_refresh="))
    ?.split(";")[0]
    ?.replace("predpol_refresh=", "");
  if (refresh) {
    response.cookies.set(REFRESH_COOKIE, refresh, cookieOptions(60 * 60 * 24 * 7));
  }

  return response;
}
