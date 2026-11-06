"use client";

import { useActionState } from "react";
import type { ProductItem } from "@/lib/monthly-products";
import {
  analystAction,
  decideAction,
  draftAction,
  outcomeAction,
  type ProductState,
  recordActionForm,
} from "./actions";

const IDLE: ProductState = { error: null, done: null };
const field = "rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink";
const primary =
  "rounded border border-accent/60 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent disabled:opacity-50";
const danger =
  "rounded border border-risk-high/60 bg-risk-high/10 px-3 py-1 text-xs font-semibold text-risk-high disabled:opacity-50";

function Status({ state }: { state: ProductState }) {
  if (state.error) return <span className="text-xs text-risk-critical">{state.error}</span>;
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return null;
}

export function DraftForm({ month }: { month: string }) {
  const [state, submit, pending] = useActionState(draftAction, IDLE);
  return (
    <form action={submit} className="flex items-center gap-2">
      <input type="hidden" name="month" value={month} />
      <button type="submit" disabled={pending} className={primary}>
        {pending ? "Menyusun…" : `Susun draf ${month}`}
      </button>
      <Status state={state} />
    </form>
  );
}

export function AnalystForm({ month, items }: { month: string; items: ProductItem[] }) {
  const [state, submit, pending] = useActionState(analystAction, IDLE);
  return (
    <form action={submit} className="space-y-2">
      <input type="hidden" name="month" value={month} />
      {items.map((item) => (
        <div
          key={item.kelurahan}
          className="grid gap-1 rounded border border-base-800 p-2 sm:grid-cols-[1fr_auto]"
        >
          <input type="hidden" name="kelurahan" value={item.kelurahan} />
          <div className="text-xs">
            <span className="font-semibold text-ink">
              {item.rank}. {item.kelurahan}
            </span>
            <p className="mt-0.5 text-ink-muted">{item.proposal_text}</p>
          </div>
          <div className="flex flex-col gap-1">
            <select name={`status:${item.kelurahan}`} defaultValue="ACCEPTED" className={field}>
              <option value="ACCEPTED">Terima</option>
              <option value="REVISED">Perbaiki</option>
              <option value="REJECTED">Tolak</option>
            </select>
            <input name={`text:${item.kelurahan}`} placeholder="Teks perbaikan" className={field} />
            <input
              name={`reason:${item.kelurahan}`}
              placeholder="Alasan (wajib bila perbaiki/tolak)"
              className={field}
            />
          </div>
        </div>
      ))}
      <div className="flex flex-wrap items-center gap-2">
        <input name="note" placeholder="Catatan analis" className={`${field} flex-1`} />
        <button type="submit" disabled={pending} className={primary}>
          Teruskan ke KBO
        </button>
        <Status state={state} />
      </div>
    </form>
  );
}

export function OutcomeForm({
  month,
  stage,
  label,
}: {
  month: string;
  stage: "kbo" | "kasat";
  label: string;
}) {
  const [state, submit, pending] = useActionState(outcomeAction, IDLE);
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="month" value={month} />
      <input type="hidden" name="stage" value={stage} />
      <input
        name="reason"
        placeholder="Alasan (wajib bila dikembalikan)"
        className={`${field} flex-1`}
      />
      <button type="submit" name="outcome" value="ACCEPTED" disabled={pending} className={primary}>
        {label}
      </button>
      <button type="submit" name="outcome" value="REJECTED" disabled={pending} className={danger}>
        Kembalikan
      </button>
      <Status state={state} />
    </form>
  );
}

export function DecideForm({ month, items }: { month: string; items: ProductItem[] }) {
  const [state, submit, pending] = useActionState(decideAction, IDLE);
  const eligible = items.filter((item) => item.analyst_status !== "REJECTED");
  return (
    <form action={submit} className="space-y-2">
      <input type="hidden" name="month" value={month} />
      {eligible.map((item) => (
        <label
          key={item.kelurahan}
          className="grid gap-1 rounded border border-base-800 p-2 text-xs sm:grid-cols-[auto_1fr]"
        >
          <span className="flex items-start gap-2">
            <input
              type="checkbox"
              name="selected"
              value={item.kelurahan}
              defaultChecked={item.rank <= 6}
              className="mt-0.5"
            />
            <span className="font-semibold text-ink">
              {item.rank}. {item.kelurahan}
            </span>
          </span>
          <input
            name={`action:${item.kelurahan}`}
            defaultValue={item.analyst_text ?? item.proposal_text}
            className={field}
          />
        </label>
      ))}
      <div className="flex flex-wrap items-center gap-2">
        <input name="reason" placeholder="Pertimbangan" className={`${field} flex-1`} />
        <button type="submit" disabled={pending} className={primary}>
          Tetapkan prioritas
        </button>
        <Status state={state} />
      </div>
    </form>
  );
}

export function ActionForm({ month, kelurahan }: { month: string; kelurahan: string }) {
  const [state, submit, pending] = useActionState(recordActionForm, IDLE);
  return (
    <form action={submit} className="mt-1 flex flex-wrap items-center gap-1.5">
      <input type="hidden" name="month" value={month} />
      <input type="hidden" name="kelurahan" value={kelurahan} />
      <input name="acted_at" type="datetime-local" required className={field} />
      <input name="place" placeholder="Tempat" required className={field} />
      <input name="action" placeholder="Tindakan" required className={`${field} min-w-[12rem]`} />
      <input name="result" placeholder="Hasil" className={field} />
      <input name="unit" placeholder="Satuan" className={`${field} w-28`} />
      <button type="submit" disabled={pending} className={primary}>
        Catat
      </button>
      <Status state={state} />
    </form>
  );
}
