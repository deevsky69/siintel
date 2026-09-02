import type { PublishResult, RunResult } from "@/lib/prediction-center";

/**
 * Keadaan kedua formulir pada layar AI Prediction Center.
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

export const IDLE_RUN: RunState = { error: null, result: null };

export type PublishState = {
  error: string | null;
  published: PublishResult | null;
};

export const IDLE_PUBLISH: PublishState = { error: null, published: null };
