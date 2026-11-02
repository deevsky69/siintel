"use server";

import { headers } from "next/headers";

const BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export type ReviewSubmitState =
  | { status: "idle" }
  | { status: "sent"; code: string; message: string }
  | { status: "error"; message: string };

/**
 * Mengirim ulasan Survey Rasa Aman ke API publik. Alamat pengunjung diteruskan lewat
 * `X-Forwarded-For` supaya pembatas laju API menghitung per pengunjung, bukan per server
 * Next.js — pola yang sama dengan laporan masyarakat.
 */
export async function submitReview(
  _previous: ReviewSubmitState,
  form: FormData,
): Promise<ReviewSubmitState> {
  const body = {
    kecamatan: String(form.get("kecamatan") ?? ""),
    kelurahan: String(form.get("kelurahan") ?? ""),
    rating: Number(form.get("rating") ?? 0),
    comment: String(form.get("comment") ?? "").trim() || null,
  };
  if (!body.kelurahan || !body.kecamatan)
    return { status: "error", message: "Pilih kelurahan dulu." };
  if (!(body.rating >= 1 && body.rating <= 5)) {
    return { status: "error", message: "Beri nilai 1 sampai 5 bintang." };
  }
  const incoming = await headers();
  const outgoing: Record<string, string> = { "Content-Type": "application/json" };
  const client = incoming.get("x-forwarded-for") ?? incoming.get("x-real-ip");
  if (client) outgoing["X-Forwarded-For"] = client;
  try {
    const response = await fetch(`${BASE_URL}/api/v1/public/reviews`, {
      method: "POST",
      headers: outgoing,
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      return {
        status: "error",
        message: payload?.error?.message ?? "Ulasan belum dapat dikirim. Coba lagi sebentar.",
      };
    }
    return { status: "sent", code: payload.code, message: payload.message };
  } catch {
    return { status: "error", message: "Server tidak dapat dihubungi." };
  }
}
