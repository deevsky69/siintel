import { type NextRequest, NextResponse } from "next/server";
import { BASE_URL } from "@/lib/api";
import { readSession } from "@/lib/session";

/**
 * Unduhan .docx perkiraan singkat satu bulan ke depan (`GET /patrol-plan/outlook?format=docx`).
 *
 * Peramban tidak dapat melampirkan cookie `httpOnly` ke permintaan lintas alamat, jadi rute
 * ini menyeberangkan token sesi lalu meneruskan berkasnya apa adanya. Kewenangan
 * (`recommendation:read`) dan cakupan wilayah tetap diputuskan API.
 */
export async function GET(request: NextRequest): Promise<Response> {
  const session = await readSession();
  if (session === null) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const bulan = request.nextUrl.searchParams.get("bulan");
  const query = new URLSearchParams({ format: "docx" });
  if (bulan && /^\d{4}-\d{2}$/.test(bulan)) query.set("month", bulan);
  const upstream = await fetch(`${BASE_URL}/api/v1/patrol-plan/outlook?${query}`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: "no-store",
  });
  if (!upstream.ok) {
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store, private" },
    });
  }
  return new NextResponse(await upstream.arrayBuffer(), {
    status: 200,
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "Content-Disposition":
        upstream.headers.get("content-disposition") ?? 'attachment; filename="perkiraan.docx"',
      "Cache-Control": "no-store, private",
    },
  });
}
