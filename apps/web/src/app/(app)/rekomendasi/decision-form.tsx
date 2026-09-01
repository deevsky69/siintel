"use client";

import { useActionState, useState } from "react";
import type { Decision } from "@/lib/decisions";
import { decide } from "./actions";
import { IDLE } from "./decision-state";

/**
 * Formulir keputusan pejabat.
 *
 * Tiga keputusan berdiri sejajar — menyetujui, memodifikasi, menolak — supaya layar tidak
 * mendorong pengguna menekan "setuju" sebagai jalan termudah. Sistem mengusulkan,
 * manusia memutuskan (CLAUDE.md §13).
 *
 * Tombol ini disembunyikan bagi peran tanpa kewenangan, tetapi itu hanya kenyamanan:
 * penolakan sesungguhnya terjadi di backend (CLAUDE.md §21).
 */

/**
 * Label tombol adalah kata kerja ("Setujui"), berbeda dari label status ("Disetujui")
 * pada `lib/decisions.ts` — dan ditulis di sini agar komponen klien ini tidak ikut
 * menarik modul yang memuat `next/headers`.
 */
const CHOICES: { value: Decision; label: string; tone: string }[] = [
  {
    value: "APPROVED",
    label: "Setujui",
    tone: "border-risk-low/50 text-risk-low hover:bg-risk-low/10",
  },
  {
    value: "MODIFIED",
    label: "Modifikasi",
    tone: "border-risk-moderate/50 text-risk-moderate hover:bg-risk-moderate/10",
  },
  {
    value: "REJECTED",
    label: "Tolak",
    tone: "border-risk-critical/50 text-risk-critical hover:bg-risk-critical/10",
  },
];

export function DecisionForm({ code }: { code: string }) {
  const [state, submit, pending] = useActionState(decide, IDLE);
  const [choice, setChoice] = useState<Decision | null>(null);

  return (
    <form action={submit} className="mt-4 border-t border-base-800 pt-4">
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="decision" value={choice ?? ""} />

      <fieldset>
        <legend className="stat-label">Keputusan Pejabat Berwenang</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {CHOICES.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={choice === item.value}
              onClick={() => setChoice(choice === item.value ? null : item.value)}
              className={[
                "rounded border px-3 py-1.5 font-heading text-[11px] font-semibold uppercase tracking-wider transition",
                item.tone,
                choice === item.value ? "bg-base-800" : "",
              ].join(" ")}
            >
              {item.label}
            </button>
          ))}
        </div>
      </fieldset>

      {choice === "MODIFIED" ? (
        <label className="mt-3 block">
          <span className="stat-label">Rekomendasi Setelah Disesuaikan</span>
          <textarea
            name="modified_text"
            rows={3}
            required
            className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
          <span className="mt-1 block text-[10px] text-ink-muted">
            Usulan asli sistem tidak ditimpa — keduanya tersimpan berdampingan.
          </span>
        </label>
      ) : null}

      {choice ? (
        <label className="mt-3 block">
          <span className="stat-label">Pertimbangan</span>
          <textarea
            name="reason"
            rows={2}
            className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
          />
        </label>
      ) : null}

      {state.error ? (
        <p role="alert" className="mt-3 text-xs text-risk-critical">
          {state.error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending || choice === null}
        className="mt-3 rounded bg-accent/20 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-40"
      >
        {pending ? "Mencatat…" : "Catat Keputusan"}
      </button>
      <p className="mt-2 text-[10px] text-ink-muted">
        Keputusan tercatat beserta nama pejabat dan waktunya, serta tidak dapat diubah kemudian.
      </p>
    </form>
  );
}
