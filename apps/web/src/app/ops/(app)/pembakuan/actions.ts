"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { confirmArea, decideMatch, recordImpact, resolveDuplicate } from "@/lib/standardization";

export type StandardState = { error: string | null; done: string | null };

export async function confirmAreaAction(_p: StandardState, form: FormData): Promise<StandardState> {
  const code = String(form.get("code") ?? "");
  const location = String(form.get("location_code") ?? "");
  if (!code || !location) return { error: "Pilih kelurahan.", done: null };
  try {
    const row = await confirmArea(code, {
      location_code: location,
      note: String(form.get("note") ?? "") || undefined,
    });
    revalidatePath("/ops/pembakuan");
    return { error: null, done: `${row.code} → ${row.kelurahan}` };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

export async function resolveDuplicateAction(
  _p: StandardState,
  form: FormData,
): Promise<StandardState> {
  const code = String(form.get("code") ?? "");
  const status = form.get("status") === "CONFIRMED" ? "CONFIRMED" : "CLEARED";
  const note = String(form.get("note") ?? "").trim();
  if (!note) return { error: "Alasan wajib diisi.", done: null };
  try {
    await resolveDuplicate(code, { status, note });
    revalidatePath("/ops/pembakuan");
    return {
      error: null,
      done: status === "CONFIRMED" ? `${code} dinyatakan ganda` : `${code} bukan ganda`,
    };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

/** Kecocokan laporan warga dengan kejadian resmi: keputusan petugas, alasan wajib. */
export async function matchAction(_p: StandardState, form: FormData): Promise<StandardState> {
  const code = String(form.get("code") ?? "");
  const incident = String(form.get("incident_code") ?? "");
  const reason = String(form.get("reason") ?? "").trim();
  if (!reason) return { error: "Alasan wajib diisi.", done: null };
  try {
    await decideMatch(
      code,
      incident
        ? { decision: "MATCHED", incident_code: incident, reason }
        : { decision: "NOT_MATCHED", reason },
    );
    revalidatePath("/ops/pembakuan");
    return {
      error: null,
      done: incident ? `${code} ditautkan ke ${incident}` : `${code} kejadian tambahan`,
    };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

/** Isian dampak satu laporan; rujukan sumber wajib. */
export async function impactAction(_p: StandardState, form: FormData): Promise<StandardState> {
  const code = String(form.get("code") ?? "");
  const source = String(form.get("source") ?? "").trim();
  if (!source) return { error: "Rujukan sumber wajib diisi.", done: null };
  try {
    await recordImpact(code, {
      loss_status: String(form.get("loss_status") ?? "UNKNOWN"),
      injury_level: String(form.get("injury_level") ?? "UNKNOWN"),
      status: String(form.get("status") ?? "PENDING"),
      source,
    });
    revalidatePath("/ops/pembakuan");
    return { error: null, done: `${code} dampak dicatat` };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
