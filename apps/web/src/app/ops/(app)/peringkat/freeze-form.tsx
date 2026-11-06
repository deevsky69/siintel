"use client";

import { useActionState } from "react";
import { type FreezeState, freezeAction } from "./actions";

const IDLE: FreezeState = { error: null, done: null };

export function FreezeForm({
  month,
  method,
  scope,
}: {
  month: string;
  method: string;
  scope: string;
}) {
  const [state, submit, pending] = useActionState(freezeAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="inline-flex items-center gap-2">
      <input type="hidden" name="month" value={month} />
      <input type="hidden" name="method" value={method} />
      <input type="hidden" name="scope" value={scope} />
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-accent/60 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent disabled:opacity-50"
      >
        {pending ? "Membekukan…" : "Bekukan peringkat"}
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}
