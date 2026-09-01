"use client";

import { ErrorState } from "@/components/data-state";
import { Panel } from "@/components/panel";

/** Keadaan gagal untuk halaman peta (CLAUDE.md §23). */
export default function PetaError({ reset }: { error: Error; reset: () => void }) {
  return (
    <Panel
      title="Live Kamtibmas Map"
      action={
        <button type="button" className="panel-action" onClick={reset}>
          Muat ulang
        </button>
      }
    >
      <ErrorState label="Data peta gagal dimuat." />
    </Panel>
  );
}
