"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan gagal jejak audit (CLAUDE.md §23). */
export default function AuditError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel title="Jejak Audit">
      <ErrorState label="Jejak audit gagal dimuat." />
      <p className="mt-2 text-center text-xs text-ink-muted">
        Bila Anda tidak berwenang membaca jejak audit, itulah sebabnya — kewenangan ini hanya
        dimiliki Pimpinan dan Administrator.
      </p>
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
