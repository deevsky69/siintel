"use client";

import { useActionState } from "react";
import { approve, type BulletinState, generate } from "./actions";

const IDLE: BulletinState = { error: null, done: null };

export function GenerateForm({ suggested }: { suggested: string }) {
  const [state, submit, pending] = useActionState(generate, IDLE);
  return (
    <form action={submit} className="flex flex-wrap items-end gap-2 text-xs">
      <label className="text-ink-muted">
        Senin minggu yang dilaporkan
        <input
          name="week"
          type="date"
          defaultValue={suggested}
          className="mt-1 block rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink"
        />
      </label>
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-accent/60 bg-accent/10 px-3 py-1.5 font-semibold text-accent disabled:opacity-50"
      >
        {pending ? "Menyusun…" : "Susun draf seluruh kelurahan"}
      </button>
      {state.error ? <span className="text-risk-critical">{state.error}</span> : null}
      {state.done ? <span className="text-risk-low">{state.done}</span> : null}
    </form>
  );
}

export function ApproveButton({ id }: { id: string }) {
  const [state, submit, pending] = useActionState(approve, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="inline-flex items-center gap-2">
      <input type="hidden" name="id" value={id} />
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-risk-low/60 bg-risk-low/10 px-3 py-1 text-xs font-semibold text-risk-low disabled:opacity-50"
      >
        Setujui & kirim
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}
