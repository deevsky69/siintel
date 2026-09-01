"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan gagal Warning Center (CLAUDE.md §23). */
export default function WarningCenterError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel title="Warning Center">
      <ErrorState label="Peringatan dini gagal dimuat." />
      <div className="mt-3 text-center">
        <button
          type="button"
          onClick={reset}
          className="rounded border border-base-800 px-3 py-1.5 font-heading text-[11px] font-semibold uppercase tracking-wider text-ink hover:border-accent/60 hover:text-accent"
        >
          Coba muat ulang
        </button>
      </div>
    </Panel>
  );
}
