import { type NextRequest, NextResponse } from "next/server";
import { ACCESS_COOKIE } from "@/lib/session";

/**
 * Melindungi seluruh halaman aplikasi.
 *
 * Ini **kenyamanan**, bukan pengamanan: otorisasi sesungguhnya ditegakkan backend pada
 * setiap permintaan (CLAUDE.md §15). Melewati middleware ini tidak memberi akses data.
 */
export function middleware(request: NextRequest) {
  if (request.cookies.get(ACCESS_COOKIE)) return NextResponse.next();

  const target = new URL("/masuk", request.url);
  target.searchParams.set("lanjut", request.nextUrl.pathname);
  return NextResponse.redirect(target);
}

export const config = {
  matcher: ["/((?!masuk|api|_next/static|_next/image|favicon.ico).*)"],
};
