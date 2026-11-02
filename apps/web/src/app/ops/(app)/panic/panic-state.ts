/** Keadaan formulir tindakan darurat — dipisah dari `actions.ts` yang hanya boleh mengekspor fungsi async. */
export type PanicActionState = { error: string | null; done: string | null };

export const IDLE_PANIC: PanicActionState = { error: null, done: null };
