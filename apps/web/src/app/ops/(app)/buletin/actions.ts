"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import {
  approveAdvisory,
  approveAreaSummary,
  approveBulletin,
  generateBulletins,
} from "@/lib/babin";

export type BulletinState = { error: string | null; done: string | null };

export async function generate(_previous: BulletinState, form: FormData): Promise<BulletinState> {
  const week = String(form.get("week") ?? "").trim() || null;
  try {
    const result = await generateBulletins(week);
    revalidatePath("/ops/buletin");
    return {
      error: null,
      done: `Minggu ${result.week_start}: ${result.created} draf baru, ${result.refreshed} disegarkan.`,
    };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

export async function approve(_previous: BulletinState, form: FormData): Promise<BulletinState> {
  const id = String(form.get("id") ?? "");
  try {
    const row = await approveBulletin(id);
    revalidatePath("/ops/buletin");
    return { error: null, done: `${row.kelurahan} disetujui; bot akan mengirimnya.` };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

/** Persetujuan Humas atas ringkasan wilayah; setelah itu angkanya tayang di SIGAP BERSAMA. */
export async function approveAreaSummaryAction(
  _previous: BulletinState,
  form: FormData,
): Promise<BulletinState> {
  try {
    await approveAreaSummary(String(form.get("note") ?? "") || undefined);
    revalidatePath("/ops/buletin");
    revalidatePath("/");
    revalidatePath("/peta");
    return { error: null, done: "Ringkasan wilayah disetujui dan tayang untuk masyarakat." };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

/** Persetujuan Humas atas imbauan bulanan; setelah itu bot mengirimnya. */
export async function approveAdvisoryAction(
  _previous: BulletinState,
  form: FormData,
): Promise<BulletinState> {
  const month = String(form.get("month") ?? "");
  try {
    await approveAdvisory(month, String(form.get("note") ?? "") || undefined);
    revalidatePath("/ops/buletin");
    return { error: null, done: `Imbauan ${month} disetujui; bot akan mengirimnya.` };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}
