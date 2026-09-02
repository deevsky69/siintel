"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { runScoring } from "@/lib/scoring";
import type { RunState } from "./run-state";

/**
 * Server action penjalanan penilaian risiko.
 *
 * Berjalan di server Next.js sehingga token tidak pernah menyentuh kode peramban.
 * Pemeriksaan di sini **bukan** pengaman: `risk_score:run` ditegakkan backend
 * (CLAUDE.md §21). Yang dikerjakan di sini hanya mengubah kegagalan menjadi kalimat yang
 * dapat ditindaklanjuti — termasuk penolakan 409 ketika tanggal penilaian sudah terpakai.
 *
 * Berkas `"use server"` hanya boleh mengekspor fungsi async; keadaan awal dan tipenya
 * tinggal di `run-state.ts`.
 */
export async function runAssessment(_previous: RunState, form: FormData): Promise<RunState> {
  const assessmentDate = String(form.get("assessment_date") ?? "").trim();
  // Menulis harus dinyatakan secara sadar. Nilai apa pun selain "tulis" berarti uji coba.
  const write = String(form.get("mode") ?? "") === "tulis";

  if (assessmentDate && !/^\d{4}-\d{2}-\d{2}$/.test(assessmentDate)) {
    return { error: "Tanggal penilaian harus berbentuk YYYY-MM-DD.", result: null };
  }

  try {
    const result = await runScoring({
      assessment_date: assessmentDate || undefined,
      dry_run: !write,
    });

    if (write) {
      // Angka risiko berubah di peta, dashboard, dan brief — dimuat ulang dari API,
      // bukan ditebak di klien.
      revalidatePath("/skoring");
      revalidatePath("/peta");
      revalidatePath("/");
    }

    return { error: null, result };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, result: null };
    throw error;
  }
}
