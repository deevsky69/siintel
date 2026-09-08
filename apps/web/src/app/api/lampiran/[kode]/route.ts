import { type NextRequest, NextResponse } from "next/server";
import { BASE_URL } from "@/lib/api";
import { readSession } from "@/lib/session";

/**
 * Daftar lampiran satu laporan — keterangannya, bukan isinya.
 *
 * Dipanggil dari peramban ketika petugas membuka panel lampiran, bukan saat daftar
 * laporan digambar. Mengambilnya untuk setiap baris berarti satu permintaan per laporan
 * pada setiap pemuatan halaman, untuk data yang hampir selalu tidak jadi dilihat.
 *
 * Kewenangan tetap diputuskan API. Rute ini hanya menyeberangkan token sesi yang sudah ada,
 * karena cookie `httpOnly` milik aplikasi web tidak dapat dilampirkan JavaScript ke
 * permintaan lintas alamat.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ kode: string }> },
): Promise<Response> {
  const { kode } = await params;
  const session = await readSession();
  if (session === null) return NextResponse.json({ data: [] }, { status: 401 });

  const upstream = await fetch(
    `${BASE_URL}/api/v1/citizen-reports/${encodeURIComponent(kode)}/attachments`,
    { headers: { Authorization: `Bearer ${session.accessToken}` }, cache: "no-store" },
  );

  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store, private" },
  });
}
