"use server";

import { revalidatePath } from "next/cache";
import { ApiError } from "@/lib/api";
import { publishAlert, withdrawAlert } from "@/lib/public-alerts";

/**
 * Server action kanal imbauan (TASK 111).
 *
 * Berjalan di server Next.js sehingga token tidak pernah menyentuh peramban — pola yang
 * sama dengan `peringatan/actions.ts`.
 *
 * Pemeriksaan di sini **bukan** pengaman. Kewenangan `public_alert:publish` ditegakkan
 * backend; yang dikerjakan di sini hanya mengubah kegagalan menjadi kalimat yang dapat
 * ditindaklanjuti (CLAUDE.md §21, §23).
 */

export type PublishState = {
  error: string | null;
  done: { code: string; action: "publish" | "withdraw" } | null;
};

/** Panjang minimum yang sama dengan backend, supaya penolakannya terbaca sebelum dikirim. */
const MIN_MESSAGE = 40;

function explain(error: ApiError, action: "publish" | "withdraw"): string {
  const verb = action === "publish" ? "menerbitkan" : "mencabut";
  if (error.status === 403) {
    return `Akun Anda tidak berwenang ${verb} imbauan kepada masyarakat. Kewenangan itu ada pada Pimpinan; permintaan ditolak backend dan percobaannya tercatat.`;
  }
  if (error.status === 404) {
    return "Data tidak ditemukan atau berada di luar cakupan wilayah akun Anda.";
  }
  if (error.status === 409) {
    return `${error.message} Muat ulang halaman untuk melihat keadaan terkini.`;
  }
  return error.message;
}

/**
 * Menyegarkan setiap halaman yang menampilkan imbauan.
 *
 * Halaman muka publik ikut disebut, dan itu yang paling mudah terlewat: ia di-prerender
 * dengan ISR 60 detik, sehingga tanpa baris ini sebuah imbauan baru terbit — atau sebuah
 * imbauan yang dicabut tetap beredar — sampai satu menit berikutnya. Pada kanal yang
 * gunanya justru mengabarkan hal mendesak, satu menit adalah selisih yang nyata, dan
 * imbauan tercabut yang masih terbaca lebih buruk lagi.
 *
 * `/` disebut terpisah dari `/beranda` karena halaman muka dilayani lewat rewrite di
 * middleware: alamat yang di-cache adalah `/`, sedangkan berkasnya `beranda/page.tsx`.
 */
function segarkan(): void {
  revalidatePath("/imbauan");
  revalidatePath("/beranda");
  revalidatePath("/");
}

export async function publish(_previous: PublishState, form: FormData): Promise<PublishState> {
  const warningCode = String(form.get("warning_code") ?? "").trim();
  const message = String(form.get("public_message") ?? "").trim();

  if (!warningCode) return { error: "Peringatan yang menjadi dasar belum dipilih.", done: null };
  if (message.length < MIN_MESSAGE) {
    return {
      error: `Isi imbauan terlalu pendek (${message.length} huruf, minimum ${MIN_MESSAGE}). Kalimat ini dibaca masyarakat dan tidak dapat ditarik kembali setelah terbaca.`,
      done: null,
    };
  }

  try {
    await publishAlert(warningCode, message);
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error, "publish"), done: null };
    throw error;
  }

  segarkan();
  return { error: null, done: { code: warningCode, action: "publish" } };
}

export async function withdraw(_previous: PublishState, form: FormData): Promise<PublishState> {
  const code = String(form.get("code") ?? "").trim();
  if (!code) return { error: "Imbauan tidak dikenali.", done: null };

  try {
    await withdrawAlert(code);
  } catch (error) {
    if (error instanceof ApiError) return { error: explain(error, "withdraw"), done: null };
    throw error;
  }

  segarkan();
  return { error: null, done: { code, action: "withdraw" } };
}
