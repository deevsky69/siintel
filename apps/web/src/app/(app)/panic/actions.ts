"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { PANIC_ACTIONS, type PanicAction, submitPanicAction } from "@/lib/panic";
import type { PanicActionState } from "./panic-state";

export async function actOnPanic(
  _previous: PanicActionState,
  form: FormData,
): Promise<PanicActionState> {
  const code = String(form.get("code") ?? "");
  const action = String(form.get("action") ?? "") as PanicAction;
  const note = String(form.get("note") ?? "");
  if (!code || !PANIC_ACTIONS.includes(action)) {
    return { error: "Tindakan tidak dikenali.", done: null };
  }
  try {
    await submitPanicAction(code, action, note);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 403) {
        return { error: "Akun Anda tidak berwenang menerima permintaan darurat.", done: null };
      }
      if (error.status === 404) {
        return { error: `${code} tidak ditemukan atau di luar wilayah akun Anda.`, done: null };
      }
      return { error: error.message, done: null };
    }
    throw error;
  }
  revalidatePath("/panic");
  revalidatePath("/", "layout");
  return { error: null, done: `${code} ${action === "acknowledge" ? "diterima" : "ditutup"}.` };
}
