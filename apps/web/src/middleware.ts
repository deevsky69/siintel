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

/** Halaman yang dilayani tanpa akun. Kanal laporan masyarakat ada di sini (docs/14 §3). */
const PUBLIC_PATHS = ["/masuk", "/beranda", "/lapor"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const signedIn = Boolean(request.cookies.get(ACCESS_COOKIE));

  if (PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`))) {
    return NextResponse.next();
  }

  if (signedIn) return NextResponse.next();

  if (pathname === "/") {
    return NextResponse.rewrite(new URL("/beranda", request.url));
  }

  const target = new URL("/masuk", request.url);
  target.searchParams.set("lanjut", pathname);
  return NextResponse.redirect(target);
}

export const config = {
  // `api` dikecualikan supaya rute BFF (`/api/auth/*`) tidak ikut dialihkan; backend
  // yang memeriksa kewenangannya.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
