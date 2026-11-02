"use server";

import { headers } from "next/headers";
import type { CaseTrack, VehicleCheck } from "@/lib/warga";

const BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export type TrackState =
  | { status: "idle" }
  | { status: "found"; data: CaseTrack }
  | { status: "error"; message: string };

export type VehicleState =
  | { status: "idle" }
  | { status: "done"; data: VehicleCheck; query: string }
  | { status: "error"; message: string };

async function clientHeaders(): Promise<Record<string, string>> {
  const incoming = await headers();
  const client = incoming.get("x-forwarded-for") ?? incoming.get("x-real-ip");
  return client
    ? { "X-Forwarded-For": client, Accept: "application/json" }
    : { Accept: "application/json" };
}

/** Lacak laporan: nomor LP + PIN. Jawaban 404 API diteruskan apa adanya — seragam. */
export async function trackCase(_previous: TrackState, form: FormData): Promise<TrackState> {
  const lp = String(form.get("lp") ?? "").trim();
  const pin = String(form.get("pin") ?? "").trim();
  if (lp.length < 5)
    return { status: "error", message: "Isi nomor LP seperti tertulis pada STPL." };
  if (!/^\d{4}$/.test(pin)) return { status: "error", message: "PIN terdiri dari empat angka." };
  try {
    const query = new URLSearchParams({ lp, pin });
    const response = await fetch(`${BASE_URL}/api/v1/public/cases/track?${query}`, {
      headers: await clientHeaders(),
      cache: "no-store",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      return { status: "error", message: payload?.error?.message ?? "Laporan tidak ditemukan." };
    }
    return { status: "found", data: payload as CaseTrack };
  } catch {
    return { status: "error", message: "Server tidak dapat dihubungi." };
  }
}

/** Cek kendaraan: plat atau nomor rangka. */
export async function checkVehicle(_previous: VehicleState, form: FormData): Promise<VehicleState> {
  const plat = String(form.get("plat") ?? "").trim();
  const rangka = String(form.get("rangka") ?? "").trim();
  if (!plat && !rangka) return { status: "error", message: "Isi plat nomor atau nomor rangka." };
  try {
    const query = new URLSearchParams();
    if (plat) query.set("plat", plat);
    if (rangka) query.set("rangka", rangka);
    const response = await fetch(`${BASE_URL}/api/v1/public/vehicles/check?${query}`, {
      headers: await clientHeaders(),
      cache: "no-store",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      return {
        status: "error",
        message: payload?.error?.message ?? "Pemeriksaan belum dapat dilakukan.",
      };
    }
    return { status: "done", data: payload as VehicleCheck, query: plat || rangka };
  } catch {
    return { status: "error", message: "Server tidak dapat dihubungi." };
  }
}
