"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { recordSopCheck } from "@/lib/sop";

export type SopState = { error: string | null; done: string | null };

/** Mencatat satu butir berkala SOP sudah dikerjakan untuk periode itu. */
export async function recordSopCheckAction(_p: SopState, form: FormData): Promise<SopState> {
  const period = String(form.get("period") ?? "");
  const item = String(form.get("item") ?? "");
  try {
    await recordSopCheck(period, item, String(form.get("note") ?? "").trim() || undefined);
    revalidatePath("/ops/sop");
    return { error: null, done: "Tercatat." };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
