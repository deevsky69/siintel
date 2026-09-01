"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { DECISIONS, type Decision, submitDecision } from "@/lib/decisions";
import type { DecisionState } from "./decision-state";

/**
 * Server action keputusan komandan.
 *
 * Berjalan di server Next.js, sehingga token tidak pernah menyentuh kode peramban.
 * Validasi di sini **bukan** pengaman: backend yang memutuskan boleh-tidaknya
 * (CLAUDE.md §21). Yang dikerjakan di sini hanya mengubah kegagalan menjadi kalimat
 * yang dapat ditindaklanjuti pejabat, bukan kode kesalahan.
 *
 * Berkas `"use server"` **hanya boleh mengekspor fungsi async**. Mengekspor nilai
 * atau tipe dari sini membuat Next menolak seluruh modul — dan penolakannya baru
 * terjadi ketika action dipanggil, bukan saat halaman dirender, sehingga lolos dari
 * `next build` maupun test. Karena itu keadaan awal dan tipenya tinggal di
 * `decision-state.ts`.
 */

export async function decide(_previous: DecisionState, form: FormData): Promise<DecisionState> {
  const code = String(form.get("code") ?? "");
  const decision = String(form.get("decision") ?? "") as Decision;
  const reason = String(form.get("reason") ?? "").trim();
  const modified = String(form.get("modified_text") ?? "").trim();

  if (!code || !DECISIONS.includes(decision)) {
    return { error: "Keputusan tidak dikenali.", done: null };
  }
  if (decision === "MODIFIED" && !modified) {
    return {
      error: "Modifikasi wajib menyertakan isi rekomendasi yang telah disesuaikan.",
      done: null,
    };
  }

  try {
    await submitDecision(code, {
      decision,
      reason: reason || undefined,
      modified_text: decision === "MODIFIED" ? modified : undefined,
    });
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }

  // Status rekomendasi ikut berubah, jadi seluruh halaman dimuat ulang dari API —
  // bukan ditebak di klien.
  revalidatePath("/rekomendasi");
  revalidatePath("/");
  return { error: null, done: code };
}
