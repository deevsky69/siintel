"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { PLAN_DECISIONS, type PlanDecision } from "@/lib/patrol-plan";
import { submitPlanDecision } from "@/lib/patrol-plan-api";
import type { PlanDecisionState } from "./decision-state";

/**
 * Server action keputusan Pimpinan atas rencana patroli.
 *
 * Slot yang dipertahankan dikirim sebagai `kept` berulang dengan nilai
 * `JENIS|Kelurahan|blok`. Validasi di sini hanya mengubah kegagalan menjadi kalimat;
 * backend yang memutuskan sah-tidaknya (CLAUDE.md §21).
 */
export async function decidePlan(
  _previous: PlanDecisionState,
  form: FormData,
): Promise<PlanDecisionState> {
  const decision = String(form.get("decision") ?? "") as PlanDecision;
  const reason = String(form.get("reason") ?? "").trim();
  const kept = form
    .getAll("kept")
    .map((value) => String(value))
    .map((value) => {
      const [threat_type, kelurahan, block] = value.split("|");
      return { threat_type, kelurahan, block_start: Number(block) };
    })
    .filter((row) => row.threat_type && row.kelurahan && Number.isInteger(row.block_start));

  if (!PLAN_DECISIONS.includes(decision)) {
    return { error: "Keputusan tidak dikenali.", done: null };
  }
  if (decision === "REJECTED" && !reason) {
    return { error: "Penolakan wajib menyertakan alasan.", done: null };
  }
  if (decision === "MODIFIED" && kept.length === 0) {
    return {
      error: "Pilih sekurang-kurangnya satu slot yang dipertahankan, atau tolak usulan.",
      done: null,
    };
  }

  try {
    const result = await submitPlanDecision({
      decision,
      reason: reason || undefined,
      kept_slots: decision === "MODIFIED" ? kept : undefined,
    });
    revalidatePath("/rencana-patroli");
    return { error: null, done: result.code };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
