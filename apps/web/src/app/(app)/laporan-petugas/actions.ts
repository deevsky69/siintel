"use server";

import { revalidatePath } from "next/cache";
import { ApiError, apiPost } from "@/lib/api";

/**
 * Perpindahan status penanganan kejadian.
 *
 * Berjalan di server Next.js, sehingga token tidak pernah menyentuh kode peramban — pola
 * yang sama dengan server action lain di aplikasi ini.
 *
 * Kewenangan (`crime:write`) dan cakupan wilayah ditegakkan backend. Tidak ada pemeriksaan
 * izin di berkas ini, dan itu disengaja: pemeriksaan di sini akan terlihat seperti
 * pengaman padahal hanya kenyamanan, dan yang terlihat seperti pengaman cenderung
 * dipercaya (CLAUDE.md §15, §21).
 */

export type StatusState = { error: string | null; done: string | null };

export async function changeCrimeStatus(
  _previous: StatusState,
  form: FormData,
): Promise<StatusState> {
  const code = String(form.get("code") ?? "").trim();
  const status = String(form.get("status") ?? "").trim();
  const note = String(form.get("note") ?? "").trim();

  if (!code || !status) return { error: "Pilih status baru untuk kejadian ini.", done: null };

  try {
    const result = await apiPost<{ code: string; status_before: string; status: string }>(
      `/crimes/${encodeURIComponent(code)}/status`,
      { status, note: note || undefined },
    );
    // Daftar kejadian muncul di beberapa layar; ketiganya disegarkan supaya tidak ada yang
    // menampilkan status lama beberapa saat setelah diubah.
    revalidatePath("/laporan-petugas");
    revalidatePath("/informasi");
    revalidatePath("/wilayah", "layout");

    return { error: null, done: `${result.code}: ${result.status_before} → ${result.status}` };
  } catch (error) {
    if (error instanceof ApiError) {
      // Pesan backend diteruskan apa adanya bila ada: ia yang tahu apa yang ditolak, dan
      // menggantinya dengan kalimat umum menghilangkan satu-satunya petunjuk yang dipunyai
      // petugas untuk memperbaikinya.
      return { error: error.message || "Status kejadian tidak dapat diubah.", done: null };
    }
    throw error;
  }
}
