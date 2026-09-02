import type { RunResult } from "@/lib/scoring";

/**
 * Keadaan formulir penjalanan penilaian.
 *
 * Dipisahkan dari `actions.ts` karena berkas `"use server"` hanya boleh mengekspor fungsi
 * async: mengekspor nilai dari sana membuat Next menolak seluruh modul ketika action
 * dipanggil — kegagalan yang tidak terlihat oleh `next build` maupun test
 * (`src/app/server-actions.test.ts`).
 */
export type RunState = {
  error: string | null;
  result: RunResult | null;
};

export const IDLE: RunState = { error: null, result: null };
