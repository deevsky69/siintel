"use client";

import { useActionState } from "react";
import { actOnPanic } from "./actions";
import { IDLE_PANIC } from "./panic-state";

/** Tombol Terima / Tutup pada satu permintaan darurat; server yang memutuskan boleh atau tidak. */
export function PanicActions({ code, status }: { code: string; status: string }) {
  const [state, submit, pending] = useActionState(actOnPanic, IDLE_PANIC);
  if (status === "CLOSED") return null;
  return (
    <form action={submit} className="mt-2 flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      {status === "OPEN" ? (
        <button
          type="submit"
          name="action"
          value="acknowledge"
          disabled={pending}
          className="rounded border border-risk-critical/60 bg-risk-critical/15 px-3 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider text-risk-critical transition hover:bg-risk-critical/25 disabled:opacity-50"
        >
          Terima
        </button>
      ) : null}
      <input
        type="text"
        name="note"
        maxLength={2000}
        placeholder="Catatan penutupan (opsional)"
        className="min-w-[12rem] flex-1 rounded border border-base-700 bg-base-950/60 px-2 py-1.5 text-xs text-ink outline-none focus:border-accent"
      />
      <button
        type="submit"
        name="action"
        value="close"
        disabled={pending}
        className="rounded border border-base-700 px-3 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider text-ink-muted transition hover:border-accent/40 hover:text-ink disabled:opacity-50"
      >
        Tutup
      </button>
      {state.error ? <span className="text-2xs text-risk-critical">{state.error}</span> : null}
      {state.done ? <span className="text-2xs text-risk-low">{state.done}</span> : null}
    </form>
  );
}
