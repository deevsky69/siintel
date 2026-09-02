"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { publishPrediction, runPrediction } from "@/lib/prediction-center";
import { HORIZONS } from "./display";
import type { PublishState, RunState } from "./run-state";

/**
 * Server action layar AI Prediction Center.
 *
 * Berjalan di server Next.js sehingga token tidak pernah menyentuh kode peramban.
 * Pemeriksaan di sini **bukan** pengaman: `prediction:run` dan `prediction:publish`
 * ditegakkan backend (CLAUDE.md §21). Yang dikerjakan di sini hanya mengubah kegagalan
 * menjadi kalimat yang dapat ditindaklanjuti — termasuk penolakan 409 ketika tanggal
 * prediksi + horizon sudah terpakai, atau ketika prediksi sudah terbit.
 *
 * Berkas `"use server"` hanya boleh mengekspor fungsi async; keadaan awal dan tipenya
 * tinggal di `run-state.ts`.
 */
export async function submitRun(_previous: RunState, form: FormData): Promise<RunState> {
  const predictionDate = String(form.get("prediction_date") ?? "").trim();
  const horizon = String(form.get("horizon") ?? "")
    .trim()
    .toUpperCase();
  // Menulis harus dinyatakan secara sadar. Nilai apa pun selain "tulis" berarti uji coba.
  const write = String(form.get("mode") ?? "") === "tulis";

  if (predictionDate && !/^\d{4}-\d{2}-\d{2}$/.test(predictionDate)) {
    return { error: "Tanggal prediksi harus berbentuk YYYY-MM-DD.", result: null };
  }

  if (!HORIZONS.some((item) => item === horizon)) {
    return { error: `Horizon harus salah satu dari ${HORIZONS.join(", ")}.`, result: null };
  }

  try {
    const result = await runPrediction({
      prediction_date: predictionDate || undefined,
      horizon,
      dry_run: !write,
    });

    if (write) {
      // Prediksi baru ikut terbaca di peta dan Warning Center — dimuat ulang dari API,
      // bukan ditebak di klien.
      revalidatePath("/prediksi");
      revalidatePath("/peta");
      revalidatePath("/");
    }

    return { error: null, result };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, result: null };
    throw error;
  }
}

/**
 * Mempublikasikan satu prediksi.
 *
 * Tindakan terpisah dari penjalanan, dengan kewenangan sendiri: hanya prediksi
 * `PUBLISHED` yang boleh melahirkan peringatan dini, sehingga menerbitkannya adalah
 * keputusan manusia — bukan efek samping menekan tombol jalankan (CLAUDE.md §13).
 */
export async function submitPublish(
  _previous: PublishState,
  form: FormData,
): Promise<PublishState> {
  const code = String(form.get("code") ?? "").trim();

  if (!code) {
    return { error: "Kode prediksi tidak terbaca dari formulir.", published: null };
  }

  try {
    const published = await publishPrediction(code);
    revalidatePath("/prediksi");
    revalidatePath("/peringatan");
    return { error: null, published };
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message, published: null };
    throw error;
  }
}
