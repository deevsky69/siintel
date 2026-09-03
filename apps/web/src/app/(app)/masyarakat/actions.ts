"use server";

import { revalidatePath } from "next/cache";
import type { StatusState } from "@/app/(app)/laporan-petugas/actions";
import { ApiError, apiPost } from "@/lib/api";

/**
 * Triase laporan masyarakat, dijalankan dari daftar laporannya sendiri.
 *
 * Memakai endpoint yang sama dengan tab Triase pada `Input Data`
 * (`POST /citizen-reports/{code}/status`); yang berbeda hanya tempat pemanggilannya.
 * Aturan perpindahan status hidup di backend, dan tidak diduplikasi di sini — aturan
 * yang ditulis dua kali akan menyimpang, dan yang menyimpang di layar akan menang atas
 * yang benar di server sampai ada yang menyadarinya.
 */
export async function changeReportStatus(
  _previous: StatusState,
  form: FormData,
): Promise<StatusState> {
  const code = String(form.get("code") ?? "").trim();
  const status = String(form.get("status") ?? "").trim();
  const note = String(form.get("note") ?? "").trim();

  if (!code || !status) return { error: "Pilih tahapan baru untuk laporan ini.", done: null };

  try {
    const result = await apiPost<{ code: string; status_before: string; status: string }>(
      `/citizen-reports/${encodeURIComponent(code)}/status`,
      { status, note: note || undefined },
    );
    revalidatePath("/masyarakat");
    revalidatePath("/informasi");
    revalidatePath("/panic");
    revalidatePath("/input");

    return { error: null, done: `${result.code}: ${result.status_before} → ${result.status}` };
  } catch (error) {
    if (error instanceof ApiError) {
      return { error: error.message || "Tahapan laporan tidak dapat diubah.", done: null };
    }
    throw error;
  }
}
