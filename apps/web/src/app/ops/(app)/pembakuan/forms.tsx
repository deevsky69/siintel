"use client";

import { useActionState } from "react";
import { confirmAreaAction, resolveDuplicateAction, type StandardState } from "./actions";

const IDLE: StandardState = { error: null, done: null };
const field = "rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink";
const button = "rounded border px-2.5 py-1 text-xs font-semibold disabled:opacity-50";

export function AreaForm({
  code,
  options,
}: {
  code: string;
  options: { code: string; kelurahan: string }[];
}) {
  const [state, submit, pending] = useActionState(confirmAreaAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <select name="location_code" required className={field} defaultValue="">
        <option value="" disabled>
          Kelurahan…
        </option>
        {options.map((option) => (
          <option key={option.code} value={option.code}>
            {option.kelurahan}
          </option>
        ))}
      </select>
      <input name="note" placeholder="Catatan" className={field} />
      <button
        type="submit"
        disabled={pending}
        className={`${button} border-accent/60 bg-accent/10 text-accent`}
      >
        Pastikan
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}

export function DuplicateForm({ code }: { code: string }) {
  const [state, submit, pending] = useActionState(resolveDuplicateAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <input name="note" placeholder="Catatan" className={field} />
      <button
        type="submit"
        name="status"
        value="CONFIRMED"
        disabled={pending}
        className={`${button} border-risk-high/60 bg-risk-high/10 text-risk-high`}
      >
        Ganda
      </button>
      <button
        type="submit"
        name="status"
        value="CLEARED"
        disabled={pending}
        className={`${button} border-risk-low/60 bg-risk-low/10 text-risk-low`}
      >
        Bukan ganda
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}
