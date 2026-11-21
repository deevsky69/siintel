"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { recordWorkLog } from "@/lib/monthly-products";

export type WorkState = { error: string | null; done: string | null };

const RUBRIC = ["traceability", "place_time", "field_fit", "feasibility"] as const;

/** `datetime-local` tidak membawa zona; layar ini bekerja dalam WIB. */
function wib(value: FormDataEntryValue | null): string | undefined {
  const text = String(value ?? "").trim();
  return text ? `${text}:00+07:00` : undefined;
}

function scores(form: FormData, prefix: string): Record<string, number> | null {
  const out: Record<string, number> = {};
  for (const key of RUBRIC) {
    const raw = String(form.get(`${prefix}:${key}`) ?? "");
    if (raw === "") return null;
    out[key] = Number(raw);
  }
  return out;
}

/** Mencatat skor mutu draf dan cap waktu kerja (Modul 5; naskah Taskap Lampiran L huruf D). */
export async function workLogAction(_p: WorkState, form: FormData): Promise<WorkState> {
  const month = String(form.get("month") ?? "");
  const sigap = scores(form, "sigap");
  if (!sigap) return { error: "Isi keempat unsur skor draf SIGAP.", done: null };
  const manual = scores(form, "manual");
  try {
    await recordWorkLog(month, {
      quality_sigap: sigap,
      quality_manual: manual ?? undefined,
      received_at: wib(form.get("received_at")),
      data_ready_at: wib(form.get("data_ready_at")),
      map_ready_at: wib(form.get("map_ready_at")),
      note: String(form.get("note") ?? "").trim() || undefined,
    });
    revalidatePath("/ops/evaluasi-bulanan");
    return { error: null, done: "Mutu draf dan waktu kerja tercatat." };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
