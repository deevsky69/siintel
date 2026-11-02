"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { advanceCaseStage, createCaseFile } from "@/lib/case-files";

export type CaseActionState = { error: string | null; done: string | null; pin?: string | null };

export async function recordCase(
  _previous: CaseActionState,
  form: FormData,
): Promise<CaseActionState> {
  const body = {
    lp_number: String(form.get("lp_number") ?? ""),
    crime_type: String(form.get("crime_type") ?? ""),
    kecamatan: String(form.get("kecamatan") ?? ""),
    kelurahan: String(form.get("kelurahan") ?? ""),
    reported_on: String(form.get("reported_on") ?? ""),
    summary: String(form.get("summary") ?? "") || null,
    vehicle_plate: String(form.get("vehicle_plate") ?? "") || null,
    vehicle_vin: String(form.get("vehicle_vin") ?? "") || null,
    vehicle_desc: String(form.get("vehicle_desc") ?? "") || null,
    is_dummy: form.get("is_dummy") === "on",
  };
  try {
    const created = await createCaseFile(body);
    revalidatePath("/ops/perkara");
    return { error: null, done: `${created.lp_number} tercatat.`, pin: created.reporter_pin };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

export async function moveStage(
  _previous: CaseActionState,
  form: FormData,
): Promise<CaseActionState> {
  const lp = String(form.get("lp") ?? "");
  const stage = String(form.get("stage") ?? "");
  const note = String(form.get("note") ?? "");
  const recoveredRaw = form.get("vehicle_recovered");
  const recovered = recoveredRaw === null ? undefined : recoveredRaw === "on";
  try {
    const row = await advanceCaseStage(lp, stage, note, recovered);
    revalidatePath("/ops/perkara");
    return { error: null, done: `${row.lp_number} → ${row.stage_label}.` };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
