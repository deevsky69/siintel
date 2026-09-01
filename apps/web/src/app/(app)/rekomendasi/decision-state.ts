/**
 * Keadaan formulir keputusan.
 *
 * Dipisahkan dari `actions.ts` karena berkas `"use server"` hanya boleh mengekspor
 * fungsi async: mengekspor nilai dari sana membuat Next menolak seluruh modul ketika
 * action dipanggil — kegagalan yang tidak terlihat oleh `next build` maupun test.
 */
export type DecisionState = { error: string | null; done: string | null };

export const IDLE: DecisionState = { error: null, done: null };
