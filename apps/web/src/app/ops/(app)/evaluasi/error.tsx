"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan gagal Evaluation Center (CLAUDE.md §23). */
export default function EvaluationCenterError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel title="Evaluation Center">
      <ErrorState label="Hasil evaluasi gagal dimuat." />
      <div className="mt-3 text-center">
        <button
          type="button"
          onClick={reset}
          className="rounded border border-base-800 px-3 py-1.5 font-heading text-xs font-semibold uppercase tracking-wider text-ink hover:border-accent/60 hover:text-accent"
        >
          Coba muat ulang
        </button>
      </div>
    </Panel>
  );
}
