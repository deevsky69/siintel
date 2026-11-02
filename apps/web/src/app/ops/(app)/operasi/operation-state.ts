/**
 * Keadaan kedua formulir layar operasi.
 *
 * Dipisahkan dari `actions.ts` karena berkas `"use server"` hanya boleh mengekspor fungsi
 * async: mengekspor nilai dari sana membuat Next menolak seluruh modul ketika action
 * dipanggil — kegagalan yang tidak terlihat oleh `next build` maupun test, dan baru
 * muncul sebagai 500 saat tombol pertama kali ditekan. Lihat `app/server-actions.test.ts`.
 */

/** Hasil percobaan mencatat penugasan; `done` berisi kode tindakan yang terbentuk. */
export type AssignmentState = { error: string | null; done: string | null };

export const ASSIGNMENT_IDLE: AssignmentState = { error: null, done: null };

/** Hasil percobaan mencatat hasil nyata; `done` berisi kode tindakan yang ditutup. */
export type ResultState = { error: string | null; done: string | null };

export const RESULT_IDLE: ResultState = { error: null, done: null };
