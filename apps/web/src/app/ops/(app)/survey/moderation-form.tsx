"use client";

import { useActionState } from "react";
import { type ModerationState, moderate } from "./actions";

const IDLE: ModerationState = { error: null, done: null };

export function ModerationForm({ code }: { code: string }) {
  const [state, submit, pending] = useActionState(moderate, IDLE);
  if (state.done) return <p className="text-xs text-risk-low">{state.done}</p>;
  return (
    <form action={submit} className="mt-2 flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <input
        name="note"
        maxLength={300}
        placeholder="Catatan (opsional)"
        className="min-w-[200px] flex-1 rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink"
      />
      <button
        type="submit"
        name="decision"
        value="PUBLISH"
        disabled={pending}
        className="rounded border border-risk-low/60 bg-risk-low/10 px-3 py-1 text-xs font-semibold text-risk-low disabled:opacity-50"
      >
        Tayangkan
      </button>
      <button
        type="submit"
        name="decision"
        value="REJECT"
        disabled={pending}
        className="rounded border border-risk-critical/60 bg-risk-critical/10 px-3 py-1 text-xs font-semibold text-risk-critical disabled:opacity-50"
      >
        Tolak
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}
