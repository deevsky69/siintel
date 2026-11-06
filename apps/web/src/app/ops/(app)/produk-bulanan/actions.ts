"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import {
  analystReview,
  decideProduct,
  draftProduct,
  recordAction,
  stageOutcome,
} from "@/lib/monthly-products";

export type ProductState = { error: string | null; done: string | null };
const IDLE_OK = (done: string): ProductState => ({ error: null, done });

async function guard(run: () => Promise<ProductState>): Promise<ProductState> {
  try {
    const state = await run();
    revalidatePath("/ops/produk-bulanan");
    return state;
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, done: null };
    throw error;
  }
}

export async function draftAction(_p: ProductState, form: FormData): Promise<ProductState> {
  const month = String(form.get("month") ?? "");
  return guard(async () => {
    await draftProduct(month);
    return IDLE_OK("Draf disusun.");
  });
}

export async function analystAction(_p: ProductState, form: FormData): Promise<ProductState> {
  const month = String(form.get("month") ?? "");
  const names = form.getAll("kelurahan").map(String);
  const items = names.map((kelurahan) => ({
    kelurahan,
    status: String(form.get(`status:${kelurahan}`) ?? "ACCEPTED"),
    text: String(form.get(`text:${kelurahan}`) ?? "") || undefined,
    reason: String(form.get(`reason:${kelurahan}`) ?? "") || undefined,
  }));
  return guard(async () => {
    await analystReview(month, { items, note: String(form.get("note") ?? "") || undefined });
    return IDLE_OK("Pemeriksaan analis tersimpan.");
  });
}

export async function outcomeAction(_p: ProductState, form: FormData): Promise<ProductState> {
  const month = String(form.get("month") ?? "");
  const stage = form.get("stage") === "kasat" ? "kasat" : "kbo";
  const outcome = form.get("outcome") === "REJECTED" ? "REJECTED" : "ACCEPTED";
  return guard(async () => {
    await stageOutcome(month, stage, {
      outcome,
      reason: String(form.get("reason") ?? "") || undefined,
    });
    return IDLE_OK(outcome === "ACCEPTED" ? "Diterima." : "Dikembalikan ke analis.");
  });
}

export async function decideAction(_p: ProductState, form: FormData): Promise<ProductState> {
  const month = String(form.get("month") ?? "");
  const selected = form.getAll("selected").map((name) => ({
    kelurahan: String(name),
    action: String(form.get(`action:${String(name)}`) ?? "") || undefined,
  }));
  return guard(async () => {
    await decideProduct(month, { selected, reason: String(form.get("reason") ?? "") || undefined });
    return IDLE_OK(`${selected.length} kelurahan ditetapkan.`);
  });
}

export async function recordActionForm(_p: ProductState, form: FormData): Promise<ProductState> {
  const month = String(form.get("month") ?? "");
  const kelurahan = String(form.get("kelurahan") ?? "");
  return guard(async () => {
    await recordAction(month, kelurahan, {
      unit: String(form.get("unit") ?? "") || undefined,
      acted_at: new Date(String(form.get("acted_at") ?? "")).toISOString(),
      place: String(form.get("place") ?? ""),
      action: String(form.get("action") ?? ""),
      result: String(form.get("result") ?? "") || undefined,
    });
    return IDLE_OK("Kegiatan tercatat.");
  });
}
