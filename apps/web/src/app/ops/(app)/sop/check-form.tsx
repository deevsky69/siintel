"use client";

import { useActionState } from "react";
import { recordSopCheckAction, type SopState } from "./actions";

const IDLE: SopState = { error: null, done: null };

/** Tombol "Catat" untuk satu butir SOP; hanya tampil bagi peran yang berwenang atas butir itu. */
export function SopCheckForm({ period, item }: { period: string; item: string }) {
  const [state, submit, pending] = useActionState(recordSopCheckAction, IDLE);
  if (state.done) return <span className="text-2xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-1.5">
      <input type="hidden" name="period" value={period} />
      <input type="hidden" name="item" value={item} />
      <input
        name="note"
        aria-label="Catatan"
        placeholder="Catatan (opsional)"
        className="min-w-32 flex-1 rounded border border-base-700 bg-base-850 px-2 py-1 text-2xs text-ink"
      />
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-accent/60 bg-accent/10 px-2.5 py-1 text-2xs font-semibold text-accent disabled:opacity-50"
      >
        {pending ? "Mencatat…" : "Catat sudah dikerjakan"}
      </button>
      {state.error ? <span className="text-2xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}
