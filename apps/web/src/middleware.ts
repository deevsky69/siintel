import { type NextRequest, NextResponse } from "next/server";
import { ACCESS_COOKIE } from "@/lib/session";

/**
 * Memisahkan halaman publik dari halaman aplikasi.
 *
 * Ini **kenyamanan**, bukan pengamanan: otorisasi sesungguhnya ditegakkan backend pada
 * setiap permintaan (CLAUDE.md §15). Melewati middleware ini tidak memberi akses data.
 *
 * Alamat `/` melayani dua hal yang berbeda menurut siapa yang membukanya:
 *
 * - **sudah masuk** → dashboard, seperti sebelumnya;
 * - **belum masuk** → halaman muka publik, lewat *rewrite* ke `/beranda`.
 *
 * Dipakai `rewrite`, bukan `redirect`, dengan sengaja: alamatnya tetap `/` sehingga
 * pengunjung tidak perlu tahu ada dua halaman di baliknya, dan tautan `/` yang dibagikan
 * tetap masuk akal bagi keduanya. Redirect akan mengubah alamat di bilah peramban dan
 * membuat "halaman muka" punya dua nama.
 */

/**
 * Sejak 2 November 2026 (SIGAP WARGA): seluruh jalur di luar `/ops` adalah halaman warga
 * tanpa akun; `/ops/...` adalah aplikasi kepolisian yang menuntut sesi, kecuali `/ops/masuk`.
 */
const OPS_PREFIX = "/ops";
const OPS_PUBLIC = ["/ops/masuk"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname !== OPS_PREFIX && !pathname.startsWith(`${OPS_PREFIX}/`)) {
    return NextResponse.next();
  }
  if (OPS_PUBLIC.some((path) => pathname === path || pathname.startsWith(`${path}/`))) {
    return NextResponse.next();
  }
  if (request.cookies.get(ACCESS_COOKIE)) return NextResponse.next();

  const target = new URL("/ops/masuk", request.url);
  target.searchParams.set("lanjut", pathname);
  return NextResponse.redirect(target);
}

export const config = {
  // `api` dikecualikan supaya rute BFF (`/api/auth/*`) tidak ikut dialihkan; backend
  // yang memeriksa kewenangannya.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
