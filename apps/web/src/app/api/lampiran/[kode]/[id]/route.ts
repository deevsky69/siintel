import { type NextRequest, NextResponse } from "next/server";
import { BASE_URL } from "@/lib/api";
import { readSession } from "@/lib/session";

/**
 * Meneruskan berkas lampiran dari API ke peramban petugas.
 *
 * ## Mengapa berkasnya melewati sini
 *
 * Peramban tidak dapat memanggil API secara langsung: alamatnya tidak dibuka ke publik, dan
 * token sesi hidup di cookie `httpOnly` milik aplikasi web — bukan sesuatu yang dapat
 * dilampirkan JavaScript ke permintaan lintas alamat. Rute ini yang menyeberangkannya.
 *
 * ## Kewenangan tetap diputuskan API, bukan di sini
 *
 * Yang dikerjakan rute ini hanya meneruskan token sesi yang sudah ada. API-lah yang
 * memeriksa `citizen_report:write`, cakupan wilayah, dan masa retensi — dan API pula yang
 * menulis jejak audit. Memeriksa ulang di sini akan menciptakan aturan kedua yang harus
 * dijaga tetap sama, dan aturan kedua selalu berakhir berbeda.
 *
 * Status apa pun dari API diteruskan apa adanya: `404` untuk laporan di luar wilayah,
 * `410` untuk berkas yang sudah dimusnahkan retensi.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ kode: string; id: string }> },
): Promise<Response> {
  const { kode, id } = await params;
  const session = await readSession();
  if (session === null) return new NextResponse("Sesi berakhir.", { status: 401 });

  const upstream = await fetch(
    `${BASE_URL}/api/v1/citizen-reports/${encodeURIComponent(kode)}/attachments/${encodeURIComponent(id)}`,
    { headers: { Authorization: `Bearer ${session.accessToken}` }, cache: "no-store" },
  );

  if (!upstream.ok || upstream.body === null) {
    return new NextResponse(await upstream.text(), { status: upstream.status });
  }

  return new NextResponse(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/octet-stream",
      // Ditampilkan di layar, tidak diunduh ke cakram petugas: makin sedikit salinan data
      // pribadi yang tersebar, makin sedikit yang harus dijaga.
      "Content-Disposition": "inline",
      // Berkas ini data pribadi. Ia tidak boleh tersimpan di cache peramban bersama, dan
      // tidak boleh tertinggal di mesin yang dipakai bergantian.
      "Cache-Control": "no-store, private",
    },
  });
}
