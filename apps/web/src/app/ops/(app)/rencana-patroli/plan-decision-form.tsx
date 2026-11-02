"use client";

import { useActionState, useState } from "react";
import type { PatrolPlan, PlanDecision, ThreatEvaluation } from "@/lib/patrol-plan";
import { decidePlan } from "./actions";
import { IDLE } from "./decision-state";
import { ThreatSlots } from "./plan-view";

/**
 * Formulir keputusan Pimpinan atas rencana patroli.
 *
 * Tiga keputusan berdiri sejajar — setujui, ubah, tolak — supaya layar tidak mendorong
 * "setuju" sebagai jalan termudah (CLAUDE.md §13). Pada "ubah", tiap slot usulan menjadi
 * kotak centang: yang dicentang dipertahankan, yang tidak dicentang dilepas. Slot di luar
 * usulan tidak dapat ditambahkan di sini — itu bukan keputusan atas usulan, melainkan
 * usulan baru.
 *
 * Tombol disembunyikan bagi peran tanpa kewenangan, tetapi itu hanya kenyamanan: penolakan
 * sesungguhnya terjadi di backend (CLAUDE.md §21).
 */
const CHOICES: { value: PlanDecision; label: string; tone: string }[] = [
  {
    value: "APPROVED",
    label: "Setujui seluruhnya",
    tone: "border-risk-low/50 text-risk-low hover:bg-risk-low/10",
  },
  {
    value: "MODIFIED",
    label: "Setujui sebagian",
    tone: "border-risk-moderate/50 text-risk-moderate hover:bg-risk-moderate/10",
  },
  {
    value: "REJECTED",
    label: "Tolak",
    tone: "border-risk-critical/50 text-risk-critical hover:bg-risk-critical/10",
  },
];

export function PlanDecisionForm({
  plan,
  resultOf,
}: {
  plan: PatrolPlan;
  resultOf: Map<string, ThreatEvaluation>;
}) {
  const [state, submit, pending] = useActionState(decidePlan, IDLE);
  const [choice, setChoice] = useState<PlanDecision | null>(null);

  return (
    <form action={submit} className="space-y-4">
      <input type="hidden" name="decision" value={choice ?? ""} />

      {plan.threats.map((threat) => (
        <ThreatSlots
          key={threat.threat_type}
          threat={threat}
          result={resultOf.get(threat.threat_type)}
          selectable={choice === "MODIFIED"}
        />
      ))}

      <fieldset className="border-t border-base-800 pt-4">
        <legend className="stat-label">Keputusan Pimpinan</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {CHOICES.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={choice === item.value}
              onClick={() => setChoice(choice === item.value ? null : item.value)}
              className={[
                "rounded border px-3 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider transition",
                item.tone,
                choice === item.value ? "bg-base-800" : "",
              ].join(" ")}
            >
              {item.label}
            </button>
          ))}
        </div>
        {choice === "MODIFIED" ? (
          <p className="mt-2 text-2xs text-ink-muted">
            Hilangkan centang pada slot yang tidak akan dipatroli. Usulan asli tetap tersimpan
            berdampingan dengan keputusan.
          </p>
        ) : null}
      </fieldset>

      {choice ? (
        <label className="block">
          <span className="stat-label">Pertimbangan{choice === "REJECTED" ? " (wajib)" : ""}</span>
          <textarea
            name="reason"
            rows={2}
            required={choice === "REJECTED"}
            className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
        </label>
      ) : null}

      {state.error ? (
        <p role="alert" className="text-xs text-risk-critical">
          {state.error}
        </p>
      ) : null}
      {state.done ? (
        <p role="status" className="text-xs text-accent">
          Keputusan {state.done} tercatat.
        </p>
      ) : null}

      <div>
        <button
          type="submit"
          disabled={pending || choice === null}
          className="rounded bg-accent/20 px-4 py-2 font-heading text-xs font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-40"
        >
          {pending ? "Mencatat…" : "Catat Keputusan"}
        </button>
        <p className="mt-2 text-2xs text-ink-muted">
          Keputusan tercatat beserta nama pejabat, waktu, dan salinan usulan yang dibaca saat
          memutus. Keputusan berikutnya menggantikan yang berlaku tanpa menghapus riwayat.
        </p>
      </div>
    </form>
  );
}
