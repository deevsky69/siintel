"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { freezeRanking } from "@/lib/rankings";

export type FreezeState = { error: string | null; done: string | null };

export async function freezeAction(_p: FreezeState, form: FormData): Promise<FreezeState> {
  const month = String(form.get("month") ?? "");
  const method = String(form.get("method") ?? "") || undefined;
  const scope = String(form.get("scope") ?? "") || undefined;
  try {
    const row = await freezeRanking({ month, method, scope });
    revalidatePath("/ops/peringkat");
    return { error: null, done: `Peringkat ${row.target_month} dibekukan.` };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
