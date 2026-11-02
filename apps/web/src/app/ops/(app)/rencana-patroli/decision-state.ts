/**
 * Keadaan formulir keputusan rencana patroli.
 *
 * Dipisahkan dari `actions.ts` karena berkas `"use server"` hanya boleh mengekspor fungsi
 * async (lihat catatan pada `rekomendasi/decision-state.ts`).
 */
export type PlanDecisionState = { error: string | null; done: string | null };

export const IDLE: PlanDecisionState = { error: null, done: null };
