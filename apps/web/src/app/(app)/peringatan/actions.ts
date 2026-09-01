"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { submitWarningAction, WARNING_ACTIONS, type WarningAction } from "@/lib/warnings";

/**
 * Server action tindak lanjut peringatan dini (TASK 111).
 *
 * Berjalan di server Next.js, sehingga token tidak pernah menyentuh kode peramban —
 * pola yang sama dengan `rekomendasi/actions.ts`.
 *
 * Pemeriksaan di sini **bukan** pengaman. Kewenangan dan kesahan transisi ditegakkan
 * backend (`routers/warning_actions.py`); yang dikerjakan di sini hanya mengubah
 * kegagalan menjadi kalimat yang dapat ditindaklanjuti petugas, bukan kode kesalahan
 * mentah (CLAUDE.md §21, §23).
 */

/**
 * Keadaan formulir. Nilai awalnya (`IDLE`) ditulis di komponen klien, bukan di sini:
 * berkas `"use server"` hanya boleh mengekspor fungsi async — mengekspor objek membuat
 * Next menolak seluruh modul saat action dipanggil.
 */
export type FollowUpState = {
  error: string | null;
  done: { code: string; action: WarningAction } | null;
};

/** Kata kerja untuk menyusun kalimat kegagalan, bukan label tombol. */
const VERBS: Record<WarningAction, string> = {
  acknowledge: "menerima",
  resolve: "menyatakan selesai",
};

/**
 * Kegagalan backend diterjemahkan menjadi langkah yang dapat diambil pengguna.
 *
 * Pesan 403 dan 404 dari backend sengaja seragam dan tanpa detail supaya tidak
 * membocorkan keberadaan data wilayah lain; karena itu kalimat yang dibaca petugas
 * disusun di sini. Pesan 409 dari backend sudah menyebut status asal dan tujuan, jadi
 * pesan itu dipertahankan apa adanya dan hanya diberi langkah lanjutan.
 */
function explain(error: ApiError, code: string, action: WarningAction): string {
  if (error.status === 403) {
    return `Akun Anda tidak berwenang ${VERBS[action]} peringatan. Permintaan ditolak backend dan percobaannya tercatat; mintakan tindak lanjut ini kepada petugas yang berwenang.`;
  }
  if (error.status === 404) {
    return `Peringatan ${code} tidak ditemukan atau berada di luar cakupan wilayah akun Anda.`;
  }
  if (error.status === 409) {
    return `${error.message} Status peringatan kemungkinan sudah diubah petugas lain — muat ulang halaman untuk melihat status terkini.`;
  }
  return error.message;
}

export async function followUp(_previous: FollowUpState, form: FormData): Promise<FollowUpState> {
  const code = String(form.get("code") ?? "");
  const action = String(form.get("action") ?? "") as WarningAction;

  if (!code || !WARNING_ACTIONS.includes(action)) {
    return { error: "Tindak lanjut tidak dikenali.", done: null };
  }

  try {
    await submitWarningAction(code, action);
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error, code, action), done: null };
    throw error;
  }

  // Status peringatan ikut berubah, jadi seluruh halaman dimuat ulang dari API — bukan
  // ditebak di klien. Dashboard ikut disegarkan karena memuat ringkasan peringatan aktif.
  revalidatePath("/peringatan");
  revalidatePath("/");
  return { error: null, done: { code, action } };
}
