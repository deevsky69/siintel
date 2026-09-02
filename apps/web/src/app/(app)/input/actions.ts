"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import {
  type CrimeInput,
  createCrime,
  createIntelligenceReport,
  type IntelligenceInput,
  updateReportStatus,
} from "@/lib/data-entry";
import type { EntryState } from "./entry-state";

/**
 * Server action pintu masuk data.
 *
 * Berjalan di server Next.js, sehingga token tidak pernah menyentuh kode peramban — pola
 * yang sama dengan `rekomendasi/actions.ts` dan `operasi/actions.ts`.
 *
 * Pemeriksaan di sini **bukan** pengaman. Kewenangan (`crime:write`,
 * `intelligence:write`, `citizen_report:write`), cakupan wilayah, kesahan nilai
 * taksonomi, dan larangan mencatat kejadian di masa depan seluruhnya ditegakkan backend
 * (CLAUDE.md §21). Yang dikerjakan di sini hanya dua: menolak isian yang jelas-jelas
 * belum lengkap tanpa perlu perjalanan ke server, dan mengubah kegagalan menjadi kalimat
 * yang dapat ditindaklanjuti petugas — bukan kode kesalahan mentah (§23).
 *
 * Berkas ini hanya mengekspor fungsi async; keadaan awal formulir tinggal di
 * `entry-state.ts`.
 */

/** Menerjemahkan kegagalan backend menjadi langkah yang dapat diambil pengguna. */
function explain(error: ApiError, subject: string): string {
  if (error.status === 403) {
    return `Akun Anda tidak berwenang mencatat ${subject}. Permintaan ditolak backend dan percobaannya tercatat di audit; mintakan pencatatan ini kepada petugas yang berwenang.`;
  }
  if (error.status === 404) {
    // Backend sengaja tidak membedakan "tidak ada" dari "di luar wilayah Anda": jawaban
    // yang berbeda akan membocorkan keberadaan lokasi di wilayah lain.
    return "Lokasi atau laporan tersebut tidak ditemukan dalam cakupan wilayah akun Anda. Pilih wilayah yang menjadi tanggung jawab satuan Anda.";
  }
  if (error.status === 409) {
    return `${error.message} Muat ulang halaman untuk melihat keadaan terkini.`;
  }
  // 400 dari backend sudah menyebut sebabnya secara spesifik — termasuk daftar nilai
  // yang sah dan batas waktu acuan sistem. Pesannya dipertahankan apa adanya.
  return error.message;
}

function text(form: FormData, field: string): string {
  return String(form.get(field) ?? "").trim();
}

/** Isian angka yang boleh dikosongkan; teks bukan angka dianggap tidak diisi. */
function optionalNumber(form: FormData, field: string): number | undefined {
  const raw = text(form, field);
  if (!raw) return undefined;
  const value = Number(raw);
  return Number.isFinite(value) ? value : undefined;
}

export async function recordCrime(_previous: EntryState, form: FormData): Promise<EntryState> {
  const payload: CrimeInput = {
    incident_type: text(form, "incident_type"),
    incident_date: text(form, "incident_date"),
    incident_time: text(form, "incident_time"),
    location_code: text(form, "location_code"),
    location_type: text(form, "location_type") || undefined,
    modus: text(form, "modus") || undefined,
    target_type: text(form, "target_type") || undefined,
    status: text(form, "status") || undefined,
  };

  if (!payload.incident_type) return { error: "Pilih jenis kejadian.", done: null };
  if (!payload.location_code)
    return { error: "Pilih wilayah/sel grid tempat kejadian.", done: null };
  if (!payload.incident_date || !payload.incident_time) {
    return { error: "Tanggal dan jam kejadian wajib diisi.", done: null };
  }

  let created: Awaited<ReturnType<typeof createCrime>>;
  try {
    created = await createCrime(payload);
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error, "kejadian"), done: null };
    throw error;
  }

  // Kejadian baru mengubah hitungan pada dashboard, analitik, dan peta. Semuanya dimuat
  // ulang dari API — bukan ditebak di klien.
  revalidatePath("/input");
  revalidatePath("/");
  revalidatePath("/analitik");
  revalidatePath("/peta");

  const area = created.kelurahan ? `${created.kelurahan}, ${created.kecamatan}` : created.kecamatan;
  return {
    error: null,
    done: { code: created.code, detail: `${created.incident_type} · ${area} · ${created.grid_id}` },
  };
}

export async function recordIntelligence(
  _previous: EntryState,
  form: FormData,
): Promise<EntryState> {
  const payload: IntelligenceInput = {
    report_date: text(form, "report_date"),
    category: text(form, "category"),
    location_code: text(form, "location_code"),
    reliability: text(form, "reliability") || undefined,
    confidence: optionalNumber(form, "confidence"),
    urgency: optionalNumber(form, "urgency"),
    impact: text(form, "impact") || undefined,
    status: text(form, "status") || undefined,
  };

  if (!payload.category) return { error: "Isi kategori kerawanan.", done: null };
  if (!payload.location_code) return { error: "Pilih wilayah/sel grid laporan.", done: null };
  if (!payload.report_date) return { error: "Tanggal laporan wajib diisi.", done: null };

  let created: Awaited<ReturnType<typeof createIntelligenceReport>>;
  try {
    created = await createIntelligenceReport(payload);
  } catch (error) {
    if (error instanceof ApiError)
      return { error: explain(error, "laporan intelijen"), done: null };
    throw error;
  }

  revalidatePath("/input");
  revalidatePath("/intelijen");

  return {
    error: null,
    done: {
      code: created.code,
      detail: `${created.category} · ${created.kecamatan} · ${created.grid_id}`,
    },
  };
}

export async function triageReport(_previous: EntryState, form: FormData): Promise<EntryState> {
  const code = text(form, "code");
  const status = text(form, "status");
  const note = text(form, "note");

  if (!code) return { error: "Pilih laporan masyarakat yang akan ditriase.", done: null };
  if (!status) return { error: "Pilih status baru laporan.", done: null };

  let result: Awaited<ReturnType<typeof updateReportStatus>>;
  try {
    result = await updateReportStatus(code, { status, note: note || undefined });
  } catch (error) {
    if (error instanceof ApiError) {
      return { error: explain(error, "perubahan status laporan"), done: null };
    }
    throw error;
  }

  revalidatePath("/input");
  revalidatePath("/masyarakat");

  return {
    error: null,
    done: {
      code: result.code,
      detail: `${result.status_before} → ${result.status}`,
    },
  };
}
