"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { moderateReview } from "@/lib/reviews";

export type ModerationState = { error: string | null; done: string | null };

export async function moderate(
  _previous: ModerationState,
  form: FormData,
): Promise<ModerationState> {
  const code = String(form.get("code") ?? "");
  const decision = String(form.get("decision") ?? "");
  const note = String(form.get("note") ?? "");
  if (!code || (decision !== "PUBLISH" && decision !== "REJECT")) {
    return { error: "Keputusan tidak dikenali.", done: null };
  }
  try {
    await moderateReview(code, decision, note);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 403)
        return { error: "Akun Anda tidak berwenang memoderasi.", done: null };
      return { error: error.message, done: null };
    }
    throw error;
  }
  revalidatePath("/ops/survey");
  revalidatePath("/ops", "layout");
  return { error: null, done: `${code} ${decision === "PUBLISH" ? "ditayangkan" : "ditolak"}.` };
}
