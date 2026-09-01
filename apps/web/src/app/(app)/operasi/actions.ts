"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import {
  createOperation,
  RESULT_STATUSES,
  type ResultStatus,
  recordOperationResult,
  wibIso,
} from "@/lib/operations";
import type { AssignmentState, ResultState } from "./operation-state";

/**
 * Server action lengan umpan balik: mencatat penugasan, lalu mencatat hasil nyatanya.
 *
 * Berjalan di server Next.js, sehingga token tidak pernah menyentuh kode peramban — pola
 * yang sama dengan `rekomendasi/actions.ts` dan `peringatan/actions.ts`.
 *
 * Pemeriksaan di sini **bukan** pengaman. Kewenangan `operation:write`, kesahan keputusan
 * asal, dan larangan mengubah hasil yang sudah final ditegakkan backend beserta trigger
 * database (CLAUDE.md §21). Yang dikerjakan di sini hanya mengubah kegagalan menjadi
 * kalimat yang dapat ditindaklanjuti petugas, bukan kode kesalahan mentah (§23).
 *
 * Berkas ini hanya mengekspor fungsi async; keadaan awal formulir tinggal di
 * `operation-state.ts`.
 */

/** Menerjemahkan kegagalan backend menjadi langkah yang dapat diambil pengguna. */
function explain(error: ApiError, subject: string): string {
  if (error.status === 403) {
    return `Akun Anda tidak berwenang mencatat ${subject}. Permintaan ditolak backend dan percobaannya tercatat; mintakan pencatatan ini kepada petugas Command Center.`;
  }
  if (error.status === 404) {
    return "Data tidak ditemukan atau berada di luar cakupan wilayah akun Anda.";
  }
  if (error.status === 409) {
    return `${error.message} Muat ulang halaman untuk melihat keadaan terkini.`;
  }
  // 400 dan 422 dari backend sudah menyebut sebabnya secara spesifik — antara lain
  // syarat waktu selesai harus setelah waktu mulai. Pesannya dipertahankan apa adanya.
  return error.message;
}

export async function assign(_previous: AssignmentState, form: FormData): Promise<AssignmentState> {
  const decisionCode = String(form.get("decision_code") ?? "").trim();
  const unitCode = String(form.get("unit_code") ?? "").trim();
  const startLocal = String(form.get("start_at") ?? "").trim();
  const notes = String(form.get("notes") ?? "").trim();

  if (!decisionCode) return { error: "Keputusan asal tidak dikenali.", done: null };
  if (!unitCode) return { error: "Pilih satuan yang ditugaskan.", done: null };

  let startAt: string | undefined;
  if (startLocal) {
    const parsed = wibIso(startLocal);
    if (!parsed)
      return { error: "Waktu mulai tidak dapat dibaca. Isi ulang tanggal dan jamnya.", done: null };
    startAt = parsed;
  }

  let created: { code: string };
  try {
    created = await createOperation({
      decision_code: decisionCode,
      unit_code: unitCode,
      start_at: startAt,
      notes: notes || undefined,
    });
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error, "penugasan"), done: null };
    throw error;
  }

  // Keputusan berpindah dari antrean kerja ke daftar tindakan, jadi seluruh halaman
  // dimuat ulang dari API — bukan ditebak di klien. Dashboard ikut disegarkan karena
  // memuat hitungan tindakan berjalan.
  revalidatePath("/operasi");
  revalidatePath("/");
  return { error: null, done: created.code };
}

export async function record(_previous: ResultState, form: FormData): Promise<ResultState> {
  const code = String(form.get("code") ?? "").trim();
  const status = String(form.get("status") ?? "").trim() as ResultStatus;
  const result = String(form.get("result") ?? "").trim();
  const endLocal = String(form.get("end_at") ?? "").trim();

  if (!code) return { error: "Tindakan tidak dikenali.", done: null };
  if (!RESULT_STATUSES.includes(status)) {
    return { error: "Pilih status akhir: Selesai atau Dibatalkan.", done: null };
  }
  if (!result) return { error: "Uraian hasil nyata wajib diisi.", done: null };

  // Waktu acuan aplikasi beku pada dataset demo, sehingga tanpa waktu selesai yang
  // eksplisit backend menolak permintaan. Yang benar adalah menanyakannya, bukan
  // mengarang durasi penugasan agar constraint database lolos.
  if (!endLocal) {
    return { error: "Waktu selesai wajib diisi dan harus setelah waktu mulai.", done: null };
  }
  const endAt = wibIso(endLocal);
  if (!endAt) {
    return { error: "Waktu selesai tidak dapat dibaca. Isi ulang tanggal dan jamnya.", done: null };
  }

  try {
    await recordOperationResult(code, { status, result, end_at: endAt });
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error, "hasil"), done: null };
    throw error;
  }

  revalidatePath("/operasi");
  revalidatePath("/");
  return { error: null, done: code };
}
