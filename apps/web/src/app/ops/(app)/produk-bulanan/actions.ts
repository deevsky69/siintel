"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import {
  analystReview,
  decideProduct,
  draftProduct,
  kasatReview,
  kboCheck,
  recordAction,
  wakasatCheck,
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
    return IDLE_OK("Draf disusun; peringkat bulan ini dibekukan.");
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
    return IDLE_OK("Pemeriksaan tersimpan; produk dikirim ke KBO.");
  });
}

/** Telaah Kasat Intelkam: meneruskan ke Pimpinan, atau mengembalikan ke staf dengan alasan. */
export async function kasatAction(_p: ProductState, form: FormData): Promise<ProductState> {
  const month = String(form.get("month") ?? "");
  const raw = String(form.get("outcome") ?? "");
  if (raw !== "ACCEPTED" && raw !== "REJECTED") {
    return { error: "Pilih meneruskan atau mengembalikan.", done: null };
  }
  const outcome: "ACCEPTED" | "REJECTED" = raw;
  const reason = String(form.get("reason") ?? "").trim();
  if (outcome === "REJECTED" && !reason) {
    return { error: "Alasan wajib diisi bila dikembalikan ke analis.", done: null };
  }
  // Formulir yang sama dipakai KBO dan Kasat; `stage` menentukan tahap yang dicatat.
  const stage = String(form.get("stage") ?? "KASAT");
  return guard(async () => {
    if (stage === "KBO") {
      await kboCheck(month, { outcome, reason: reason || undefined });
      return IDLE_OK(
        outcome === "ACCEPTED"
          ? "Produk diteruskan ke Wakasat Intelkam."
          : "Produk dikembalikan ke analis.",
      );
    }
    if (stage === "WAKASAT") {
      await wakasatCheck(month, { outcome, reason: reason || undefined });
      return IDLE_OK(
        outcome === "ACCEPTED"
          ? "Produk diteruskan ke Kasat Intelkam."
          : "Produk dikembalikan ke analis.",
      );
    }
    await kasatReview(month, { outcome, reason: reason || undefined });
    return IDLE_OK(
      outcome === "ACCEPTED" ? "Produk diteruskan ke Pimpinan." : "Produk dikembalikan ke analis.",
    );
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
