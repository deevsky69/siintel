"use client";

import { useActionState } from "react";
import type { WorkSummary } from "@/lib/monthly-evaluation";
import { type WorkState, workLogAction } from "./actions";

const IDLE: WorkState = { error: null, done: null };
const field = "rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink";
const SCORE_LABEL = ["0 · belum memenuhi", "1 · perlu revisi", "2 · memenuhi"];

/** `datetime-local` meminta "YYYY-MM-DDTHH:mm" dalam waktu setempat; layar ini memakai WIB. */
function toLocal(iso: string | null): string {
  if (!iso) return "";
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Jakarta",
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(iso));
  return parts.replace(" ", "T");
}

function ScoreSelect({
  name,
  label,
  value,
  required,
}: {
  name: string;
  label: string;
  value: number | undefined;
  required: boolean;
}) {
  return (
    <select
      name={name}
      aria-label={label}
      defaultValue={value === undefined ? "" : String(value)}
      required={required}
      className={field}
    >
      <option value="">{required ? "pilih" : "—"}</option>
      {SCORE_LABEL.map((text, score) => (
        <option key={text} value={score}>
          {text}
        </option>
      ))}
    </select>
  );
}

/**
 * Formulir Modul 5: skor mutu draf menurut rubrik empat unsur dan cap waktu kerja. "Draf siap"
 * dan "validasi selesai" tidak ada di sini — keduanya diambil dari catatan sistem.
 */
export function WorkLogForm({ month, work }: { month: string; work: WorkSummary }) {
  const [state, submit, pending] = useActionState(workLogAction, IDLE);
  return (
    <form action={submit} className="space-y-3">
      <input type="hidden" name="month" value={month} />
      <div className="table-scroll">
        <table className="w-full min-w-[30rem] text-left text-xs">
          <thead>
            <tr className="border-b border-base-800">
              <th className="stat-label py-1.5 font-medium">Unsur rubrik</th>
              <th className="stat-label py-1.5 font-medium">Draf SIGAP</th>
              <th className="stat-label py-1.5 font-medium">Cara kerja biasa (opsional)</th>
            </tr>
          </thead>
          <tbody>
            {work.rubric.map((item) => (
              <tr key={item.key} className="border-b border-base-800/60">
                <td className="py-1.5 text-ink">{item.label}</td>
                <td className="py-1.5">
                  <ScoreSelect
                    name={`sigap:${item.key}`}
                    label={`${item.label} — draf SIGAP`}
                    value={work.quality_sigap?.[item.key]}
                    required
                  />
                </td>
                <td className="py-1.5">
                  <ScoreSelect
                    name={`manual:${item.key}`}
                    label={`${item.label} — cara kerja biasa`}
                    value={work.quality_manual?.[item.key]}
                    required={false}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {(
          [
            ["received_at", "Data diterima (WIB)", work.received_at],
            ["data_ready_at", "Data siap olah (WIB)", work.data_ready_at],
            ["map_ready_at", "Peta siap (WIB)", work.map_ready_at],
          ] as const
        ).map(([name, label, value]) => (
          <label key={name} className="flex flex-col gap-1 text-2xs text-ink-muted">
            {label}
            <input
              type="datetime-local"
              name={name}
              defaultValue={toLocal(value)}
              className={field}
            />
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          name="note"
          defaultValue={work.note ?? ""}
          placeholder="Catatan (bukti yang diperiksa, alasan skor)"
          className={`${field} min-w-56 flex-1`}
        />
        <button
          type="submit"
          disabled={pending}
          className="rounded border border-accent/60 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent disabled:opacity-50"
        >
          {pending ? "Menyimpan…" : "Catat"}
        </button>
        {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
        {state.done ? <span className="text-xs text-risk-low">{state.done}</span> : null}
      </div>
    </form>
  );
}
