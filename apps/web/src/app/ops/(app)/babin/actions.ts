"use server";

import { revalidatePath } from "next/cache";
import { putBabin } from "@/lib/babin";

export type BabinState = { error: string | null; done: string | null };

export async function saveBabin(_previous: BabinState, form: FormData): Promise<BabinState> {
  const kelurahan = String(form.get("kelurahan") ?? "");
  const body = {
    name: String(form.get("name") ?? "").trim(),
    rank: String(form.get("rank") ?? "").trim() || null,
    phone_display: String(form.get("phone_display") ?? "").trim(),
    telegram_chat_id: String(form.get("telegram_chat_id") ?? "").trim() || null,
    whatsapp_group_link: String(form.get("whatsapp_group_link") ?? "").trim() || null,
    whatsapp_number: String(form.get("whatsapp_number") ?? "").trim() || null,
    is_dummy: form.get("is_dummy") === "on",
  };
  if (!kelurahan || body.name.length < 2 || body.phone_display.length < 6) {
    return { error: "Nama dan nomor dinas wajib diisi.", done: null };
  }
  try {
    await putBabin(kelurahan, body);
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Gagal menyimpan.", done: null };
  }
  revalidatePath("/ops/babin");
  return { error: null, done: `Kontak ${kelurahan} tersimpan.` };
}
