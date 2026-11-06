"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { confirmArea, resolveDuplicate } from "@/lib/standardization";

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
  try {
    await resolveDuplicate(code, { status, note: String(form.get("note") ?? "") || undefined });
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
