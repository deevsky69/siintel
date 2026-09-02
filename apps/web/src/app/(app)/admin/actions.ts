"use server";

import { revalidatePath } from "next/cache";
import { updateUserAssignment } from "@/lib/administration";
import { ApiError } from "@/lib/api";
import type { AssignmentState } from "./assignment-state";

/**
 * Server action pemindahan penugasan pengguna (TASK 143).
 *
 * Berjalan di server Next.js, sehingga token tidak pernah menyentuh kode peramban — pola
 * yang sama dengan `rekomendasi/actions.ts` dan `operasi/actions.ts`.
 *
 * Aturan yang sesungguhnya ditegakkan backend (CLAUDE.md §21):
 *
 * - password ditolak, tidak diabaikan;
 * - tidak ada yang boleh mengubah perannya sendiri;
 * - pemegang `commander_decision:approve` terakhir tidak boleh dipindahkan;
 * - peran ber-cakupan wajib punya atributnya.
 *
 * Tidak satu pun ditiru di sini. Yang dikerjakan action ini hanya mengubah kegagalan
 * menjadi kalimat yang dapat ditindaklanjuti (§23), dan **tidak pernah** mengirim bidang
 * password: formulirnya memang tidak punya kolom itu.
 *
 * Berkas ini hanya mengekspor fungsi async; keadaan awal formulir tinggal di
 * `assignment-state.ts`.
 */

/** Membaca satu bidang pilihan; string kosong berarti "tidak ditetapkan", bukan "kosongkan teks". */
function optional(form: FormData, field: string): string | null {
  const value = String(form.get(field) ?? "").trim();
  return value === "" ? null : value;
}

function explain(error: ApiError): string {
  if (error.status === 403) {
    return "Akun Anda tidak berwenang mengubah penugasan pengguna. Permintaan ditolak backend dan percobaannya tercatat pada audit trail.";
  }
  if (error.status === 404) {
    return "Pengguna tidak ditemukan. Muat ulang halaman untuk melihat daftar terkini.";
  }
  // 400 dan 409 dari backend sudah menyebut aturan yang dilanggar beserta alasannya —
  // termasuk larangan mengubah peran sendiri dan larangan menghabiskan pemegang
  // kewenangan persetujuan. Pesannya dipertahankan apa adanya.
  return error.message;
}

export async function reassign(
  _previous: AssignmentState,
  form: FormData,
): Promise<AssignmentState> {
  const code = String(form.get("code") ?? "").trim();
  const roleCode = String(form.get("role_code") ?? "").trim();
  const status = String(form.get("status") ?? "").trim();

  if (!code) return { error: "Pengguna tidak dikenali.", done: null };
  if (!roleCode) return { error: "Pilih peran yang akan diberikan.", done: null };
  if (!status) return { error: "Pilih status akun.", done: null };

  try {
    await updateUserAssignment(code, {
      role_code: roleCode,
      polsek: optional(form, "polsek"),
      function: optional(form, "function"),
      status,
    });
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error), done: null };
    throw error;
  }

  // Peran, cakupan, dan jumlah pemegang tiap peran ikut berubah, jadi seluruh halaman
  // dimuat ulang dari API — bukan ditebak di klien.
  revalidatePath("/admin");
  return { error: null, done: code };
}
